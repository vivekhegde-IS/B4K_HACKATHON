from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..database.models import ReturnTicket
from ..schemas.return_ticket import (
    EligibilityStatus,
    ReturnCreateRequest,
    ReturnEligibilityRequest,
    ReturnEligibilityResponse,
    ReturnTicketResponse,
)
from ..services.eligibility import check_eligibility


router = APIRouter(
    prefix="/api/returns",
    tags=["Returns"],
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
    Generate a unique return ticket number.
    """

    ticket_number = f"RET-{uuid4().hex[:20].upper()}"

    existing_ticket = (
        db.query(ReturnTicket)
        .filter(
            ReturnTicket.ticket_number == ticket_number
        )
        .first()
    )

    if existing_ticket:
        return _generate_ticket_number(db)

    return ticket_number


@router.post(
    "/check-eligibility",
    response_model=ReturnEligibilityResponse,
)
def check_return_eligibility(
    request: ReturnEligibilityRequest,
    db: Session = Depends(get_db),
):
    """
    Check whether a return request is eligible.

    The deterministic eligibility engine is the
    final authority.
    """

    result = check_eligibility(
        db=db,
        request=request,
        requested_action="RETURN",
    )

    return ReturnEligibilityResponse(
        status=EligibilityStatus(
            result["status"]
        ),
        eligible=result["eligible"],
        message=result["message"],
        reasons=result["reasons"],
    )


@router.post(
    "",
    response_model=ReturnTicketResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_return(
    request: ReturnCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Create a return ticket only when the request
    passes deterministic eligibility.
    """

    eligibility_request = ReturnEligibilityRequest(
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
        requested_action="RETURN",
    )

    if result["status"] != EligibilityStatus.ELIGIBLE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_error(
                "RETURN_NOT_ELIGIBLE",
                result["message"],
            ),
        )

    ticket = ReturnTicket(
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
                "RETURN_CREATE_FAILED",
                (
                    "Return ticket could not be created "
                    "because of a database constraint."
                ),
            ),
        )

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=_error(
                "RETURN_CREATE_FAILED",
                "Return ticket could not be created.",
            ),
        )

    return ticket


@router.get(
    "",
    response_model=list[ReturnTicketResponse],
)
def list_returns(
    db: Session = Depends(get_db),
):
    """
    Return all return tickets.
    """

    return (
        db.query(ReturnTicket)
        .order_by(ReturnTicket.created_at.desc())
        .all()
    )


@router.get(
    "/{ticket_number}",
    response_model=ReturnTicketResponse,
)
def get_return(
    ticket_number: str,
    db: Session = Depends(get_db),
):
    """
    Return a specific return ticket.
    """

    ticket = (
        db.query(ReturnTicket)
        .filter(
            ReturnTicket.ticket_number == ticket_number
        )
        .first()
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=_error(
                "RETURN_TICKET_NOT_FOUND",
                "Return ticket not found.",
            ),
        )

    return ticket