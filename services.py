"""Business operations shared by the HTML routes and the JSON API."""
from extensions import db
from models import STATUSES, Ticket, TicketComment, User, utcnow
from utils import log_history

CLOSING = ("Resolved", "Closed")


def add_comment(ticket, user, body):
    body = (body or "").strip()
    if not body:
        raise ValueError("Comment cannot be empty.")
    if len(body) > 2000:
        raise ValueError("Comment must be 2000 characters or fewer.")
    comment = TicketComment(ticket_id=ticket.id, user_id=user.id, body=body)
    db.session.add(comment)
    log_history(ticket, user, "Comment added")
    ticket.updated_at = utcnow()
    db.session.commit()
    return comment


def change_status(ticket, user, status, resolution=None):
    if status not in STATUSES:
        raise ValueError("Invalid status.")
    resolution = (resolution or "").strip() or None
    if resolution and len(resolution) > 5000:
        raise ValueError("Resolution details are too long.")
    final_resolution = resolution if resolution is not None else ticket.resolution
    if status in CLOSING and not final_resolution:
        raise ValueError("Resolution details are required when resolving or closing a ticket.")
    if status != ticket.status:
        log_history(ticket, user, "Status changed", ticket.status, status)
        ticket.status = status
        if status in CLOSING:
            ticket.resolved_at = ticket.resolved_at or utcnow()
        else:
            ticket.resolved_at = None
    if resolution is not None and resolution != ticket.resolution:
        log_history(ticket, user, "Resolution updated")
        ticket.resolution = resolution
    ticket.updated_at = utcnow()
    db.session.commit()
    return ticket


def assign_ticket(ticket, admin, staff_id):
    old = ticket.assignee.name if ticket.assignee else "Unassigned"
    if not staff_id:
        ticket.assignee_id = None
        new = "Unassigned"
    else:
        staff = db.session.get(User, staff_id)
        if staff is None or staff.role != "staff" or not staff.active:
            raise ValueError("Selected user is not an active support staff member.")
        ticket.assignee_id = staff.id
        new = staff.name
    if old != new:
        log_history(ticket, admin, "Assignment changed", old, new)
    ticket.updated_at = utcnow()
    db.session.commit()
    return ticket


def create_ticket(user, title, description, category, priority):
    ticket = Ticket(title=title, description=description, category=category,
                    priority=priority, status="Open", creator_id=user.id)
    db.session.add(ticket)
    db.session.flush()
    log_history(ticket, user, "Ticket created", None, "Open")
    return ticket
