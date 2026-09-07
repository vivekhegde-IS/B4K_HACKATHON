import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from ..database.models import Order, OrderItem, Product


POLICY_PATH = Path(__file__).resolve().parents[2] / "data" / "policy" / "retailmate_policy.json"


def load_policy() -> dict[str, Any]:
    with POLICY_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _normalise(value: str | None) -> str:
    return " ".join(value.lower().replace("-", " ").split()) if value else ""


def _find_order_item(db: Session, order_number: str, product_id: int):
    order = db.query(Order).filter(Order.order_number == order_number).first()
    if not order:
        return None, None, None
    item = db.query(OrderItem).filter(
        OrderItem.order_id == order.id, OrderItem.product_id == product_id
    ).first()
    if not item:
        return order, None, None
    return order, item, db.query(Product).filter(Product.id == product_id).first()


def _product_rule_matches(product: Product, rule: dict[str, Any]) -> bool:
    if rule.get("sku") and _normalise(product.sku) == _normalise(rule["sku"]):
        return True
    if rule.get("product_id") and product.id == rule["product_id"]:
        return True
    return bool(rule.get("name") and _normalise(product.name) == _normalise(rule["name"]))


def _resolve_rule(product: Product, policy_type: str, policy: dict[str, Any]):
    product_matches = [
        rule
        for rule in policy.get("product_rules", {}).get(policy_type, [])
        if _product_rule_matches(product, rule)
    ]
    if len(product_matches) == 1:
        return product_matches[0], "product-specific"
    if len(product_matches) > 1:
        return None, None

    category = _normalise(product.category)
    matches = [
        rule for rule in policy.get(policy_type, {}).get("categories", [])
        if category and category in {
            _normalise(rule.get("name")),
            *(_normalise(alias) for alias in rule.get("category_aliases", [])),
        }
    ]
    return (matches[0], "category") if len(matches) == 1 else (None, None)


def _check_pickup_conditions(request: Any, rule: dict[str, Any]):
    ambiguous: list[str] = []
    failed: list[str] = []
    fields = {
        "product_identifier": (request.product_identifier, "Product identifier"),
        "accessories_complete": (request.accessories_complete, "Accessories/freebies/combos"),
        "product_unused": (request.product_unused, "Unused product condition"),
        "product_undamaged": (request.product_undamaged, "Product condition"),
        "packaging_undamaged": (request.packaging_undamaged, "Original packaging condition"),
        "device_formatted": (request.device_formatted, "Device formatting"),
        "device_unlocked": (request.device_unlocked, "Screen lock status"),
        "icloud_lock_disabled": (request.icloud_lock_disabled, "iCloud lock status"),
        "installation_done_by_authorized_person": (request.installation_done_by_authorized_person, "Authorized installation"),
    }
    for field_name in rule.get("required_conditions", []):
        value, label = fields[field_name]
        if value is None or (field_name == "product_identifier" and not value.strip()):
            ambiguous.append(f"{label} must be confirmed.")
        elif value is False:
            failed.append(f"{label} condition failed.")
    return ambiguous, failed


def _result(state: str, message: str, reasons: list[str]) -> dict[str, Any]:
    return {"status": state, "eligible": state == "ELIGIBLE", "message": message, "reasons": reasons}


def check_eligibility(db: Session, request: Any, requested_action: str = "RETURN") -> dict[str, Any]:
    policy = load_policy()
    order, order_item, product = _find_order_item(db, request.order_number, request.product_id)
    if not order:
        return _result("INELIGIBLE", "Order not found.", ["The supplied order number does not exist."])
    if not order_item or not product:
        return _result("INELIGIBLE", "Product not found in the order.", ["The supplied product is not part of the specified order."])

    policy_type = "hyperlocal" if "hyperlocal" in _normalise(order.status) else "standard"
    no_return_categories = {
        _normalise(value)
        for value in policy.get(policy_type, {}).get("no_return_categories", [])
    }
    if _normalise(product.category) in no_return_categories:
        return _result("INELIGIBLE", "This product category is not returnable.", ["The source policy excludes this category."])

    rule, source = _resolve_rule(product, policy_type, policy)
    if not rule:
        return _result("AMBIGUOUS", "Applicable return policy could not be determined.", [f"Product category '{product.category}' has no unique {policy_type} policy rule."])

    delivery_date = order.delivery_date
    if delivery_date is None:
        return _result("AMBIGUOUS", "Delivery date is required.", ["The order has no delivery date."])
    if delivery_date.tzinfo is not None:
        delivery_date = delivery_date.astimezone(timezone.utc).replace(tzinfo=None)
    days_since_delivery = (datetime.now(timezone.utc).replace(tzinfo=None) - delivery_date).days
    window_days = rule.get("window_days")
    if window_days is None:
        return _result("AMBIGUOUS", "Return window could not be determined.", ["The applicable policy rule has no return window."])
    if days_since_delivery < 0 or days_since_delivery > window_days:
        return _result("INELIGIBLE", "Return window has expired.", [f"The applicable return window is {window_days} days."])

    actions = {str(action).upper() for action in rule.get("actions", [])}
    requested_action = requested_action.upper()
    if requested_action == "EXCHANGE" and "EXCHANGE" not in actions:
        return _result("INELIGIBLE", "Exchange is not an allowed action for this product.", ["The applicable policy does not allow exchange."])
    if requested_action == "RETURN" and not actions.intersection({"REFUND", "REPLACEMENT", "REPAIR"}):
        return _result("INELIGIBLE", "Return is not an allowed action for this product.", ["The applicable policy has no return action."])

    ambiguous, failed = _check_pickup_conditions(request, rule)
    if failed:
        return _result("INELIGIBLE", "Return conditions were not satisfied.", failed)
    if ambiguous:
        return _result("AMBIGUOUS", "Additional product condition information is required.", ambiguous)
    return _result("ELIGIBLE", "Return/exchange request is eligible under the applicable policy.", [f"Used {source} {policy_type} policy rule.", f"Within the {window_days}-day return window.", f"Allowed actions: {', '.join(sorted(actions))}."])
