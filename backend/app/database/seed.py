from datetime import datetime, timedelta, timezone

from .database import SessionLocal, init_db
from .models import (
    Customer,
    Inventory,
    Order,
    OrderItem,
    Product,
)


def get_or_create_product(
    db,
    sku,
    name,
    category,
    brand,
    description,
    price,
):
    product = (
        db.query(Product)
        .filter(Product.sku == sku)
        .first()
    )

    if product:
        return product

    product = Product(
        sku=sku,
        name=name,
        category=category,
        brand=brand,
        description=description,
        price=price,
        active=True,
    )

    db.add(product)
    db.flush()

    return product


def get_or_create_inventory(
    db,
    product_id,
    quantity,
    aisle,
    shelf,
):
    inventory = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .first()
    )

    if inventory:
        return inventory

    inventory = Inventory(
        product_id=product_id,
        quantity=quantity,
        aisle=aisle,
        shelf=shelf,
    )

    db.add(inventory)
    db.flush()

    return inventory


def get_or_create_customer(
    db,
    name,
    email,
    phone,
):
    customer = (
        db.query(Customer)
        .filter(Customer.email == email)
        .first()
    )

    if customer:
        return customer

    customer = Customer(
        name=name,
        email=email,
        phone=phone,
    )

    db.add(customer)
    db.flush()

    return customer


def get_or_create_order(
    db,
    order_number,
    customer_id,
    delivery_date,
    status,
):
    order = (
        db.query(Order)
        .filter(Order.order_number == order_number)
        .first()
    )

    if order:
        return order

    order = Order(
        order_number=order_number,
        customer_id=customer_id,
        delivery_date=delivery_date,
        status=status,
    )

    db.add(order)
    db.flush()

    return order


def get_or_create_order_item(
    db,
    order_id,
    product_id,
    quantity,
    unit_price,
):
    item = (
        db.query(OrderItem)
        .filter(
            OrderItem.order_id == order_id,
            OrderItem.product_id == product_id,
        )
        .first()
    )

    if item:
        return item

    item = OrderItem(
        order_id=order_id,
        product_id=product_id,
        quantity=quantity,
        unit_price=unit_price,
    )

    db.add(item)
    db.flush()

    return item


def seed_database():
    init_db()

    db = SessionLocal()

    try:
        # =========================================================
        # PRODUCTS
        # =========================================================

        raspberry_pi = get_or_create_product(
            db=db,
            sku="RPI5-8GB",
            name="Raspberry Pi 5 8GB",
            category="Electronics",
            brand="Raspberry Pi",
            description=(
                "Raspberry Pi 5 single-board computer "
                "with 8GB RAM."
            ),
            price=8999.00,
        )

        arduino = get_or_create_product(
            db=db,
            sku="ARD-UNO-R3",
            name="Arduino Uno R3",
            category="Unclassified",
            brand="Arduino",
            description="Arduino Uno R3 development board.",
            price=799.00,
        )

        # =========================================================
        # INVENTORY
        # =========================================================

        get_or_create_inventory(
            db=db,
            product_id=raspberry_pi.id,
            quantity=8,
            aisle="A3",
            shelf="S2",
        )

        get_or_create_inventory(
            db=db,
            product_id=arduino.id,
            quantity=15,
            aisle="A3",
            shelf="S3",
        )

        # =========================================================
        # CUSTOMER
        # =========================================================

        customer = get_or_create_customer(
            db=db,
            name="Demo Customer",
            email="demo@retailmate.local",
            phone="9999999999",
        )

        # =========================================================
        # ORDERS
        #
        # ORD-10001 -> eligible test order
        # ORD-10002 -> expired return-window test order
        # ORD-10003 -> ambiguous-policy test order
        # =========================================================

        now = datetime.now(timezone.utc).replace(tzinfo=None)

        order_10001 = get_or_create_order(
            db=db,
            order_number="ORD-10001",
            customer_id=customer.id,
            delivery_date=now - timedelta(days=2),
            status="DELIVERED",
        )

        order_10002 = get_or_create_order(
            db=db,
            order_number="ORD-10002",
            customer_id=customer.id,
            delivery_date=now - timedelta(days=30),
            status="DELIVERED",
        )

        order_10003 = get_or_create_order(
            db=db,
            order_number="ORD-10003",
            customer_id=customer.id,
            delivery_date=now - timedelta(days=2),
            status="DELIVERED",
        )

        # =========================================================
        # ORDER ITEMS
        # =========================================================

        get_or_create_order_item(
            db=db,
            order_id=order_10001.id,
            product_id=raspberry_pi.id,
            quantity=1,
            unit_price=raspberry_pi.price,
        )

        get_or_create_order_item(
            db=db,
            order_id=order_10002.id,
            product_id=raspberry_pi.id,
            quantity=1,
            unit_price=raspberry_pi.price,
        )

        get_or_create_order_item(
            db=db,
            order_id=order_10003.id,
            product_id=arduino.id,
            quantity=1,
            unit_price=arduino.price,
        )

        # =========================================================
        # COMMIT
        # =========================================================

        db.commit()

        print("Database seed completed successfully.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()