import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..database import get_db, SupportTicket, User, generate_custom_id
from ..auth import get_current_user

router = APIRouter(prefix="/api/support", tags=["Support"])


class TicketIn(BaseModel):
    issue_type: str
    description: str = ""
    ride_id: str = ""


@router.post("/")
async def raise_ticket(
    body: TicketIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    ticket = SupportTicket(
        id=generate_custom_id("TKT"),
        user_id=user.id,
        user_name=user.name,
        ride_id=body.ride_id or None,
        issue_type=body.issue_type,
        description=body.description,
        status="open"
    )
    db.add(ticket)
    await db.commit()
    return {"ok": True, "ticket_id": ticket.id}
