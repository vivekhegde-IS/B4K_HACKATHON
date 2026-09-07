from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from ..database.database import get_db
from ..database.models import Order
from ..schemas.order import OrderResponse


router = APIRouter(
    prefix="/api/orders",
    tags=["Orders"],
)


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }


@router.get(
    "/{order_number}",
    response_model=OrderResponse,
)
def get_order(
    order_number: str,
    db: Session = Depends(get_db),
):
    """
    Return complete order information including customer and items.
    """

    order = (
        db.query(Order)
        .options(
            joinedload(Order.customer),
            joinedload(Order.items),
        )
        .filter(Order.order_number == order_number)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(
                "ORDER_NOT_FOUND",
                "Order not found.",
            ),
        )

    return order