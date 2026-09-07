from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import ExchangeTicket
from ..schemas.exchange_ticket import (
    ExchangeCreateRequest,
    ExchangeEligibilityRequest,
    ExchangeEligibilityResponse,
    ExchangeTicketResponse,
)
from ..schemas.return_ticket import EligibilityStatus
from ..services.eligibility import check_eligibility


router = APIRouter(
    prefix="/api/exchanges",
    tags=["Exchanges"],
)


def _error(code: str, message: str) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _generate_ticket_number(db: Session) -> str:
    """
    Generate a unique exchange ticket number.
    """

    ticket_number = f"EXC-{uuid4().hex[:20].upper()}"

    existing_ticket = (
        db.query(ExchangeTicket)
        .filter(
            ExchangeTicket.ticket_number == ticket_number
        )
        .first()
    )

    if existing_ticket:
        return _generate_ticket_number(db)

    return ticket_number


@router.post(
    "/check-eligibility",
    response_model=ExchangeEligibilityResponse,
)
def check_exchange_eligibility(
    request: ExchangeEligibilityRequest,
    db: Session = Depends(get_db),
):
    """
    Check whether an exchange request is eligible.

    The deterministic eligibility engine is the
    final authority.
    """

    result = check_eligibility(
        db=db,
        request=request,
        requested_action="EXCHANGE",
    )

    return ExchangeEligibilityResponse(
        status=EligibilityStatus(
            result["status"]
        ),
        eligible=result["eligible"],
        message=result["message"],
        reasons=result["reasons"],
    )


@router.post(
    "",
    response_model=ExchangeTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_exchange(
    request: ExchangeCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Create an exchange ticket only when the request
    passes deterministic eligibility.
    """

    eligibility_request = ExchangeEligibilityRequest(
        order_number=request.order_number,
        product_id=request.product_id,
        reason=request.reason,
        product_identifier=request.product_identifier,
        accessories_complete=request.accessories_complete,
        product_unused=request.product_unused,
        product_undamaged=request.product_undamaged,
        packaging_undamaged=request.packaging_undamaged,
        device_unlocked=request.device_unlocked,
        device_formatted=request.device_formatted,
        icloud_lock_disabled=request.icloud_lock_disabled,
        installation_done_by_authorized_person=(
            request.installation_done_by_authorized_person
        ),
    )

    result = check_eligibility(
        db=db,
        request=eligibility_request,
        requested_action="EXCHANGE",
    )

    if result["status"] != EligibilityStatus.ELIGIBLE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error(
                "EXCHANGE_NOT_ELIGIBLE",
                result["message"],
            ),
        )

    ticket = ExchangeTicket(
        ticket_number=_generate_ticket_number(db),
        order_number=request.order_number,
        product_id=request.product_id,
        reason=request.reason,
        status="CREATED",
    )

    try:
        db.add(ticket)

        db.commit()

        db.refresh(ticket)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_error(
                "EXCHANGE_CREATE_FAILED",
                (
                    "Exchange ticket could not be created "
                    "because of a database constraint."
                ),
            ),
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error(
                "EXCHANGE_CREATE_FAILED",
                "Exchange ticket could not be created.",
            ),
        )

    return ticket


@router.get(
    "",
    response_model=list[ExchangeTicketResponse],
)
def list_exchanges(
    db: Session = Depends(get_db),
):
    """
    Return all exchange tickets.
    """

    return (
        db.query(ExchangeTicket)
        .order_by(ExchangeTicket.created_at.desc())
        .all()
    )


@router.get(
    "/{ticket_number}",
    response_model=ExchangeTicketResponse,
)
def get_exchange(
    ticket_number: str,
    db: Session = Depends(get_db),
):
    """
    Return a specific exchange ticket.
    """

    ticket = (
        db.query(ExchangeTicket)
        .filter(
            ExchangeTicket.ticket_number == ticket_number
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(
                "EXCHANGE_TICKET_NOT_FOUND",
                "Exchange ticket not found.",
            ),
        )

    return ticket