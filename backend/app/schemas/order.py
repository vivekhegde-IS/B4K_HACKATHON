from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .customer import CustomerResponse


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int = Field(ge=1)
    unit_price: float = Field(ge=0)


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_number: str
    customer: CustomerResponse
    delivery_date: datetime
    status: str
    items: list[OrderItemResponse]
