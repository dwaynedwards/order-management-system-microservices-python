"""
Module that provides repository for the Orders API
"""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from orders_service.exceptions import OrderEntityNotFoundError, OrderValidationError
from orders_service.models import OrderItemModel, OrderModel, Status
from orders_service.schemas import (
    OrderCreateSchema,
    OrderGetSchema,
    OrdersListSchema,
    OrderUpdateSchema,
)
from orders_service.session import DBSessionDep


class OrdersRepository:
    """Orders API Reponsitory"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, cancelled: Optional[bool] = None, limit: Optional[int] = None) -> OrdersListSchema:
        """List Orders"""

        orders_to_get = select(OrderModel)

        if cancelled is not None:
            if cancelled:
                orders_to_get = orders_to_get.where(OrderModel.status == Status.CANCELLED)
            else:
                orders_to_get = orders_to_get.where(OrderModel.status != Status.CANCELLED)
        if limit is not None:
            if limit < 1 or limit > 10:
                raise OrderValidationError(f"Limit must be >= 1 and <= 10: found {limit}")

            orders_to_get = orders_to_get.limit(limit)

        orders_found = (await self.db.execute(orders_to_get)).scalars().all()

        return OrdersListSchema(orders=[OrderGetSchema(**order.dict()) for order in orders_found])

    async def create(self, order_details: OrderCreateSchema) -> OrderModel:
        """Create Order"""

        order_created = OrderModel(items=[OrderItemModel(**item) for item in order_details.model_dump()["items"]])

        self.db.add(order_created)
        await self.db.commit()
        await self.db.refresh(order_created)

        return order_created

    async def get(self, order_id: UUID) -> OrderModel:
        """Get Order"""

        order_found = (
            (await self.db.execute(select(OrderModel).where(OrderModel.id == str(order_id)))).scalars().first()
        )

        if not order_found:
            raise OrderEntityNotFoundError(f"Order with ID {order_id} not found")

        return order_found

    async def update(self, order_id: UUID, order_details: OrderUpdateSchema) -> OrderModel:
        """Update Order"""

        order_found = (
            (await self.db.execute(select(OrderModel).where(OrderModel.id == str(order_id)))).scalars().first()
        )

        if not order_found:
            raise OrderEntityNotFoundError(f"Order with ID {order_id} not found")

        for item in order_found.items:
            await self.db.delete(item)

        order_found.items = [OrderItemModel(**item) for item in order_details.model_dump()["items"]]

        await self.db.commit()
        await self.db.refresh(order_found)

        return order_found

    async def delete(self, order_id: UUID) -> OrderModel:
        """Get Order"""

        order_found = (
            (await self.db.execute(select(OrderModel).where(OrderModel.id == str(order_id)))).scalars().first()
        )

        if not order_found:
            raise OrderEntityNotFoundError(f"Order with ID {order_id} not found")

        await self.db.delete(order_found)
        await self.db.commit()

    async def cancel(self, order_id: UUID) -> OrderModel:
        """Cancel Order"""

        order_found = (
            (await self.db.execute(select(OrderModel).where(OrderModel.id == str(order_id)))).scalars().first()
        )

        if not order_found:
            raise OrderEntityNotFoundError(f"Order with ID {order_id} not found")

        order_found.status = Status.CANCELLED

        await self.db.commit()
        await self.db.refresh(order_found)

        return order_found

    async def pay(self, order_id: UUID) -> OrderModel:
        """Pay Order"""

        order_found = (
            (await self.db.execute(select(OrderModel).where(OrderModel.id == str(order_id)))).scalars().first()
        )

        if not order_found:
            raise OrderEntityNotFoundError(f"Order with ID {order_id} not found")

        order_found.status = Status.PAID

        await self.db.commit()
        await self.db.refresh(order_found)

        return order_found


def get_repo(db: DBSessionDep):
    """Returns Orders Reponsitory"""

    return OrdersRepository(db)


OrdersRepoDep = Annotated[OrdersRepository, Depends(get_repo)]
