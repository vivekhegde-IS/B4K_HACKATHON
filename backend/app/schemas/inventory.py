from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InventoryBase(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=0)
    aisle: str | None = None
    shelf: str | None = None


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    aisle: str | None = None
    shelf: str | None = None


class InventoryResponse(InventoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime
