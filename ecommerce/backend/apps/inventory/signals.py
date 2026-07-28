from .notifications import InventoryNotificationService


def stock_reached_low_threshold(*, balance) -> None:
    """Thin event boundary; threshold calculation remains inside StockService."""
    InventoryNotificationService.notify_low_stock(balance=balance)


def stock_became_available(*, variant, available_stock: int) -> None:
    """Thin event boundary; transition detection remains inside StockService."""
    InventoryNotificationService.notify_back_in_stock(
        variant=variant,
        available_stock=available_stock,
    )

