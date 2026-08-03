from apps.common.exceptions import BusinessError


class InvalidOrderTransition(BusinessError):
    def __init__(self, current: str, target: str):
        super().__init__(
            f"Không thể chuyển đơn từ {current} sang {target}",
            errors={"fulfillment_status": ["Chuyển trạng thái không hợp lệ"]},
            http_status=409,
        )
