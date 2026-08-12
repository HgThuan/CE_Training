from io import BytesIO

from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.account.models import Shop
from apps.account.permissions import IsAdmin, IsSeller
from apps.common.cache_utils import build_cache_key
from apps.common.models import AuditLog, SiteSetting
from apps.common.responses import success_response

from . import selectors


def days_from(request):
    try:
        return max(1, min(int(request.query_params.get("days", 30)), 366))
    except (TypeError, ValueError):
        return 30


def cached(request, namespace, producer):
    period = request.query_params.get("period", "day")
    key = build_cache_key(
        namespace,
        {"days": days_from(request), "period": period, "user": request.user.pk},
    )
    value = cache.get(key)
    if value is None:
        value = producer()
        cache.set(key, value, 300)
    return success_response(data=value)


class AdminDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    metric = "summary"

    def get(self, request):
        days = days_from(request)
        period = request.query_params.get("period", "day")
        producers = {
            "summary": lambda: selectors.admin_summary(days),
            "revenue": lambda: selectors.revenue_chart(days, period=period),
            "products": lambda: selectors.top_products(days),
        }
        return cached(request, f"admin-dashboard-{self.metric}", producers[self.metric])


class SellerDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsSeller]
    metric = "summary"

    def get(self, request):
        shop = Shop.objects.get(owner=request.user, is_deleted=False)
        days = days_from(request)
        period = request.query_params.get("period", "day")
        producers = {
            "summary": lambda: selectors.seller_summary(shop, days),
            "revenue": lambda: selectors.revenue_chart(days, shop, period=period),
            "products": lambda: selectors.top_products(days, shop),
        }
        return cached(request, f"seller-dashboard-{self.metric}", producers[self.metric])


class ShopRevenueView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, shop_id):
        shop = Shop.objects.get(pk=shop_id, is_deleted=False)
        days = days_from(request)
        period = request.query_params.get("period", "day")
        return success_response(
            data={
                "summary": selectors.seller_summary(shop, days),
                "chart": selectors.revenue_chart(days, shop, period=period),
            }
        )


class ReportView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    report = "sellers"

    def get(self, request):
        days = days_from(request)
        producers = {
            "sellers": selectors.top_sellers,
            "customers": selectors.top_customers,
            "categories": selectors.top_categories,
            "cancel-return": selectors.cancel_return_rate,
        }
        return success_response(data=producers[self.report](days))


class ReportExportView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        report = request.data.get("report", "top-sellers")
        export_format = request.data.get("format", "xlsx").lower()
        if export_format not in {"xlsx", "pdf"}:
            export_format = "xlsx"
        days = days_from(request)
        producers = {
            "top-sellers": selectors.top_sellers,
            "top-customers": selectors.top_customers,
            "top-categories": selectors.top_categories,
        }
        rows = producers.get(report, selectors.top_sellers)(days)
        fields = list(rows[0].keys()) if rows else ["message"]
        rows = rows or [{"message": "No data"}]
        output = BytesIO()
        if export_format == "xlsx":
            from openpyxl import Workbook

            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Report"
            sheet.append(fields)
            for row in rows:
                sheet.append([row.get(field) for field in fields])
            workbook.save(output)
            content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen.canvas import Canvas

            canvas = Canvas(output, pagesize=A4)
            width, height = A4
            y = height - 48
            canvas.setFont("Helvetica-Bold", 14)
            canvas.drawString(40, y, report.replace("-", " ").title())
            canvas.setFont("Helvetica", 8)
            for row in rows:
                y -= 18
                if y < 40:
                    canvas.showPage()
                    canvas.setFont("Helvetica", 8)
                    y = height - 40
                text = " | ".join(f"{field}: {row.get(field, '')}" for field in fields)
                canvas.drawString(40, y, text[:130])
            canvas.save()
            content_type = "application/pdf"
        AuditLog.objects.create(
            actor=request.user,
            action="report.export",
            target_type="report",
            target_id=report,
            request_id=getattr(request, "request_id", ""),
            diff={"days": days, "format": export_format},
        )
        response = HttpResponse(output.getvalue(), content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{report}.{export_format}"'
        return response


class AuditLogView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        queryset = AuditLog.objects.select_related("actor")
        for field in ("action", "target_type", "target_id", "request_id"):
            if value := request.query_params.get(field):
                queryset = queryset.filter(**{field: value})
        data = [
            {
                "id": row.pk,
                "actor": row.actor.email,
                "action": row.action,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "reason": row.reason,
                "request_id": row.request_id,
                "diff": row.diff,
                "created_at": row.created_at,
            }
            for row in queryset[:200]
        ]
        return success_response(data=data)


class SiteSettingView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return success_response(
            data=[
                {
                    "key": item.key,
                    "value": item.value,
                    "value_type": item.value_type,
                    "description": item.description,
                    "is_public": item.is_public,
                }
                for item in SiteSetting.objects.all()
            ]
        )

    def put(self, request):
        items = request.data.get("settings", [request.data])
        saved = []
        for item in items:
            setting = SiteSetting.set_value(
                item["key"],
                item.get("value"),
                description=item.get("description"),
                is_public=item.get("is_public"),
                updated_by=request.user,
            )
            saved.append(
                {
                    "key": setting.key,
                    "value": setting.value,
                    "value_type": setting.value_type,
                    "description": setting.description,
                    "is_public": setting.is_public,
                }
            )
        AuditLog.objects.create(
            actor=request.user,
            action="settings.update",
            target_type="site_setting",
            target_id=",".join(x["key"] for x in saved)[:64],
            request_id=getattr(request, "request_id", ""),
            diff={"keys": [x["key"] for x in saved]},
        )
        return success_response(data=saved, message="Đã cập nhật cấu hình")
