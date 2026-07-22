class BusinessError(Exception):
    """Base exception for expected domain failures."""

    def __init__(self, message: str, *, errors: dict | None = None, http_status: int = 400):
        super().__init__(message)
        self.errors = errors or {}
        self.http_status = http_status
