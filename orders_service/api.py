"""
Module that provides the route endpoints for the Orders API
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status

from orders_service.exceptions import OrderEntityNotFoundError
from orders_service.repository import OrdersRepoDep
from orders_service.schemas import (
    OrderCreateSchema,
    OrderGetSchema,
    OrdersListSchema,
    OrderUpdateSchema,
)

router = APIRouter(prefix="/orders")


@router.get("/", status_code=status.HTTP_200_OK, response_model=OrdersListSchema)
async def list_orders(
    repo: OrdersRepoDep,
    cancelled: bool | None = None,
    limit: int | None = Query(default=None, ge=1, le=10),
):
    """Returns a list of orders"""

    orders = await repo.list(cancelled, limit)

    return orders.model_dump()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=OrderGetSchema)
async def create_order(
    repo: OrdersRepoDep,
    order_details: OrderCreateSchema,
):
    """Creates an order"""

    order = await repo.create(order_details)

    return order.dict()


@router.get("/{order_id}", status_code=status.HTTP_200_OK, response_model=OrderGetSchema)
async def get_order(repo: OrdersRepoDep, order_id: UUID):
    """Returns the details of a specified order"""

    try:
        return await repo.get(order_id)
    except OrderEntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message) from e


@router.put("/{order_id}", response_model=OrderGetSchema)
async def update_order(
    repo: OrdersRepoDep,
    order_id: UUID,
    order_details: OrderUpdateSchema,
):
    """Replaces an existing specified order"""

    try:
        order = await repo.update(order_id, order_details)

        return order.dict()
    except OrderEntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message) from e


@router.delete("/{order_id}", response_class=Response)
async def delete_order(
    repo: OrdersRepoDep,
    order_id: UUID,
):
    """Deletes an existing specified order"""

    try:
        await repo.delete(order_id)

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except OrderEntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message) from e


@router.post("/{order_id}/cancel", response_model=OrderGetSchema)
async def cancel_order(
    repo: OrdersRepoDep,
    order_id: UUID,
):
    """Cancels a specified order"""

    try:
        order = await repo.cancel(order_id)

        return order.dict()
    except OrderEntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message) from e


@router.post("/{order_id}/pay", response_model=OrderGetSchema)
async def pay_order(
    repo: OrdersRepoDep,
    order_id: UUID,
):
    """Processes payment for a specified order"""

    try:
        order = await repo.pay(order_id)

        return order.dict()
    except OrderEntityNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message) from e
