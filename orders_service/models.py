"""
Module that provides models for the database
"""

import datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer
from sqlalchemy.orm import (
    Mapped,
    declarative_base,
    mapped_column,
    relationship,
    validates,
)

from orders_service.common import Product, Size, Status


def generate_uuid():
    """Generates UUID as String"""

    return str(uuid4())


Base = declarative_base()


class OrderModel(Base):
    """Order Model"""

    __tablename__ = "order"

    id: Mapped[str] = mapped_column(default=generate_uuid, primary_key=True, index=True)
    created: Mapped[datetime.datetime] = mapped_column(default=datetime.datetime.now(datetime.UTC))
    status: Mapped[Status] = mapped_column(default=Status.CREATED, nullable=False)
    items: Mapped[list["OrderItemModel"]] = relationship(
        "OrderItemModel", cascade="all,delete", backref="order", lazy="selectin"
    )

    def dict(self):
        """Returns Order Item as a dict"""

        return {
            "id": self.id,
            "status": self.status,
            "created": self.created,
            "items": [item.dict() for item in self.items],
        }

    def __repr__(self) -> str:
        """Order REPR"""

        return f"Order(id={self.id!r}, created={self.created!r}, status={self.status!r}, items={self.items!r})"


class OrderItemModel(Base):
    """Order Item Model"""

    __tablename__ = "order_item"

    id: Mapped[str] = mapped_column(default=generate_uuid, primary_key=True, index=True)
    product: Mapped[Product] = mapped_column(nullable=False)
    size: Mapped[Size] = mapped_column(nullable=False)
    quantity = Column(
        Integer,
        CheckConstraint("quantity >= 1 AND quantity <= 10"),
        default=1,
        nullable=False,
    )

    order_id: Mapped[str] = mapped_column(ForeignKey("order.id"), index=True, nullable=False)

    @validates("quantity")
    def validate_quantity(self, _, value):
        """Quantity Validation"""

        if value < 1 or value > 10:
            raise ValueError(f"Quantity must be between 1 and 10 found: {value}")
        return value

    def dict(self):
        """Returns Order Item as a dict"""

        return {
            "id": self.id,
            "product": self.product,
            "size": self.size,
            "quantity": self.quantity,
        }

    def __repr__(self) -> str:
        """Order Item REPR"""

        return f"OrderItem(id={self.id!r}, product={self.product!r}, size={self.size!r}, quantity={self.quantity!r})"
