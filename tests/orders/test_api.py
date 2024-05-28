from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import status
from fastapi.testclient import TestClient

from orders_service.app import app
from orders_service.config import get_config
from orders_service.session import begin_session_create_tables, end_session, init_session_manager


class TestOrdersAPI:
    """Test Orders API"""

    @pytest_asyncio.fixture
    async def orders_client(self):
        init_session_manager(get_config("orders_service/.env.test").DATABASE_URL)
        await begin_session_create_tables()
        client = TestClient(app)
        client.base_url = f"{client.base_url}/v1/orders"
        yield client
        await end_session()

    # Orders List Happy Path

    def test_that_list_orders_should_be_empty(self, orders_client: TestClient):
        response = orders_client.get("/")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["orders"]) == 0

    def test_that_list_orders_should_retrieve_4_orders(self, orders_client: TestClient):
        orders_client.post("/", json={"items": [{"product": "cheese", "size": "small"}]})
        orders_client.post("/", json={"items": [{"product": "pepperoni", "size": "medium"}]})
        orders_client.post("/", json={"items": [{"product": "coke", "size": "large"}]})
        orders_client.post("/", json={"items": [{"product": "gingerale", "size": "xlarge"}]})

        response = orders_client.get("/")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["orders"]) == 4

    @pytest.mark.parametrize("cancelled,count", [(True, 1), (False, 3)])
    def test_that_list_orders_should_retrieve_filtered_orders(
        self,
        orders_client: TestClient,
        cancelled: bool,
        count: int,
    ):
        orders_client.post("/", json={"items": [{"product": "cheese", "size": "small"}]})
        orders_client.post("/", json={"items": [{"product": "pepperoni", "size": "medium"}]})
        orders_client.post("/", json={"items": [{"product": "coke", "size": "large"}]})
        response = orders_client.post("/", json={"items": [{"product": "gingerale", "size": "xlarge"}]})
        order_id = response.json()["id"]

        orders_client.post(f"/{order_id}/cancel")

        response = orders_client.get("/")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["orders"]) == 4

        response = orders_client.get(f"/?cancelled={cancelled}")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["orders"]) == count

    @pytest.mark.parametrize("limit,expected_limit", [(1, 1), (5, 5), (10, 5)])
    def test_that_list_orders_should_retrieve_limited_orders(
        self,
        orders_client: TestClient,
        limit: int,
        expected_limit: int,
    ):
        orders_client.post("/", json={"items": [{"product": "cheese", "size": "small"}]})
        orders_client.post("/", json={"items": [{"product": "pepperoni", "size": "medium"}]})
        orders_client.post("/", json={"items": [{"product": "hawaiian", "size": "xlarge"}]})
        orders_client.post("/", json={"items": [{"product": "coke", "size": "large"}]})
        orders_client.post("/", json={"items": [{"product": "gingerale", "size": "xlarge"}]})

        response = orders_client.get("/")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["orders"]) == 5

        response = orders_client.get(f"/?limit={limit}")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert len(data["orders"]) == expected_limit

    # Orders List Sad Path

    @pytest.mark.parametrize(
        "limit,msg",
        [(0, "Input should be greater than or equal to 1"), (11, "Input should be less than or equal to 10")],
    )
    def test_that_list_orders_should_fail_to_retrieve_limited_orders_out_of_range(
        self,
        orders_client: TestClient,
        limit: int,
        msg: str,
    ):
        response = orders_client.get(f"/?limit={limit}")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json()["detail"][0]["msg"] == msg

    # Orders Create Happy Path

    def test_that_an_order_is_created_with_default_quantity(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "cheese", "size": "small"}]})
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["id"] is not None
        assert data["created"] is not None
        assert data["status"] == "created"
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] is not None
        assert data["items"][0]["product"] == "cheese"
        assert data["items"][0]["size"] == "small"
        assert data["items"][0]["quantity"] == 1

    @pytest.mark.parametrize("product,size,quantity", [("coke", "large", 4), ("icedtea", "medium", 10)])
    def test_that_an_order_is_created_with_product_size_and_quantity(
        self, orders_client: TestClient, product: str, size: str, quantity: int
    ):
        response = orders_client.post("/", json={"items": [{"product": product, "size": size, "quantity": quantity}]})
        data = response.json()

        assert response.status_code == status.HTTP_201_CREATED
        assert data["id"] is not None
        assert data["created"] is not None
        assert data["status"] == "created"
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] is not None
        assert data["items"][0]["product"] == product
        assert data["items"][0]["size"] == size
        assert data["items"][0]["quantity"] == quantity

    # Orders Create Sad Path

    @pytest.mark.parametrize(
        "quantity,msg",
        [(0, "Input should be greater than or equal to 1"), (11, "Input should be less than or equal to 10")],
    )
    def test_that_an_order_should_fail_to_create_with_quantity_out_of_range(
        self, orders_client: TestClient, quantity: int, msg: str
    ):
        json = {"items": [{"product": "cheese", "size": "small", "quantity": quantity}]}
        response = orders_client.post("/", json=json)
        assert response.json()["detail"][0]["msg"] == msg

    def test_that_an_order_should_fail_to_create_with_incorrect_product(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "noproduct", "size": "small"}]})
        msg = "Input should be 'cheese', 'pepperoni', 'deluxe', 'hawaiian', 'canadian', 'veggie', 'coke', 'sprite', 'gingerale' or 'icedtea'"
        assert response.json()["detail"][0]["msg"] == msg

    def test_that_an_order_should_fail_to_create_with_quantity_incorrect_size(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "cheese", "size": "nosize"}]})
        assert response.json()["detail"][0]["msg"] == "Input should be 'small', 'medium', 'large' or 'xlarge'"

    def test_that_an_order_should_fail_to_create_with_no_items(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": []})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json()["detail"][0]["msg"] == "List should have at least 1 item after validation, not 0"

    # Orders Get Happy Path

    def test_that_an_order_is_retrieved_by_id(self, orders_client: TestClient):
        quantity = 5
        json = {
            "items": [
                {"product": "cheese", "size": "small"},
                {"product": "sprite", "size": "xlarge", "quantity": quantity},
            ]
        }

        response = orders_client.post("/", json=json)
        data = response.json()
        order_id = data["id"]

        response = orders_client.get(f"/{order_id}")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == order_id
        assert data["created"] is not None
        assert data["status"] == "created"
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] is not None
        assert data["items"][0]["product"] == "cheese"
        assert data["items"][0]["size"] == "small"
        assert data["items"][0]["quantity"] == 1
        assert data["items"][1]["id"] is not None
        assert data["items"][1]["product"] == "sprite"
        assert data["items"][1]["size"] == "xlarge"
        assert data["items"][1]["quantity"] == quantity

    # Orders Get Sad Path

    def test_that_an_order_fails_to_retrieved_by_id_with_incorrect_id(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "sprite", "size": "xlarge"}]})
        order_id = response.json()["id"]

        fake_order_id = uuid4()
        response = orders_client.get(f"/{fake_order_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == f"Order with ID {fake_order_id} not found"
        assert order_id != fake_order_id

    # Orders Update Happy Path

    @pytest.mark.parametrize("product,size,quantity", [("gingerale", "large", 6), ("hawaiian", "xlarge", 2)])
    def test_that_an_order_is_updated_by_id_with_product_size_and_quantity(
        self, orders_client: TestClient, product: str, size: str, quantity: int
    ):
        response = orders_client.post("/", json={"items": [{"product": "cheese", "size": "small"}]})
        order_id = response.json()["id"]

        response = orders_client.put(
            f"/{order_id}", json={"items": [{"product": product, "size": size, "quantity": quantity}]}
        )
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == order_id
        assert data["created"] is not None
        assert data["status"] == "created"
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] is not None
        assert data["items"][0]["product"] == product
        assert data["items"][0]["size"] == size
        assert data["items"][0]["quantity"] == quantity

    # Orders Update Sad Path

    def test_that_an_order_should_fail_to_update_by_id_with_no_items(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "cheese", "size": "small"}]})
        order_id = response.json()["id"]

        response = orders_client.put(f"/{order_id}", json={"items": []})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json()["detail"][0]["msg"] == "List should have at least 1 item after validation, not 0"

    def test_that_an_order_fails_to_update_by_id_with_incorrect_id(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "sprite", "size": "xlarge"}]})
        order_id = response.json()["id"]

        fake_order_id = uuid4()
        response = orders_client.put(f"/{fake_order_id}", json={"items": [{"product": "sprite", "size": "xlarge"}]})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == f"Order with ID {fake_order_id} not found"
        assert order_id != fake_order_id

    # Orders Delete Happy Path

    def test_that_an_order_is_deleted_by_id(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "cheese", "size": "small"}]})
        order_id = response.json()["id"]

        response = orders_client.delete(f"/{order_id}")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        response = orders_client.get(f"/{order_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == f"Order with ID {order_id} not found"

    # Orders Delete Sad Path

    def test_that_an_order_fails_to_delete_by_id_with_incorrect_id(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "sprite", "size": "xlarge"}]})
        order_id = response.json()["id"]

        fake_order_id = uuid4()
        response = orders_client.delete(f"/{fake_order_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == f"Order with ID {fake_order_id} not found"
        assert order_id != fake_order_id

    # Orders Cancel Happy Path

    def test_that_an_order_is_canceled_by_id(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "cheese", "size": "small"}]})
        data = response.json()
        order_id = data["id"]

        assert data["status"] == "created"

        response = orders_client.post(f"/{order_id}/cancel")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == order_id
        assert data["status"] == "cancelled"

    # Orders Cancel Sad Path

    def test_that_an_order_fails_to_cancel_by_id_with_incorrect_id(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "sprite", "size": "xlarge"}]})
        order_id = response.json()["id"]

        fake_order_id = uuid4()
        response = orders_client.post(f"/{fake_order_id}/cancel")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == f"Order with ID {fake_order_id} not found"
        assert order_id != fake_order_id

    # Orders Pay Happy Path

    def test_that_an_order_is_paid_by_id(self, orders_client: TestClient):
        response = orders_client.post("/", json={"items": [{"product": "cheese", "size": "small"}]})
        data = response.json()
        order_id = data["id"]

        assert data["status"] == "created"

        response = orders_client.post(f"/{order_id}/pay")
        data = response.json()

        assert response.status_code == status.HTTP_200_OK
        assert data["id"] == order_id
        assert data["status"] == "paid"

    # Orders Pay Sad Path

    def test_that_an_order_fails_to_pay_by_id_with_incorrect_id(self, orders_client: TestClient):
        fake_order_id = uuid4()

        response = orders_client.post("/", json={"items": [{"product": "sprite", "size": "xlarge"}]})
        order_id = response.json()["id"]

        response = orders_client.post(f"/{fake_order_id}/pay")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == f"Order with ID {fake_order_id} not found"
        assert order_id != fake_order_id
