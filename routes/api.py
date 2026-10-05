from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

import reports
import services
from extensions import db
from models import CATEGORIES, PRIORITIES, Ticket, User
from routes.main import dashboard_stats
from utils import apply_ticket_filters, can_update, can_view, roles_required, visible_tickets_query

bp = Blueprint("api", __name__)


def error(message, code=400):
    return jsonify(error=message), code


def ticket_json(t, detail=False):
    data = {
        "id": t.id, "ticket_no": t.ticket_no, "title": t.title, "category": t.category,
        "priority": t.priority, "status": t.status,
        "creator": {"id": t.creator.id, "name": t.creator.name},
        "assignee": {"id": t.assignee.id, "name": t.assignee.name} if t.assignee else None,
        "created_at": t.created_at.isoformat(), "updated_at": t.updated_at.isoformat(),
        "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
    }
    if detail:
        data.update({
            "description": t.description, "resolution": t.resolution,
            "comments": [comment_json(c) for c in t.comments],
            "attachments": [{"id": a.id, "name": a.original_name, "size": a.size} for a in t.attachments],
            "history": [{"action": h.action, "old": h.old_value, "new": h.new_value,
                         "by": h.actor.name, "at": h.created_at.isoformat()} for h in t.history],
        })
    return data


def comment_json(c):
    return {"id": c.id, "body": c.body, "author": c.author.name, "author_role": c.author.role,
            "created_at": c.created_at.isoformat()}


def user_json(u):
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "department": u.department,
            "phone": u.phone, "active": u.active, "created_at": u.created_at.isoformat()}


def load_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        return None, error("Ticket not found.", 404)
    if not can_view(ticket):
        return None, error("Access denied.", 403)
    return ticket, None


# ---- Authentication / profile -------------------------------------------------
@bp.route("/me")
@login_required
def me():
    return jsonify(user_json(current_user))


@bp.route("/stats")
@login_required
def stats():
    return jsonify(dashboard_stats())


# ---- Tickets ---------------------------------------------------------------------
@bp.route("/tickets", methods=["GET"])
@login_required
def list_tickets():
    query, _ = apply_ticket_filters(visible_tickets_query(), request.args, allow_assignee=current_user.role == "admin")
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", current_app.config["PER_PAGE"], type=int), 100)
    pagination = query.order_by(Ticket.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify(items=[ticket_json(t) for t in pagination.items], page=pagination.page,
                   pages=pagination.pages, total=pagination.total)


@bp.route("/tickets", methods=["POST"])
@roles_required("user")
def create_ticket():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    category, priority = data.get("category"), data.get("priority", "Medium")
    if not 5 <= len(title) <= 200:
        return error("Title must be 5-200 characters.")
    if not 10 <= len(description) <= 5000:
        return error("Description must be 10-5000 characters.")
    if category not in CATEGORIES or priority not in PRIORITIES:
        return error("Invalid category or priority.")
    ticket = services.create_ticket(current_user, title, description, category, priority)
    db.session.commit()
    return jsonify(ticket_json(ticket, detail=True)), 201


@bp.route("/tickets/<int:ticket_id>", methods=["GET"])
@login_required
def get_ticket(ticket_id):
    ticket, err = load_ticket(ticket_id)
    return err if err else jsonify(ticket_json(ticket, detail=True))


# ---- Comments --------------------------------------------------------------------
@bp.route("/tickets/<int:ticket_id>/comments", methods=["GET"])
@login_required
def list_comments(ticket_id):
    ticket, err = load_ticket(ticket_id)
    return err if err else jsonify(items=[comment_json(c) for c in ticket.comments])


@bp.route("/tickets/<int:ticket_id>/comments", methods=["POST"])
@login_required
def add_comment(ticket_id):
    ticket, err = load_ticket(ticket_id)
    if err:
        return err
    try:
        comment = services.add_comment(ticket, current_user, (request.get_json(silent=True) or {}).get("body"))
    except ValueError as exc:
        return error(str(exc))
    return jsonify(comment_json(comment)), 201


# ---- Status & assignment ------------------------------------------------------
@bp.route("/tickets/<int:ticket_id>/status", methods=["POST"])
@roles_required("staff", "admin")
def update_status(ticket_id):
    ticket, err = load_ticket(ticket_id)
    if err:
        return err
    if not can_update(ticket):
        return error("Access denied.", 403)
    data = request.get_json(silent=True) or {}
    try:
        services.change_status(ticket, current_user, data.get("status"), data.get("resolution"))
    except ValueError as exc:
        return error(str(exc))
    return jsonify(ticket_json(ticket, detail=True))


@bp.route("/tickets/<int:ticket_id>/assign", methods=["POST"])
@roles_required("admin")
def assign_ticket(ticket_id):
    ticket, err = load_ticket(ticket_id)
    if err:
        return err
    staff_id = (request.get_json(silent=True) or {}).get("assignee_id")
    try:
        services.assign_ticket(ticket, current_user, int(staff_id) if staff_id else 0)
    except (ValueError, TypeError) as exc:
        return error(str(exc))
    return jsonify(ticket_json(ticket))


# ---- Users (admin) -------------------------------------------------------------------
@bp.route("/users")
@roles_required("admin")
def list_users():
    query = User.query
    role = request.args.get("role")
    if role in ("user", "staff", "admin"):
        query = query.filter_by(role=role)
    return jsonify(items=[user_json(u) for u in query.order_by(User.name).all()])


@bp.route("/staff")
@roles_required("admin")
def list_staff():
    staff = User.query.filter_by(role="staff", active=True).order_by(User.name).all()
    return jsonify(items=[user_json(u) for u in staff])


# ---- Reports (admin) ----------------------------------------------------------------
@bp.route("/reports")
@roles_required("admin")
def all_reports():
    data = reports.all_reports()
    return jsonify({k: ([{"label": a, "count": b} for a, b in v] if k != "technicians" else v)
                    for k, v in data.items()})
