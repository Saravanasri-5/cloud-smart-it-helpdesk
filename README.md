# Cloud-Based Smart IT Helpdesk Management System

Flask + MySQL + SQLAlchemy helpdesk where **users** raise tickets, **IT support staff** resolve them and **administrators** manage users, assignments and reports.

## Folder structure

```
helpdesk/
├── app.py                 # application factory, error handlers, CLI, entry point
├── config.py              # development / production configuration
├── extensions.py          # db, login manager, CSRF
├── models.py              # users, tickets, ticket_comments, ticket_attachments, ticket_history
├── forms.py               # Flask-WTF forms + validation
├── utils.py               # RBAC decorator, secure uploads, ticket filters
├── services.py            # shared business logic (comment / status / assignment)
├── reports.py             # dashboard report queries
├── seed.py                # sample data loader
├── schema.sql             # MySQL schema
├── sample_data.sql        # optional SQL sample data
├── requirements.txt  .env.example  Procfile  .gitignore
├── routes/                # main, auth, tickets, admin, api blueprints
├── templates/             # Jinja2 templates (base, auth, dashboard, tickets/, admin/, errors/)
└── static/                # css/style.css, js/app.js, uploads/
```

## 1. Local installation

Requirements: Python 3.10+, MySQL 8+.

```bash
cd helpdesk
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Windows: copy .env.example .env
```

## 2. MySQL setup

```bash
mysql -u root -p < schema.sql
```

This creates the `helpdesk_db` database, the `helpdesk_user` account (password `HelpdeskPass@123`) and all tables.
Change the password in `schema.sql` **and** `.env` for anything other than local testing.
The tables are also created automatically on first start (`db.create_all()`).

Optional sample data:

```bash
python seed.py                    # generates users + 36 tickets with comments/history
# or: mysql -u root -p < sample_data.sql   (small fixed data set, empty database only)
```

## 3. Run

```bash
python app.py
# or
flask --app app run
```

Open http://127.0.0.1:5000

Default administrator (created automatically when the users table is empty):

| Role  | Email                    | Password     |
|-------|--------------------------|--------------|
| Admin | admin@helpdesk.local     | Admin@12345  |

After `python seed.py`, these accounts use `Password@123`: `arun.staff@helpdesk.local`, `priya.staff@helpdesk.local`, `karthik.staff@helpdesk.local` (staff) and `meena@`, `rahul@`, `sneha@`, `david@helpdesk.local` (users).

Quick test without MySQL: set `DATABASE_URL=sqlite:///helpdesk.db` in `.env`.

## 4. Environment variables

| Variable | Purpose |
|----------|---------|
| `APP_ENV` | `development` or `production` |
| `SECRET_KEY` | Session/CSRF signing key (**required** in production) |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | MySQL connection |
| `DATABASE_URL` | Optional full SQLAlchemy URL (overrides `DB_*`) |
| `UPLOAD_FOLDER` | Where attachments are stored (default `static/uploads`) |
| `HOST`, `PORT` | Dev server bind address |
| `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | First administrator |
| `COOKIE_SECURE` | `1` (default in production) sends cookies over HTTPS only; set `0` if testing production mode over HTTP |

## 5. Production configuration

```bash
export APP_ENV=production
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
gunicorn app:app --workers 3 --bind 0.0.0.0:8000
```

- Put Nginx/Apache (or a cloud load balancer) in front with HTTPS, and set `client_max_body_size 10m;`.
- Use a dedicated MySQL user and a strong password; keep `.env` out of version control.
- Store `UPLOAD_FOLDER` on persistent storage (volume / network disk).
- Files in `static/uploads` are served only through the authenticated `/attachments/<id>` route; block direct access to that directory in your web server (`location /static/uploads/ { deny all; }`).
- Change the default admin password immediately after first login.

## 6. Roles and features

| Role | Capabilities |
|------|--------------|
| User | Register, login, edit profile, create tickets (category, priority, screenshot), view status/history, comment |
| IT Support Staff | View assigned tickets, update status (Open / In Progress / Resolved / Closed), add resolution details, comment |
| Administrator | Dashboard statistics, manage users and staff, assign tickets, view/search/filter all tickets, reports (category, priority, status, monthly, technician performance), CSV export |

## 7. JSON API (session authenticated, CSRF header `X-CSRFToken` required on POST)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/me`, `/api/stats` | Current user, dashboard counts |
| GET/POST | `/api/tickets` | List (filters `q,status,priority,category,assignee,page`) / create |
| GET | `/api/tickets/<id>` | Ticket detail with comments, attachments, history |
| GET/POST | `/api/tickets/<id>/comments` | List / add comments |
| POST | `/api/tickets/<id>/status` | Staff/admin: `{status, resolution}` |
| POST | `/api/tickets/<id>/assign` | Admin: `{assignee_id}` |
| GET | `/api/users`, `/api/staff` | Admin only |
| GET | `/api/reports` | Admin only |

## 8. Security summary

Werkzeug password hashing, Flask-Login sessions, role-based route protection, CSRF tokens on every form and API call, SQLAlchemy parameterised queries, Jinja2 auto-escaping plus a strict Content-Security-Policy, secure upload handling (extension whitelist, magic-byte check, random stored names, 10 MB limit), login throttling, open-redirect protection and CSV formula-injection protection.
