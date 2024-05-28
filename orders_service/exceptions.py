"""
Module that provides exceptions for the Orders API
"""


class OrdersApiError(Exception):
    """Base exception class"""

    def __init__(self, message: str = "Service is unavailable", name: str = "OrdersApi"):
        self.message = message
        self.name = name
        super().__init__(self.message, self.name)


class OrderServiceError(OrdersApiError):
    """Failures in external services or APIs, like a database or a third-party service"""


class OrderEntityNotFoundError(OrdersApiError):
    """Entity not found error"""


class OrderValidationError(OrdersApiError):
    """Validation error"""
