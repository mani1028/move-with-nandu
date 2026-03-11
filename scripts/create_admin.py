from dotenv import load_dotenv
load_dotenv()
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import uuid, sqlite3, datetime
from backend.database import generate_custom_id
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
def hash_password(p):
    return pwd_context.hash(p)

"""
This script will create an admin user if none exists, or update the
existing admin's name, email and password if an admin row is present.

Edit the `email`, `pwd` and `name` variables below before running.
"""

email = os.getenv("ADMIN_EMAIL", "admin@nandutravels.local")
pwd = os.getenv("ADMIN_PASSWORD", "Adm!nNandu2026$")
name = os.getenv("ADMIN_NAME", "Nandu Admin")
phone = os.getenv("ADMIN_PHONE", "9999999999")

pw_hash = hash_password(pwd)

conn = sqlite3.connect('nandu.db')
cur = conn.cursor()

# Find existing admin (by role). If present, update fields; otherwise insert.
cur.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
row = cur.fetchone()
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
if row is None:
    # Ensure admins table exists
    cur.execute('''CREATE TABLE IF NOT EXISTS admins (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        password_hash TEXT,
        provider TEXT DEFAULT 'local',
        provider_id TEXT,
        email_verified INTEGER DEFAULT 0,
        created_at TEXT
    )''')

    # Generate compact ADMIN### id
    def next_admin_id(cur):
        cur.execute("SELECT id FROM admins WHERE id LIKE 'ADMIN%'")
        rows = cur.fetchall()
        maxn = 0
        for r in rows:
            try:
                n = int(r[0].replace('ADMIN', ''))
                if n > maxn:
                    maxn = n
            except Exception:
                continue
        return f"ADMIN{(maxn+1):03d}"

    new_id = next_admin_id(cur)

    # Insert into users and admins using the compact admin id
    cur.execute('''INSERT INTO users (id, name, email, phone, password_hash, role, provider, provider_id, email_verified, picture, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)''', (
        new_id, name, email, phone, pw_hash, 'admin', 'local', None, 1, '', now
    ))
    cur.execute('''INSERT INTO admins (id, name, email, phone, password_hash, provider, provider_id, email_verified, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)''', (
        new_id, name, email, phone, pw_hash, 'local', None, 1, now
    ))
    conn.commit()
    print('Admin created with id', new_id)
else:
    admin_id = row[0]
    cur.execute('''UPDATE users SET name = ?, email = ?, phone = ?, password_hash = ?, provider = 'local', provider_id = NULL, email_verified = 1 WHERE id = ?''', (
        name, email, phone, pw_hash, admin_id
    ))
    conn.commit()
    # Ensure admins table exists and has a corresponding row for this admin user
    cur.execute('''CREATE TABLE IF NOT EXISTS admins (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        password_hash TEXT,
        provider TEXT DEFAULT 'local',
        provider_id TEXT,
        email_verified INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    # If an admin record for this email doesn't exist, insert one
    cur.execute('SELECT id FROM admins WHERE email = ? LIMIT 1', (email,))
    arow = cur.fetchone()
    if arow is None:
        # create admin id based on existing user id if it is compact, else generate next ADMIN###
        def next_admin_id(cur):
            cur.execute("SELECT id FROM admins WHERE id LIKE 'ADMIN%'")
            rows = cur.fetchall()
            maxn = 0
            for r in rows:
                try:
                    n = int(r[0].replace('ADMIN', ''))
                    if n > maxn:
                        maxn = n
                except Exception:
                    continue
            return f"ADMIN{(maxn+1):03d}"

        # Prefer using existing user id if it already matches ADMIN### pattern
        if admin_id.startswith('ADMIN'):
            adm_id = admin_id
        else:
            adm_id = next_admin_id(cur)
        cur.execute('''INSERT INTO admins (id, name, email, phone, password_hash, provider, provider_id, email_verified, created_at)
                       VALUES (?,?,?,?,?,?,?,?,?)''', (
            adm_id, name, email, phone, pw_hash, 'local', None, 1, now
        ))
        conn.commit()
        print('Admin updated; admin record created with id', adm_id)
    else:
        print('Admin updated')

conn.close()
