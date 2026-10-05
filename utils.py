import os
import uuid
from functools import wraps

from flask import abort, current_app
from flask_login import current_user, login_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from extensions import db
from models import CATEGORIES, PRIORITIES, STATUSES, Ticket, TicketAttachment, TicketHistory

SIGNATURES = {
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "pdf": [b"%PDF"],
}
MIME = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "pdf": "application/pdf"}


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def log_history(ticket, user, action, old=None, new=None):
    db.session.add(TicketHistory(ticket_id=ticket.id, user_id=user.id, action=action,
                                 old_value=(str(old)[:255] if old is not None else None),
                                 new_value=(str(new)[:255] if new is not None else None)))


def save_attachment(file_storage, ticket, user):
    """Validate and store an uploaded file. Raises ValueError on invalid files."""
    if not file_storage or not getattr(file_storage, "filename", ""):
        return None
    raw_name = file_storage.filename
    ext = os.path.splitext(raw_name)[1].lower().lstrip(".")
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        raise ValueError("Only PNG, JPG, JPEG and PDF files are allowed.")
    head = file_storage.stream.read(16)
    file_storage.stream.seek(0)
    if not any(head.startswith(sig) for sig in SIGNATURES[ext]):
        raise ValueError("The file content does not match its extension.")
    display = secure_filename(raw_name) or f"attachment.{ext}"
    stored = f"{uuid.uuid4().hex}.{ext}"
    folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, stored)
    file_storage.save(path)
    attachment = TicketAttachment(ticket_id=ticket.id, user_id=user.id, stored_name=stored,
                                  original_name=display[:255], content_type=MIME[ext],
                                  size=os.path.getsize(path))
    db.session.add(attachment)
    log_history(ticket, user, "Attachment uploaded", None, display)
    return attachment


def delete_attachment_files(ticket):
    folder = current_app.config["UPLOAD_FOLDER"]
    for att in ticket.attachments:
        try:
            os.remove(os.path.join(folder, att.stored_name))
        except OSError:
            pass


def visible_tickets_query():
    query = Ticket.query
    if current_user.role == "user":
        query = query.filter(Ticket.creator_id == current_user.id)
    elif current_user.role == "staff":
        query = query.filter(Ticket.assignee_id == current_user.id)
    return query


def can_view(ticket):
    if current_user.role == "admin":
        return True
    if current_user.role == "staff":
        return ticket.assignee_id == current_user.id
    return ticket.creator_id == current_user.id


def can_update(ticket):
    return current_user.role == "admin" or (current_user.role == "staff" and ticket.assignee_id == current_user.id)


def apply_ticket_filters(query, args, allow_assignee=False):
    """Apply search + filters from a dict-like `args` and return (query, cleaned_args)."""
    cleaned = {}
    text = (args.get("q") or "").strip()[:100]
    if text:
        cleaned["q"] = text
        conditions = [Ticket.title.ilike(f"%{text}%"), Ticket.description.ilike(f"%{text}%")]
        digits = text.upper().replace("HD-", "").lstrip("0")
        if digits.isdigit():
            conditions.append(Ticket.id == int(digits))
        query = query.filter(or_(*conditions))
    for key, column, allowed in (("status", Ticket.status, STATUSES),
                                 ("priority", Ticket.priority, PRIORITIES),
                                 ("category", Ticket.category, CATEGORIES)):
        value = (args.get(key) or "").strip()
        if value in allowed:
            cleaned[key] = value
            query = query.filter(column == value)
    if allow_assignee:
        value = (args.get("assignee") or "").strip()
        if value == "unassigned":
            cleaned["assignee"] = value
            query = query.filter(Ticket.assignee_id.is_(None))
        elif value.isdigit():
            cleaned["assignee"] = value
            query = query.filter(Ticket.assignee_id == int(value))
    return query, cleaned
