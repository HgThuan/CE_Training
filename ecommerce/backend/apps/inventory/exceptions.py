from apps.common.exceptions import BusinessError


class InsufficientStockError(BusinessError):
    def __init__(self, message: str = "Không đủ tồn kho khả dụng"):
        super().__init__(
            message,
            errors={"stock": ["Số lượng yêu cầu vượt quá tồn kho khả dụng"]},
            http_status=409,
        )
