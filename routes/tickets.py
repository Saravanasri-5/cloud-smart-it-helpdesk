import os

from flask import (Blueprint, abort, current_app, flash, redirect, render_template, request,
                   send_from_directory, url_for)
from flask_login import current_user, login_required

from extensions import db
from forms import (AssignForm, AttachmentForm, CommentForm, EmptyForm, StatusForm, TicketForm)
from models import Ticket, TicketAttachment, User
import services
from utils import (apply_ticket_filters, can_update, can_view, delete_attachment_files,
                   roles_required, save_attachment, visible_tickets_query)

bp = Blueprint("tickets", __name__)


def get_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if ticket is None:
        abort(404)
    if not can_view(ticket):
        abort(403)
    return ticket


def staff_choices():
    staff = User.query.filter_by(role="staff", active=True).order_by(User.name).all()
    return staff, [(0, "— Unassigned —")] + [(s.id, s.name) for s in staff]


@bp.route("/tickets")
@login_required
def list_tickets():
    query, cleaned = apply_ticket_filters(visible_tickets_query(), request.args,
                                          allow_assignee=current_user.role == "admin")
    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Ticket.created_at.desc()).paginate(
        page=page, per_page=current_app.config["PER_PAGE"], error_out=False)
    staff, choices = (staff_choices() if current_user.role == "admin" else ([], []))
    assign_form = AssignForm()
    assign_form.assignee.choices = choices
    return render_template("tickets/list.html", pagination=pagination, tickets=pagination.items,
                           filters=cleaned, staff=staff, assign_form=assign_form)


@bp.route("/tickets/new", methods=["GET", "POST"])
@roles_required("user")
def new_ticket():
    form = TicketForm()
    if form.validate_on_submit():
        ticket = services.create_ticket(current_user, form.title.data.strip(), form.description.data.strip(),
                                        form.category.data, form.priority.data)
        try:
            save_attachment(form.attachment.data, ticket, current_user)
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
            return render_template("tickets/new.html", form=form)
        db.session.commit()
        flash(f"Ticket {ticket.ticket_no} created successfully.", "success")
        return redirect(url_for("tickets.detail", ticket_id=ticket.id))
    return render_template("tickets/new.html", form=form)


@bp.route("/tickets/<int:ticket_id>")
@login_required
def detail(ticket_id):
    ticket = get_ticket(ticket_id)
    status_form = StatusForm(status=ticket.status, resolution=ticket.resolution)
    assign_form = AssignForm()
    staff, choices = (staff_choices() if current_user.role == "admin" else ([], []))
    assign_form.assignee.choices = choices
    assign_form.assignee.data = ticket.assignee_id or 0
    return render_template("tickets/detail.html", ticket=ticket, comment_form=CommentForm(),
                           attachment_form=AttachmentForm(), status_form=status_form,
                           assign_form=assign_form, delete_form=EmptyForm(),
                           can_update=can_update(ticket))


@bp.route("/tickets/<int:ticket_id>/comment", methods=["POST"])
@login_required
def add_comment(ticket_id):
    ticket = get_ticket(ticket_id)
    form = CommentForm()
    if form.validate_on_submit():
        try:
            services.add_comment(ticket, current_user, form.body.data)
            flash("Comment added.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    else:
        flash("Please enter a comment (max 2000 characters).", "danger")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id) + "#comments")


@bp.route("/tickets/<int:ticket_id>/status", methods=["POST"])
@roles_required("staff", "admin")
def update_status(ticket_id):
    ticket = get_ticket(ticket_id)
    if not can_update(ticket):
        abort(403)
    form = StatusForm()
    if form.validate_on_submit():
        try:
            services.change_status(ticket, current_user, form.status.data, form.resolution.data)
            flash("Ticket updated.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    else:
        flash("Invalid form submission.", "danger")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))


@bp.route("/tickets/<int:ticket_id>/assign", methods=["POST"])
@roles_required("admin")
def assign(ticket_id):
    ticket = get_ticket(ticket_id)
    form = AssignForm()
    form.assignee.choices = staff_choices()[1]
    if form.validate_on_submit():
        try:
            services.assign_ticket(ticket, current_user, form.assignee.data)
            flash("Assignment updated.", "success")
        except ValueError as exc:
            flash(str(exc), "danger")
    else:
        flash("Invalid form submission.", "danger")
    return redirect(request.referrer if request.referrer and request.host in request.referrer
                    else url_for("tickets.detail", ticket_id=ticket.id))


@bp.route("/tickets/<int:ticket_id>/attachments", methods=["POST"])
@login_required
def upload_attachment(ticket_id):
    ticket = get_ticket(ticket_id)
    form = AttachmentForm()
    if form.validate_on_submit():
        try:
            save_attachment(form.attachment.data, ticket, current_user)
            db.session.commit()
            flash("Attachment uploaded.", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
    else:
        for errors in form.errors.values():
            for error in errors:
                flash(error, "danger")
    return redirect(url_for("tickets.detail", ticket_id=ticket.id))


@bp.route("/tickets/<int:ticket_id>/delete", methods=["POST"])
@roles_required("admin")
def delete(ticket_id):
    ticket = get_ticket(ticket_id)
    if EmptyForm().validate_on_submit():
        delete_attachment_files(ticket)
        db.session.delete(ticket)
        db.session.commit()
        flash("Ticket deleted.", "success")
    return redirect(url_for("tickets.list_tickets"))


@bp.route("/attachments/<int:attachment_id>")
@login_required
def download(attachment_id):
    attachment = db.session.get(TicketAttachment, attachment_id)
    if attachment is None:
        abort(404)
    if not can_view(attachment.ticket):
        abort(403)
    as_download = request.args.get("download") == "1" or not attachment.is_image
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], attachment.stored_name,
                               mimetype=attachment.content_type, as_attachment=as_download,
                               download_name=attachment.original_name)
