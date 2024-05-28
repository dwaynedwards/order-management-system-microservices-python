"""
Module that provides common classes for the Orders API
"""

from enum import Enum


class Product(Enum):
    """Product Enum"""

    CHEESE = "cheese"
    PEPPERONI = "pepperoni"
    DELUXE = "deluxe"
    HAWAIIAN = "hawaiian"
    CANADIAN = "canadian"
    VEGGIE = "veggie"

    COKE = "coke"
    SPRITE = "sprite"
    GINGERALE = "gingerale"
    ICEDTEA = "icedtea"


class Size(Enum):
    """Size Enum"""

    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    XLARGE = "xlarge"


class Status(Enum):
    """Status Enum"""

    CREATED = "created"
    PAID = "paid"
    PROGRESS = "progress"
    CANCELLED = "cancelled"
    DISPATCHED = "dispatched"
    DELIVIERED = "delivered"
