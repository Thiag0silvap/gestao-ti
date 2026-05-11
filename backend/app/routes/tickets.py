from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.computer import Computer
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate

router = APIRouter()


async def serialize_ticket(db: AsyncSession, ticket: Ticket):
    result_req = await db.execute(select(User).filter(User.id == ticket.requester_id))
    requester = result_req.scalars().first()
    
    assigned_to = None
    computer = None

    if ticket.assigned_to_id:
        result_ass = await db.execute(select(User).filter(User.id == ticket.assigned_to_id))
        assigned_to = result_ass.scalars().first()

    if ticket.computer_id:
        result_comp = await db.execute(select(Computer).filter(Computer.id == ticket.computer_id))
        computer = result_comp.scalars().first()

    return {
        "id": ticket.id,
        "title": ticket.title,
        "description": ticket.description,
        "status": ticket.status,
        "priority": ticket.priority,
        "requester_id": ticket.requester_id,
        "requester_name": requester.name if requester else None,
        "assigned_to_id": ticket.assigned_to_id,
        "assigned_to_name": assigned_to.name if assigned_to else None,
        "computer_id": ticket.computer_id,
        "computer_hostname": computer.hostname if computer else None,
        "sector": ticket.sector,
        "created_at": ticket.created_at,
        "closed_at": ticket.closed_at,
    }


@router.post("/tickets")
async def create_ticket(
    data: TicketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    selected_computer_id = data.computer_id

    if selected_computer_id:
        result_comp = await db.execute(select(Computer).filter(Computer.id == selected_computer_id))
        computer = result_comp.scalars().first()
        if not computer:
            raise HTTPException(status_code=404, detail="Computador não encontrado")
    else:
        result_matches = await db.execute(
            select(Computer).filter(func.lower(Computer.user) == current_user.username.lower())
        )
        matched_computers = result_matches.scalars().all()

        if len(matched_computers) == 1:
            selected_computer_id = matched_computers[0].id
        else:
            selected_computer_id = None

    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        assigned_to_id=data.assigned_to_id,
        computer_id=selected_computer_id,
        requester_id=current_user.id,
        sector=current_user.sector,
        status="Aberto"
    )

    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)

    return await serialize_ticket(db, ticket)


@router.get("/tickets")
async def list_tickets(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "operator":
        stmt = select(Ticket).filter(Ticket.requester_id == current_user.id)
    else:
        stmt = select(Ticket)

    result = await db.execute(stmt)
    tickets = result.scalars().all()

    return [await serialize_ticket(db, ticket) for ticket in tickets]


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalars().first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if current_user.role == "operator" and ticket.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    return await serialize_ticket(db, ticket)


@router.put("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalars().first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if current_user.role == "operator" and ticket.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    if data.computer_id:
        result_comp = await db.execute(select(Computer).filter(Computer.id == data.computer_id))
        computer = result_comp.scalars().first()
        if not computer:
            raise HTTPException(status_code=404, detail="Computador não encontrado")

    ticket.title = data.title
    ticket.description = data.description
    ticket.status = data.status
    ticket.priority = data.priority
    ticket.assigned_to_id = data.assigned_to_id
    ticket.computer_id = data.computer_id
    ticket.sector = data.sector

    if data.status in ["Resolvido", "Fechado"] and not ticket.closed_at:
        ticket.closed_at = datetime.now()
    elif data.status not in ["Resolvido", "Fechado"]:
        ticket.closed_at = None

    await db.commit()
    await db.refresh(ticket)

    return await serialize_ticket(db, ticket)


@router.delete("/tickets/{ticket_id}")
async def delete_ticket(
    ticket_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Ticket).filter(Ticket.id == ticket_id))
    ticket = result.scalars().first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    await db.delete(ticket)
    await db.commit()

    return {"message": "Chamado deletado com sucesso"}