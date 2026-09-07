from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import Inventory, Product
from ..schemas.inventory import (
    InventoryResponse,
    InventoryUpdate,
)


router = APIRouter(
    prefix="/api/inventory",
    tags=["Inventory"],
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
    "",
    response_model=list[InventoryResponse],
)
def list_inventory(
    product_id: int | None = Query(
        default=None,
        gt=0,
        description="Filter inventory by product ID.",
    ),
    low_stock: int | None = Query(
        default=None,
        ge=0,
        description="Return products with quantity at or below this value.",
    ),
    db: Session = Depends(get_db),
):
    """
    Return current inventory directly from SQLite.

    Inventory is intentionally queried on every request so that
    quantity changes are immediately reflected.
    """

    query = db.query(Inventory)

    if product_id is not None:
        query = query.filter(
            Inventory.product_id == product_id
        )

    if low_stock is not None:
        query = query.filter(
            Inventory.quantity <= low_stock
        )

    return query.order_by(Inventory.product_id).all()


@router.get(
    "/{product_id}",
    response_model=InventoryResponse,
)
def get_inventory(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Return the current inventory record for a product.
    """

    inventory = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .first()
    )

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(
                "INVENTORY_NOT_FOUND",
                "Inventory record not found for this product.",
            ),
        )

    return inventory


@router.put(
    "/{product_id}",
    response_model=InventoryResponse,
)
def update_inventory(
    product_id: int,
    inventory_data: InventoryUpdate,
    db: Session = Depends(get_db),
):
    """
    Update the authoritative inventory record in SQLite.
    """

    inventory = (
        db.query(Inventory)
        .filter(Inventory.product_id == product_id)
        .first()
    )

    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(
                "INVENTORY_NOT_FOUND",
                "Inventory record not found for this product.",
            ),
        )

    update_data = inventory_data.model_dump(
        exclude_unset=True
    )

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error(
                "NO_UPDATE_FIELDS",
                "At least one inventory field must be provided.",
            ),
        )

    for field, value in update_data.items():
        setattr(inventory, field, value)

    try:
        db.commit()
        db.refresh(inventory)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_error(
                "INVENTORY_UPDATE_FAILED",
                "Inventory could not be updated because of a database constraint.",
            ),
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error(
                "INVENTORY_UPDATE_FAILED",
                "Inventory could not be updated.",
            ),
        )

    return inventory