from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_main():
    response = client.get("/")
    print(response.json())
    assert response.status_code == 200
    assert response.json() == "Hello Ordering System Microservices"
