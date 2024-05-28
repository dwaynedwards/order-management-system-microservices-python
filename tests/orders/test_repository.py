from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
import pytest_asyncio
from pydantic import ValidationError

from orders_service.common import Product, Size, Status
from orders_service.config import get_config
from orders_service.exceptions import OrderEntityNotFoundError, OrderValidationError
from orders_service.repository import OrdersRepository
from orders_service.schemas import OrderCreateSchema
from orders_service.session import begin_session_create_tables, end_session, get_db_session, init_session_manager


class TestOrdersRepository:
    """Test Orders Repository"""

    @pytest_asyncio.fixture
    async def orders_repo(self):
        init_session_manager(get_config("orders_service/.env.test").DATABASE_URL)
        await begin_session_create_tables()
        async with asynccontextmanager(get_db_session)() as session:
            yield OrdersRepository(session)
        await end_session()

    # Orders List Happy Path

    @pytest.mark.asyncio
    async def test_that_list_orders_should_be_empty(self, orders_repo: OrdersRepository):
        response = await orders_repo.list()

        assert len(response.orders) == 0

    @pytest.mark.asyncio
    async def test_that_list_orders_should_retrieve_4_orders(self, orders_repo: OrdersRepository):
        await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "small"}]))
        await orders_repo.create(OrderCreateSchema(items=[{"product": "pepperoni", "size": "medium"}]))
        await orders_repo.create(OrderCreateSchema(items=[{"product": "coke", "size": "large"}]))
        await orders_repo.create(OrderCreateSchema(items=[{"product": "gingerale", "size": "xlarge"}]))

        response = await orders_repo.list()
        assert len(response.orders) == 4

    @pytest.mark.asyncio
    @pytest.mark.parametrize("cancelled,count", [(True, 1), (False, 3)])
    async def test_that_list_orders_should_retrieve_filtered_orders(
        self,
        orders_repo: OrdersRepository,
        cancelled: bool,
        count: int,
    ):
        await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "small"}]))
        await orders_repo.create(OrderCreateSchema(items=[{"product": "pepperoni", "size": "medium"}]))
        await orders_repo.create(OrderCreateSchema(items=[{"product": "coke", "size": "large"}]))
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "gingerale", "size": "xlarge"}]))
        order_id = response.id

        await orders_repo.cancel(order_id)

        response = await orders_repo.list(cancelled, None)

        assert len(response.orders) == count

    @pytest.mark.asyncio
    @pytest.mark.parametrize("limit,expected_limit", [(1, 1), (5, 5), (10, 5)])
    async def test_that_list_orders_should_retrieve_limited_orders(
        self,
        orders_repo: OrdersRepository,
        limit: int,
        expected_limit: int,
    ):
        await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "small"}]))
        await orders_repo.create(OrderCreateSchema(items=[{"product": "pepperoni", "size": "medium"}]))
        await orders_repo.create(OrderCreateSchema(items=[{"product": "hawaiian", "size": "xlarge"}]))
        await orders_repo.create(OrderCreateSchema(items=[{"product": "coke", "size": "large"}]))
        await orders_repo.create(OrderCreateSchema(items=[{"product": "gingerale", "size": "xlarge"}]))

        response = await orders_repo.list(None, limit)

        assert len(response.orders) == expected_limit

    # Orders List Sad Path

    @pytest.mark.asyncio
    @pytest.mark.parametrize("limit", [0, 11])
    async def test_that_list_orders_should_fail_to_retrieve_limited_orders_out_of_range(
        self, orders_repo: OrdersRepository, limit: int
    ):
        with pytest.raises(OrderValidationError) as e:
            await orders_repo.list(None, limit)

        assert e.value.message == f"Limit must be >= 1 and <= 10: found {limit}"

    # Orders Create Happy Path

    @pytest.mark.asyncio
    async def test_that_an_order_is_created_with_default_quantity(self, orders_repo: OrdersRepository):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "small"}]))

        assert response.id is not None
        assert response.created is not None
        assert response.status == Status.CREATED
        assert len(response.items) == 1
        assert response.items[0].id is not None
        assert response.items[0].product == Product.CHEESE
        assert response.items[0].size == Size.SMALL
        assert response.items[0].quantity == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "product,size,quantity",
        [(Product.COKE, Size.LARGE, 4), (Product.ICEDTEA, Size.MEDIUM, 10)],
    )
    async def test_that_an_order_is_created_with_product_size_and_quantity(
        self,
        orders_repo: OrdersRepository,
        product: Product,
        size: Size,
        quantity: int,
    ):
        response = await orders_repo.create(
            OrderCreateSchema(items=[{"product": product, "size": size, "quantity": quantity}])
        )

        assert response.id is not None
        assert response.created is not None
        assert response.status == Status.CREATED
        assert len(response.items) == 1
        assert response.items[0].id is not None
        assert response.items[0].product == product
        assert response.items[0].size == size
        assert response.items[0].quantity == quantity

    # Orders Create Sad Path

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "quantity,msg",
        [(0, "Input should be greater than or equal to 1"), (11, "Input should be less than or equal to 10")],
    )
    async def test_that_an_order_should_fail_to_create_with_quantity_out_of_range(
        self,
        orders_repo: OrdersRepository,
        quantity: int,
        msg: str,
    ):
        with pytest.raises(ValidationError) as e:
            await orders_repo.create(
                OrderCreateSchema(items=[{"product": "cheese", "size": "small", "quantity": quantity}])
            )

        assert e.value.errors()[0]["msg"] == msg

    @pytest.mark.asyncio
    async def test_that_an_order_should_fail_to_create_with_incorrect_product(self, orders_repo: OrdersRepository):
        msg = "Input should be 'cheese', 'pepperoni', 'deluxe', 'hawaiian', 'canadian', 'veggie', 'coke', 'sprite', 'gingerale' or 'icedtea'"
        with pytest.raises(ValidationError) as e:
            await orders_repo.create(OrderCreateSchema(items=[{"product": "noproduct", "size": "small"}]))

        assert e.value.errors()[0]["msg"] == msg

    @pytest.mark.asyncio
    async def test_that_an_order_should_fail_to_create_with_quantity_incorrect_size(
        self, orders_repo: OrdersRepository
    ):
        with pytest.raises(ValidationError) as e:
            await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "nosize"}]))

        assert e.value.errors()[0]["msg"] == "Input should be 'small', 'medium', 'large' or 'xlarge'"

    @pytest.mark.asyncio
    async def test_that_an_order_should_fail_to_create_with_no_items(self, orders_repo: OrdersRepository):
        with pytest.raises(ValidationError) as e:
            await orders_repo.create(OrderCreateSchema(items=[]))

        assert e.value.errors()[0]["msg"] == "List should have at least 1 item after validation, not 0"

    # Orders Get Happy Path

    @pytest.mark.asyncio
    async def test_that_an_order_is_retrieved_by_id(self, orders_repo: OrdersRepository):
        quantity = 5
        items = [{"product": "cheese", "size": "small"}, {"product": "sprite", "size": "xlarge", "quantity": quantity}]

        response = await orders_repo.create(OrderCreateSchema(items=items))
        order_id = response.id

        response = await orders_repo.get(order_id)

        assert response.id == order_id
        assert response.created is not None
        assert response.status == Status.CREATED
        assert len(response.items) == 2
        assert response.items[0].id is not None
        assert response.items[0].product == Product.CHEESE
        assert response.items[0].size == Size.SMALL
        assert response.items[0].quantity == 1
        assert response.items[1].id is not None
        assert response.items[1].product == Product.SPRITE
        assert response.items[1].size == Size.XLARGE
        assert response.items[1].quantity == quantity

    # Orders Get Sad Path

    @pytest.mark.asyncio
    async def test_that_an_order_fails_to_retrieved_by_id_with_incorrect_id(self, orders_repo: OrdersRepository):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "small"}]))
        order_id = response.id

        fake_order_id = uuid4()

        with pytest.raises(OrderEntityNotFoundError) as e:
            await orders_repo.get(fake_order_id)

        assert e.value.message == f"Order with ID {fake_order_id} not found"
        assert order_id != fake_order_id

    # Orders Update Happy Path

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "product,size,quantity",
        [(Product.GINGERALE, Size.LARGE, 6), (Product.HAWAIIAN, Size.XLARGE, 2)],
    )
    async def test_that_an_order_is_updated_by_id_with_product_size_and_quantity(
        self, orders_repo: OrdersRepository, product: Product, size: Size, quantity: int
    ):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "small"}]))
        order_id = response.id

        response = await orders_repo.update(
            order_id, OrderCreateSchema(items=[{"product": product, "size": size, "quantity": quantity}])
        )

        assert response.id == order_id
        assert response.created is not None
        assert response.status == Status.CREATED
        assert len(response.items) == 1
        assert response.items[0].id is not None
        assert response.items[0].product == product
        assert response.items[0].size == size
        assert response.items[0].quantity == quantity

    # Orders Update Sad Path

    @pytest.mark.asyncio
    async def test_that_an_order_should_fail_to_update_by_id_with_no_items(self, orders_repo: OrdersRepository):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "small"}]))
        order_id = response.id

        with pytest.raises(ValidationError) as e:
            await orders_repo.update(order_id, OrderCreateSchema(items=[]))

        assert e.value.errors()[0]["msg"] == "List should have at least 1 item after validation, not 0"

    @pytest.mark.asyncio
    async def test_that_an_order_fails_to_update_by_id_with_incorrect_id(self, orders_repo: OrdersRepository):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "sprite", "size": "xlarge"}]))
        order_id = response.id
        fake_order_id = uuid4()

        with pytest.raises(OrderEntityNotFoundError) as e:
            await orders_repo.update(fake_order_id, OrderCreateSchema(items=[{"product": "sprite", "size": "xlarge"}]))

        assert e.value.message == f"Order with ID {fake_order_id} not found"
        assert order_id != fake_order_id

    # Orders Delete Happy Path

    @pytest.mark.asyncio
    async def test_that_an_order_is_deleted_by_id(self, orders_repo: OrdersRepository):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "small"}]))
        order_id = response.id

        await orders_repo.delete(order_id)

        with pytest.raises(OrderEntityNotFoundError) as e:
            await orders_repo.get(order_id)

        assert e.value.message == f"Order with ID {order_id} not found"

    # Orders Delete Sad Path

    @pytest.mark.asyncio
    async def test_that_an_order_fails_to_delete_by_id_with_incorrect_id(self, orders_repo: OrdersRepository):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "sprite", "size": "xlarge"}]))
        order_id = response.id

        fake_order_id = uuid4()

        with pytest.raises(OrderEntityNotFoundError) as e:
            await orders_repo.delete(fake_order_id)

        assert e.value.message == f"Order with ID {fake_order_id} not found"
        assert order_id != fake_order_id

    # Orders Cancel Happy Path

    @pytest.mark.asyncio
    async def test_that_an_order_is_canceled_by_id(self, orders_repo: OrdersRepository):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "small"}]))
        order_id = response.id

        assert response.status == Status.CREATED

        response = await orders_repo.cancel(order_id)

        assert response.id == order_id
        assert response.status == Status.CANCELLED

    # Orders Cancel Sad Path

    @pytest.mark.asyncio
    async def test_that_an_order_fails_to_cancel_by_id_with_incorrect_id(self, orders_repo: OrdersRepository):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "sprite", "size": "xlarge"}]))
        order_id = response.id

        fake_order_id = uuid4()

        with pytest.raises(OrderEntityNotFoundError) as e:
            await orders_repo.cancel(fake_order_id)

        assert e.value.message == f"Order with ID {fake_order_id} not found"
        assert order_id != fake_order_id

    # Orders Pay Happy Path

    @pytest.mark.asyncio
    async def test_that_an_order_is_paid_by_id(self, orders_repo: OrdersRepository):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "cheese", "size": "small"}]))
        order_id = response.id

        assert response.status == Status.CREATED

        response = await orders_repo.pay(order_id)

        assert response.id == order_id
        assert response.status == Status.PAID

    # Orders Pay Sad Path

    @pytest.mark.asyncio
    async def test_that_an_order_fails_to_pay_by_id_with_incorrect_id(self, orders_repo: OrdersRepository):
        response = await orders_repo.create(OrderCreateSchema(items=[{"product": "sprite", "size": "xlarge"}]))
        order_id = response.id

        fake_order_id = uuid4()

        with pytest.raises(OrderEntityNotFoundError) as e:
            await orders_repo.pay(fake_order_id)

        assert e.value.message == f"Order with ID {fake_order_id} not found"
        assert order_id != fake_order_id
