from rest_framework.pagination import PageNumberPagination

from .responses import success_response


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return success_response(
            data=data,
            message="Lấy danh sách thành công",
            meta={
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "total_items": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
            },
        )
