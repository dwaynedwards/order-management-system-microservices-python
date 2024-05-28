"""Module that provides schema for Orders API"""

from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from annotated_types import MinLen
from pydantic import BaseModel, ConfigDict, Field, field_validator

from orders_service.common import Product, Size, Status


class OrderItemGetSchema(BaseModel):
    """Order Item Schema"""

    model_config = ConfigDict(extra="forbid")

    id: Optional[UUID] = None
    product: Product
    size: Size
    quantity: Optional[Annotated[int, Field(strict=True, ge=1, le=10)]] = 1

    @field_validator("quantity")
    @classmethod
    def quantity_non_nullable(cls, value):
        """Validates that quantity is not None"""

        assert value is not None, "quantity may not be None"
        return value


class OrderGetSchema(BaseModel):
    """Order Get Schema"""

    model_config = ConfigDict(extra="forbid")

    id: Optional[UUID] = None
    created: datetime
    status: Status
    items: Annotated[list[OrderItemGetSchema], MinLen(1)]


class OrdersListSchema(BaseModel):
    """Orders List Schema"""

    orders: List[OrderGetSchema]


class OrderCreateSchema(BaseModel):
    """Order Create Schema"""

    model_config = ConfigDict(extra="forbid")

    items: Annotated[list[OrderItemGetSchema], MinLen(1)]


class OrderUpdateSchema(OrderCreateSchema):
    """Order Update Schema"""
