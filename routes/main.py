from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

import reports
from extensions import db
from models import Ticket, User
from utils import visible_tickets_query

bp = Blueprint("main", __name__)


def dashboard_stats():
    """Counts used by the dashboard and the JSON stats endpoint."""
    if current_user.role == "admin":
        return {
            "total_users": User.query.count(),
            "total_tickets": Ticket.query.count(),
            "open_tickets": Ticket.query.filter_by(status="Open").count(),
            "resolved_tickets": Ticket.query.filter_by(status="Resolved").count(),
            "critical_tickets": Ticket.query.filter_by(priority="Critical").count(),
            "unassigned_tickets": Ticket.query.filter(Ticket.assignee_id.is_(None),
                                                      Ticket.status.in_(["Open", "In Progress"])).count(),
        }
    counts = dict(visible_tickets_query().with_entities(Ticket.status, func.count(Ticket.id))
                  .group_by(Ticket.status).all())
    return {
        "total_tickets": sum(counts.values()),
        "open_tickets": counts.get("Open", 0),
        "in_progress_tickets": counts.get("In Progress", 0),
        "resolved_tickets": counts.get("Resolved", 0) + counts.get("Closed", 0),
    }


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@bp.route("/dashboard")
@login_required
def dashboard():
    recent = visible_tickets_query().order_by(Ticket.created_at.desc()).limit(8).all()
    context = {"stats": dashboard_stats(), "recent": recent}
    if current_user.role == "admin":
        context["by_status"] = reports.by_status()
        context["by_priority"] = reports.by_priority()
    return render_template("dashboard.html", **context)
