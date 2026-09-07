from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import Product
from ..schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)


router = APIRouter(
    prefix="/api/products",
    tags=["Products"],
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
    response_model=list[ProductResponse],
)
def list_products(
    search: str | None = Query(
        default=None,
        description="Search by product name, SKU, brand, category, or description.",
    ),
    category: str | None = Query(
        default=None,
        description="Filter products by category.",
    ),
    brand: str | None = Query(
        default=None,
        description="Filter products by brand.",
    ),
    active: bool | None = Query(
        default=True,
        description="Filter by active status.",
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Product)

    if active is not None:
        query = query.filter(Product.active == active)

    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))

    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))

    if search:
        search_pattern = f"%{search}%"

        query = query.filter(
            (
                Product.name.ilike(search_pattern)
                | Product.sku.ilike(search_pattern)
                | Product.brand.ilike(search_pattern)
                | Product.category.ilike(search_pattern)
                | Product.description.ilike(search_pattern)
            )
        )

    return query.order_by(Product.id).all()


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
):
    existing_product = (
        db.query(Product)
        .filter(Product.sku == product_data.sku)
        .first()
    )

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_error(
                "DUPLICATE_SKU",
                "A product with this SKU already exists.",
            ),
        )

    product = Product(
        sku=product_data.sku,
        name=product_data.name,
        category=product_data.category,
        brand=product_data.brand,
        description=product_data.description,
        price=product_data.price,
        image_url=product_data.image_url,
        active=product_data.active,
    )

    try:
        db.add(product)
        db.commit()
        db.refresh(product)
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_error(
                "PRODUCT_CREATE_FAILED",
                "The product could not be created because of a database constraint.",
            ),
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error("PRODUCT_CREATE_FAILED", "The product could not be created."),
        )

    return product


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(
                "PRODUCT_NOT_FOUND",
                "Product not found.",
            ),
        )

    return product


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(
                "PRODUCT_NOT_FOUND",
                "Product not found.",
            ),
        )

    update_data = product_data.model_dump(
        exclude_unset=True
    )

    if "sku" in update_data:
        existing_product = (
            db.query(Product)
            .filter(
                Product.sku == update_data["sku"],
                Product.id != product_id,
            )
            .first()
        )

        if existing_product:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=_error(
                    "DUPLICATE_SKU",
                    "A product with this SKU already exists.",
                ),
            )

    for field, value in update_data.items():
        setattr(product, field, value)

    try:
        db.commit()
        db.refresh(product)
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_error(
                "PRODUCT_UPDATE_FAILED",
                "The product could not be updated because of a database constraint.",
            ),
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error("PRODUCT_UPDATE_FAILED", "The product could not be updated."),
        )

    return product


@router.delete(
    "/{product_id}",
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(
                "PRODUCT_NOT_FOUND",
                "Product not found.",
            ),
        )

    product.active = False

    try:
        db.commit()
    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error(
                "PRODUCT_DELETE_FAILED",
                "The product could not be deactivated.",
            ),
        )

    return {
        "success": True,
        "message": "Product deactivated successfully.",
        "product_id": product_id,
    }