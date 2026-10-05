-- Sample data (passwords: admin = Admin@12345, everyone else = Password@123)
-- Run AFTER schema.sql. The app also creates the admin automatically, so use this file
-- only on an empty database, or use `python seed.py` for larger generated sample data.
USE helpdesk_db;

INSERT INTO users (id, name, email, password_hash, role, phone, department, active) VALUES
(1, 'System Administrator', 'admin@helpdesk.local', 'scrypt:32768:8:1$aZvTYSOcOini4gKF$bcc02c3a2d2c00f83f8e6e1843d86a3c86c793dce470fc28e125ff099c09b2149ced9273e7ac085db63b4c7dd87c677ed642149aa62dd5fe86922aae1aac947b', 'admin', NULL, 'IT', 1),
(2, 'Arun Kumar', 'arun.staff@helpdesk.local', 'scrypt:32768:8:1$4059HhJTyC1B8RKx$4b844995b5cb9ec9a4c7bec7250f6fc13cb6c20b32dd7450f6dc8b724d4b8e677c7d38110c3d29bff0b37989c7d3d2a7bc74a3c87356dbb657cc61428754869c', 'staff', '9000000001', 'Network Operations', 1),
(3, 'Priya Nair', 'priya.staff@helpdesk.local', 'scrypt:32768:8:1$4059HhJTyC1B8RKx$4b844995b5cb9ec9a4c7bec7250f6fc13cb6c20b32dd7450f6dc8b724d4b8e677c7d38110c3d29bff0b37989c7d3d2a7bc74a3c87356dbb657cc61428754869c', 'staff', '9000000002', 'Desktop Support', 1),
(4, 'Meena Sundaram', 'meena@helpdesk.local', 'scrypt:32768:8:1$4059HhJTyC1B8RKx$4b844995b5cb9ec9a4c7bec7250f6fc13cb6c20b32dd7450f6dc8b724d4b8e677c7d38110c3d29bff0b37989c7d3d2a7bc74a3c87356dbb657cc61428754869c', 'user', '9000000003', 'Finance', 1),
(5, 'Rahul Verma', 'rahul@helpdesk.local', 'scrypt:32768:8:1$4059HhJTyC1B8RKx$4b844995b5cb9ec9a4c7bec7250f6fc13cb6c20b32dd7450f6dc8b724d4b8e677c7d38110c3d29bff0b37989c7d3d2a7bc74a3c87356dbb657cc61428754869c', 'user', '9000000004', 'Human Resources', 1);

INSERT INTO tickets (id, title, description, category, priority, status, resolution, creator_id, assignee_id, created_at, updated_at, resolved_at) VALUES
(1, 'VPN connection fails with error 809', 'Unable to connect to the company VPN from home. Error 809 is displayed.', 'Network', 'Critical', 'In Progress', NULL, 4, 2, NOW() - INTERVAL 3 DAY, NOW() - INTERVAL 2 DAY, NULL),
(2, 'Printer not responding on Finance floor', 'The shared printer shows offline for everyone in the Finance department.', 'Hardware', 'Low', 'Resolved', 'Print spooler restarted and printer IP reservation corrected.', 4, 3, NOW() - INTERVAL 10 DAY, NOW() - INTERVAL 9 DAY, NOW() - INTERVAL 9 DAY),
(3, 'Install Adobe Acrobat Pro', 'Please install Adobe Acrobat Pro on my workstation for editing contracts.', 'Software', 'Medium', 'Open', NULL, 5, NULL, NOW() - INTERVAL 1 DAY, NOW() - INTERVAL 1 DAY, NULL),
(4, 'Suspicious phishing email received', 'I received an email asking me to confirm my credentials through an unknown link.', 'Security', 'Critical', 'Closed', 'Sender blocked, mailbox scanned and user informed. Awareness reminder sent.', 5, 2, NOW() - INTERVAL 20 DAY, NOW() - INTERVAL 19 DAY, NOW() - INTERVAL 19 DAY);

INSERT INTO ticket_comments (ticket_id, user_id, body) VALUES
(1, 2, 'Hello, I have picked up this ticket. Please confirm which VPN client version you are using.'),
(1, 4, 'I am using the latest client from the company portal.'),
(2, 3, 'The printer is back online. Please confirm.');

INSERT INTO ticket_history (ticket_id, user_id, action, old_value, new_value) VALUES
(1, 4, 'Ticket created', NULL, 'Open'),
(1, 1, 'Assignment changed', 'Unassigned', 'Arun Kumar'),
(1, 2, 'Status changed', 'Open', 'In Progress'),
(2, 4, 'Ticket created', NULL, 'Open'),
(2, 3, 'Status changed', 'In Progress', 'Resolved'),
(3, 5, 'Ticket created', NULL, 'Open'),
(4, 5, 'Ticket created', NULL, 'Open'),
(4, 2, 'Status changed', 'Resolved', 'Closed');
