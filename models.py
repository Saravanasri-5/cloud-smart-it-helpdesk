from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db

CATEGORIES = ["Network", "Hardware", "Software", "Account", "Security", "Other"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
STATUSES = ["Open", "In Progress", "Resolved", "Closed"]
ROLES = ["user", "staff", "admin"]
ROLE_LABELS = {"user": "User", "staff": "IT Support Staff", "admin": "Administrator"}


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="user", index=True)
    phone = db.Column(db.String(30))
    department = db.Column(db.String(100))
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    created_tickets = db.relationship("Ticket", foreign_keys="Ticket.creator_id", back_populates="creator")
    assigned_tickets = db.relationship("Ticket", foreign_keys="Ticket.assignee_id", back_populates="assignee")
    comments = db.relationship("TicketComment", back_populates="author")
    history = db.relationship("TicketHistory", back_populates="actor")

    @property
    def is_active(self):
        return bool(self.active)

    @property
    def role_label(self):
        return ROLE_LABELS.get(self.role, self.role)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_activity(self):
        return bool(self.created_tickets or self.assigned_tickets or self.comments or self.history)

    def __repr__(self):
        return f"<User {self.email}>"


class Ticket(db.Model):
    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, index=True)
    priority = db.Column(db.String(20), nullable=False, default="Medium", index=True)
    status = db.Column(db.String(20), nullable=False, default="Open", index=True)
    resolution = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    resolved_at = db.Column(db.DateTime)

    creator = db.relationship("User", foreign_keys=[creator_id], back_populates="created_tickets")
    assignee = db.relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tickets")
    comments = db.relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan",
                               order_by="TicketComment.created_at")
    attachments = db.relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan",
                                  order_by="TicketAttachment.created_at")
    history = db.relationship("TicketHistory", back_populates="ticket", cascade="all, delete-orphan",
                              order_by="TicketHistory.created_at.desc(), TicketHistory.id.desc()")

    @property
    def ticket_no(self):
        return f"HD-{self.id:05d}"

    def __repr__(self):
        return f"<Ticket {self.ticket_no}>"


class TicketComment(db.Model):
    __tablename__ = "ticket_comments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    ticket = db.relationship("Ticket", back_populates="comments")
    author = db.relationship("User", back_populates="comments")


class TicketAttachment(db.Model):
    __tablename__ = "ticket_attachments"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    stored_name = db.Column(db.String(100), nullable=False, unique=True)
    original_name = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100), nullable=False)
    size = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    ticket = db.relationship("Ticket", back_populates="attachments")
    uploader = db.relationship("User")

    @property
    def is_image(self):
        return self.content_type.startswith("image/")


class TicketHistory(db.Model):
    __tablename__ = "ticket_history"

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)
    old_value = db.Column(db.String(255))
    new_value = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    ticket = db.relationship("Ticket", back_populates="history")
    actor = db.relationship("User", back_populates="history")
