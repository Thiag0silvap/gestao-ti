from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.computer import Computer
from app.models.ticket import Ticket
from app.models.user import User
from app.schemas.ticket import TicketCreate, TicketUpdate

router = APIRouter()


@router.post("/tickets")
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if data.computer_id:
        computer = db.query(Computer).filter(Computer.id == data.computer_id).first()
        if not computer:
            raise HTTPException(status_code=404, detail="Computador não encontrado")

    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        assigned_to_id=data.assigned_to_id,
        computer_id=data.computer_id,
        requester_id=current_user.id,
        status="Aberto"
    )

    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return ticket


@router.get("/tickets")
def list_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "operator":
        return db.query(Ticket).filter(Ticket.requester_id == current_user.id).all()

    return db.query(Ticket).all()


@router.get("/tickets/{ticket_id}")
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if current_user.role == "operator" and ticket.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    return ticket


@router.put("/tickets/{ticket_id}")
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if current_user.role == "operator" and ticket.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Acesso negado")

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

    db.commit()
    db.refresh(ticket)

    return ticket


@router.delete("/tickets/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Chamado não encontrado")

    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")

    db.delete(ticket)
    db.commit()

    return {"message": "Chamado deletado com sucesso"}