from collections import Counter
from datetime import datetime

from sqlalchemy import func

from extensions import db
from models import CATEGORIES, PRIORITIES, STATUSES, Ticket, User, utcnow


def _grouped(column, order):
    counts = dict(db.session.query(column, func.count(Ticket.id)).group_by(column).all())
    return [(label, counts.get(label, 0)) for label in order]


def by_category():
    return _grouped(Ticket.category, CATEGORIES)


def by_priority():
    return _grouped(Ticket.priority, PRIORITIES)


def by_status():
    return _grouped(Ticket.status, STATUSES)


def monthly(months=12):
    now = utcnow()
    keys = []
    year, month = now.year, now.month
    for _ in range(months):
        keys.append((year, month))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    keys.reverse()
    start = datetime(keys[0][0], keys[0][1], 1)
    counter = Counter((t.created_at.year, t.created_at.month)
                      for t in Ticket.query.filter(Ticket.created_at >= start).with_entities(Ticket.created_at).all())
    return [(datetime(y, m, 1).strftime("%b %Y"), counter.get((y, m), 0)) for y, m in keys]


def technician_performance():
    staff = User.query.filter_by(role="staff").order_by(User.name).all()
    rows = []
    for member in staff:
        tickets = Ticket.query.filter_by(assignee_id=member.id).all()
        resolved = [t for t in tickets if t.status in ("Resolved", "Closed")]
        durations = [(t.resolved_at - t.created_at).total_seconds() / 3600 for t in resolved if t.resolved_at]
        rows.append({
            "id": member.id,
            "name": member.name,
            "assigned": len(tickets),
            "open": sum(1 for t in tickets if t.status == "Open"),
            "in_progress": sum(1 for t in tickets if t.status == "In Progress"),
            "resolved": len(resolved),
            "rate": round(100 * len(resolved) / len(tickets)) if tickets else 0,
            "avg_hours": round(sum(durations) / len(durations), 1) if durations else None,
        })
    return rows


def all_reports():
    return {
        "category": by_category(),
        "priority": by_priority(),
        "status": by_status(),
        "monthly": monthly(),
        "technicians": technician_performance(),
    }
