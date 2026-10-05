"""Load sample data: python seed.py   (or: flask --app app seed)"""
import random
from datetime import timedelta

from app import app
from extensions import db
from models import (CATEGORIES, Ticket, TicketComment, TicketHistory, User, utcnow)

SAMPLE_PASSWORD = "Password@123"

STAFF = [("Arun Kumar", "arun.staff@helpdesk.local", "Network Operations"),
         ("Priya Nair", "priya.staff@helpdesk.local", "Desktop Support"),
         ("Karthik Raja", "karthik.staff@helpdesk.local", "Security Operations")]
USERS = [("Meena Sundaram", "meena@helpdesk.local", "Finance"),
         ("Rahul Verma", "rahul@helpdesk.local", "Human Resources"),
         ("Sneha Iyer", "sneha@helpdesk.local", "Sales"),
         ("David Joseph", "david@helpdesk.local", "Engineering")]
SAMPLE_TICKETS = [
    ("Wi-Fi keeps disconnecting on 3rd floor", "Network", "High", "Wireless drops every 10-15 minutes near the conference rooms since Monday."),
    ("VPN connection fails with error 809", "Network", "Critical", "Unable to connect to the company VPN from home. Error 809 is displayed."),
    ("Laptop battery drains within one hour", "Hardware", "Medium", "My laptop battery drops from 100% to 0% in about an hour even when idle."),
    ("Printer not responding on Finance floor", "Hardware", "Low", "The shared printer shows offline for everyone in the Finance department."),
    ("Install Adobe Acrobat Pro", "Software", "Low", "Please install Adobe Acrobat Pro on my workstation for editing contracts."),
    ("Excel crashes when opening large files", "Software", "Medium", "Excel closes unexpectedly when opening workbooks larger than 20 MB."),
    ("Account locked after password reset", "Account", "High", "My domain account is locked after resetting the password and I cannot log in."),
    ("Need access to shared HR folder", "Account", "Medium", "Please grant me read access to the HR shared drive for onboarding documents."),
    ("Suspicious phishing email received", "Security", "Critical", "I received an email asking me to confirm my credentials through an unknown link."),
    ("Antivirus license expired", "Security", "High", "The antivirus on my desktop reports that the license has expired."),
    ("Request for second monitor", "Hardware", "Low", "I would like to request an additional monitor for my workstation."),
    ("Conference room projector issue", "Other", "Medium", "The projector in Room B flickers and shuts down during presentations."),
]


def get_or_create(name, email, role, department):
    user = User.query.filter_by(email=email).first()
    if user:
        return user
    user = User(name=name, email=email, role=role, department=department)
    user.set_password(SAMPLE_PASSWORD)
    db.session.add(user)
    db.session.flush()
    return user


def run_seed():
    random.seed(42)
    with app.app_context():
        db.create_all()
        staff = [get_or_create(n, e, "staff", d) for n, e, d in STAFF]
        users = [get_or_create(n, e, "user", d) for n, e, d in USERS]
        admin = User.query.filter_by(role="admin").first() or get_or_create(
            "System Administrator", "admin@helpdesk.local", "admin", "IT")
        if Ticket.query.count() > 0:
            db.session.commit()
            print("Tickets already exist - skipped ticket sample data.")
            return
        now = utcnow()
        statuses = ["Open", "In Progress", "Resolved", "Closed"]
        for index, (title, category, priority, description) in enumerate(SAMPLE_TICKETS * 3):
            created = now - timedelta(days=random.randint(1, 170), hours=random.randint(0, 23))
            status = random.choice(statuses)
            creator = random.choice(users)
            assignee = random.choice(staff) if status != "Open" or random.random() < 0.5 else None
            ticket = Ticket(title=title if index < len(SAMPLE_TICKETS) else f"{title} (#{index + 1})",
                            description=description, category=category, priority=priority, status=status,
                            creator_id=creator.id, assignee_id=assignee.id if assignee else None,
                            created_at=created, updated_at=created)
            if status in ("Resolved", "Closed") and assignee:
                ticket.resolved_at = created + timedelta(hours=random.randint(2, 96))
                ticket.resolution = "Issue investigated and fixed by the support team. Verified with the requester."
                ticket.updated_at = ticket.resolved_at
            elif status in ("Resolved", "Closed"):
                ticket.status = "Open"
            db.session.add(ticket)
            db.session.flush()
            db.session.add(TicketHistory(ticket_id=ticket.id, user_id=creator.id, action="Ticket created",
                                         new_value="Open", created_at=created))
            if ticket.assignee_id:
                db.session.add(TicketHistory(ticket_id=ticket.id, user_id=admin.id, action="Assignment changed",
                                             old_value="Unassigned", new_value=assignee.name,
                                             created_at=created + timedelta(minutes=30)))
                db.session.add(TicketComment(ticket_id=ticket.id, user_id=assignee.id,
                                             body="Hello, I have picked up this ticket and I am looking into it.",
                                             created_at=created + timedelta(hours=1)))
            if ticket.status != "Open":
                db.session.add(TicketHistory(ticket_id=ticket.id, user_id=assignee.id, action="Status changed",
                                             old_value="Open", new_value=ticket.status,
                                             created_at=created + timedelta(hours=2)))
        db.session.commit()
        print("Sample data loaded.")
        print(f"All sample accounts use the password: {SAMPLE_PASSWORD}")
        print("Staff : " + ", ".join(e for _, e, _ in STAFF))
        print("Users : " + ", ".join(e for _, e, _ in USERS))


if __name__ == "__main__":
    run_seed()
