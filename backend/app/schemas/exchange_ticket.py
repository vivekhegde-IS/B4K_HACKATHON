from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .return_ticket import EligibilityStatus


class ExchangeEligibilityRequest(BaseModel):
    order_number: str = Field(min_length=1, max_length=100)
    product_id: int = Field(gt=0)
    reason: str | None = None

    product_identifier: str | None = None
    accessories_complete: bool | None = None
    product_unused: bool | None = None
    product_undamaged: bool | None = None
    packaging_undamaged: bool | None = None
    device_unlocked: bool | None = None
    device_formatted: bool | None = None
    icloud_lock_disabled: bool | None = None
    installation_done_by_authorized_person: bool | None = None


class ExchangeEligibilityResponse(BaseModel):
    status: EligibilityStatus
    eligible: bool
    message: str
    reasons: list[str] = Field(default_factory=list)


class ExchangeCreateRequest(BaseModel):
    order_number: str = Field(min_length=1, max_length=100)
    product_id: int = Field(gt=0)
    reason: str = Field(min_length=1)

    product_identifier: str | None = None
    accessories_complete: bool | None = None
    product_unused: bool | None = None
    product_undamaged: bool | None = None
    packaging_undamaged: bool | None = None
    device_unlocked: bool | None = None
    device_formatted: bool | None = None
    icloud_lock_disabled: bool | None = None
    installation_done_by_authorized_person: bool | None = None


class ExchangeTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_number: str
    order_number: str
    product_id: int
    reason: str
    status: str
    created_at: datetime
