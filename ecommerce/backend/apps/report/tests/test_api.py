from django.test import TestCase
from rest_framework.test import APIClient

from apps.account.models import Shop, User
from apps.ai.models import ChatFeedback, ChatMessage, ChatSession
from apps.common.models import AuditLog, SiteSetting


class ReportApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            email="admin-report@example.com", password="secret", role=User.Role.ADMIN
        )
        self.seller = User.objects.create_user(
            email="seller-report@example.com", password="secret", role=User.Role.SELLER
        )
        self.customer = User.objects.create_user(
            email="customer-report@example.com", password="secret"
        )
        Shop.objects.create(owner=self.seller, name="Report Shop", slug="report-shop")

    def test_admin_dashboard_is_admin_only(self):
        self.client.force_authenticate(self.customer)
        self.assertEqual(self.client.get("/api/v1/admin/dashboard/summary/").status_code, 403)

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/admin/dashboard/summary/?days=30")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["orders"], 0)

    def test_seller_dashboard_is_scoped_to_authenticated_shop(self):
        self.client.force_authenticate(self.seller)
        response = self.client.get("/api/v1/seller/dashboard/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["shop_name"], "Report Shop")

    def test_chatbot_metrics_include_csat_and_ab_variant(self):
        session = ChatSession.objects.create(
            user=self.customer,
            experiment_variant="guided_actions",
        )
        message = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content="Tư vấn đã xác minh.",
        )
        ChatFeedback.objects.create(
            message=message,
            session=session,
            submitted_by=self.customer,
            rating=5,
            resolved=True,
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/v1/admin/dashboard/chatbot?days=30")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["csat"], 5)
        self.assertEqual(response.data["data"]["automated_resolution_rate"], 100)
        self.assertEqual(
            response.data["data"]["variants"][0]["experiment_variant"],
            "guided_actions",
        )

    def test_site_setting_update_invalidates_cache_and_creates_audit_log(self):
        self.client.force_authenticate(self.admin)
        response = self.client.put(
            "/api/v1/admin/settings/",
            {"key": "checkout.enabled", "value": True, "description": "Checkout flag"},
            format="json",
            HTTP_X_REQUEST_ID="setting-test",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(SiteSetting.get_bool("checkout.enabled"))
        self.assertTrue(
            AuditLog.objects.filter(action="settings.update", request_id="setting-test").exists()
        )

    def test_report_export_supports_xlsx_and_pdf(self):
        self.client.force_authenticate(self.admin)
        for export_format, content_type in (
            ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ("pdf", "application/pdf"),
        ):
            response = self.client.post(
                "/api/v1/admin/reports/export/",
                {"report": "top-sellers", "format": export_format},
                format="json",
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], content_type)
            self.assertGreater(len(response.content), 100)
