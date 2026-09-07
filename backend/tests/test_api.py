from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database.database import (
    get_db,
)
from backend.app.database.models import (
    Base,
    Customer,
    Inventory,
    Order,
    OrderItem,
    Product,
)
from backend.app.main import app


@pytest.fixture
def client(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={
            "check_same_thread": False,
        },
    )

    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    db = session_factory()

    customer = Customer(
        name="Test Customer",
        email="test@example.com",
    )

    pi = Product(
        sku="TEST-PI",
        name="Test Pi",
        category="Electronics",
        brand="Test",
        price=10,
    )

    unknown = Product(
        sku="TEST-UNKNOWN",
        name="Unknown",
        category="Unclassified",
        brand="Test",
        price=10,
    )

    db.add_all(
        [
            customer,
            pi,
            unknown,
        ]
    )

    db.flush()

    db.add_all(
        [
            Inventory(
                product_id=pi.id,
                quantity=8,
                aisle="A3",
                shelf="S2",
            ),
            Inventory(
                product_id=unknown.id,
                quantity=2,
            ),
        ]
    )

    recent = Order(
        order_number="TEST-RECENT",
        customer_id=customer.id,
        delivery_date=datetime.now() - timedelta(days=2),
        status="DELIVERED",
    )

    ambiguous = Order(
        order_number="TEST-AMBIGUOUS",
        customer_id=customer.id,
        delivery_date=datetime.now() - timedelta(days=2),
        status="DELIVERED",
    )

    db.add_all(
        [
            recent,
            ambiguous,
        ]
    )

    db.flush()

    db.add_all(
        [
            OrderItem(
                order_id=recent.id,
                product_id=pi.id,
                quantity=1,
                unit_price=10,
            ),
            OrderItem(
                order_id=ambiguous.id,
                product_id=unknown.id,
                quantity=1,
                unit_price=10,
            ),
        ]
    )

    db.commit()
    db.close()

    def override_get_db():
        session = session_factory()

        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def valid_return(
    order_number="TEST-RECENT",
    product_id=1,
    product_identifier="TEST-PI",
):
    return {
        "order_number": order_number,
        "product_id": product_id,
        "reason": "damaged",
        "product_identifier": product_identifier,
        "accessories_complete": True,
        "product_unused": True,
        "product_undamaged": True,
        "packaging_undamaged": True,
    }


def test_health_and_product_search(client):
    health = client.get("/health")

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
    }

    response = client.get(
        "/api/products",
        params={
            "search": "TEST-PI",
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["sku"] == "TEST-PI"


def test_product_create_duplicate_and_deactivation(client):
    product = client.post(
        "/api/products",
        json={
            "sku": "NEW-1",
            "name": "New",
            "category": "Books",
            "brand": "Test",
            "price": 5,
        },
    )

    assert product.status_code == 201

    duplicate = client.post(
        "/api/products",
        json={
            "sku": "NEW-1",
            "name": "Duplicate",
            "category": "Books",
            "brand": "Test",
            "price": 5,
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_SKU"

    product_id = product.json()["id"]

    deleted = client.delete(
        f"/api/products/{product_id}"
    )

    assert deleted.status_code == 200

    fetched = client.get(
        f"/api/products/{product_id}"
    )

    assert fetched.status_code == 200
    assert fetched.json()["active"] is False


def test_live_inventory_and_negative_validation(client):
    initial = client.get(
        "/api/inventory/1"
    )

    assert initial.status_code == 200
    assert initial.json()["quantity"] == 8

    updated_zero = client.put(
        "/api/inventory/1",
        json={
            "quantity": 0,
        },
    )

    assert updated_zero.status_code == 200
    assert updated_zero.json()["quantity"] == 0

    live_value = client.get(
        "/api/inventory/1"
    )

    assert live_value.status_code == 200
    assert live_value.json()["quantity"] == 0

    negative = client.put(
        "/api/inventory/1",
        json={
            "quantity": -1,
        },
    )

    assert negative.status_code == 422

    restored = client.put(
        "/api/inventory/1",
        json={
            "quantity": 8,
        },
    )

    assert restored.status_code == 200
    assert restored.json()["quantity"] == 8


def test_order_and_missing_order_contract(client):
    order = client.get(
        "/api/orders/TEST-RECENT"
    )

    assert order.status_code == 200

    order_data = order.json()

    assert order_data["order_number"] == "TEST-RECENT"
    assert order_data["status"] == "DELIVERED"
    assert order_data["customer"]["name"] == "Test Customer"
    assert len(order_data["items"]) == 1

    missing = client.get(
        "/api/orders/MISSING"
    )

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ORDER_NOT_FOUND"


def test_eligibility_states_and_return_creation(client):
    eligible_request = valid_return()

    eligible = client.post(
        "/api/returns/check-eligibility",
        json=eligible_request,
    )

    assert eligible.status_code == 200
    assert eligible.json()["status"] == "ELIGIBLE"
    assert eligible.json()["eligible"] is True

    ambiguous_request = valid_return(
        order_number="TEST-AMBIGUOUS",
        product_id=2,
        product_identifier="TEST-UNKNOWN",
    )

    ambiguous = client.post(
        "/api/returns/check-eligibility",
        json=ambiguous_request,
    )

    assert ambiguous.status_code == 200
    assert ambiguous.json()["status"] == "AMBIGUOUS"
    assert ambiguous.json()["eligible"] is False

    created = client.post(
        "/api/returns",
        json=eligible_request,
    )

    assert created.status_code == 201

    ticket = created.json()

    assert ticket["ticket_number"].startswith(
        "RET-"
    )
    assert ticket["order_number"] == "TEST-RECENT"
    assert ticket["product_id"] == 1
    assert ticket["status"] == "CREATED"

    rejected = client.post(
        "/api/returns",
        json=ambiguous_request,
    )

    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "RETURN_NOT_ELIGIBLE"


def test_exchange_not_allowed_for_electronics(client):
    response = client.post(
        "/api/exchanges/check-eligibility",
        json=valid_return(),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "INELIGIBLE"