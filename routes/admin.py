import csv
import io

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_

import reports
from extensions import db
from forms import EmptyForm, UserAdminForm
from models import ROLES, Ticket, User
from utils import roles_required

bp = Blueprint("admin", __name__)


@bp.route("/users")
@roles_required("admin")
def users():
    query = User.query
    role = request.args.get("role", "").strip()
    text = request.args.get("q", "").strip()[:100]
    if role in ROLES:
        query = query.filter(User.role == role)
    else:
        role = ""
    if text:
        query = query.filter(or_(User.name.ilike(f"%{text}%"), User.email.ilike(f"%{text}%"),
                                 User.department.ilike(f"%{text}%")))
    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=current_app.config["PER_PAGE"], error_out=False)
    filters = {k: v for k, v in (("q", text), ("role", role)) if v}
    return render_template("admin/users.html", pagination=pagination, users=pagination.items,
                           filters=filters, role=role, action_form=EmptyForm())


@bp.route("/users/new", methods=["GET", "POST"])
@roles_required("admin")
def create_user():
    form = UserAdminForm(role=request.args.get("role", "user") if request.args.get("role") in ROLES else "user")
    if form.validate_on_submit():
        if not form.password.data:
            form.password.errors.append("Password is required for new users.")
        else:
            user = User(name=form.name.data.strip(), email=form.email.data.strip().lower(),
                        role=form.role.data, phone=(form.phone.data or "").strip() or None,
                        department=(form.department.data or "").strip() or None, active=form.active.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash(f"User {user.name} created.", "success")
            return redirect(url_for("admin.users", role=user.role if user.role == "staff" else None))
    return render_template("admin/user_form.html", form=form, editing=False, target=None)


@bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@roles_required("admin")
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if user is None:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))
    form = UserAdminForm(obj=user, user_id=user.id)
    if form.validate_on_submit():
        user.name = form.name.data.strip()
        user.email = form.email.data.strip().lower()
        user.phone = (form.phone.data or "").strip() or None
        user.department = (form.department.data or "").strip() or None
        if user.id != current_user.id:  # prevent admins from locking themselves out
            user.role = form.role.data
            user.active = form.active.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash("User updated.", "success")
        return redirect(url_for("admin.users"))
    return render_template("admin/user_form.html", form=form, editing=True, target=user)


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@roles_required("admin")
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if user is None or not EmptyForm().validate_on_submit():
        flash("Action could not be completed.", "danger")
    elif user.id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
    else:
        user.active = not user.active
        db.session.commit()
        flash(f"{user.name} is now {'active' if user.active else 'deactivated'}.", "success")
    return redirect(request.referrer if request.referrer and request.host in request.referrer else url_for("admin.users"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@roles_required("admin")
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if user is None or not EmptyForm().validate_on_submit():
        flash("Action could not be completed.", "danger")
    elif user.id == current_user.id:
        flash("You cannot delete your own account.", "danger")
    elif user.has_activity():
        flash("This user has tickets, comments or history. Deactivate the account instead of deleting it.", "warning")
    else:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted.", "success")
    return redirect(url_for("admin.users"))


@bp.route("/reports")
@roles_required("admin")
def report_page():
    data = reports.all_reports()
    return render_template("admin/reports.html", **data)


def _safe_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@") else text


@bp.route("/reports/export")
@roles_required("admin")
def export_tickets():
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Ticket", "Title", "Category", "Priority", "Status", "Created by", "Assigned to",
                     "Created at", "Resolved at"])
    for t in Ticket.query.order_by(Ticket.id).all():
        writer.writerow([_safe_cell(v) for v in (
            t.ticket_no, t.title, t.category, t.priority, t.status, t.creator.name,
            t.assignee.name if t.assignee else "", t.created_at, t.resolved_at or "")])
    return Response(buffer.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=tickets_report.csv"})
