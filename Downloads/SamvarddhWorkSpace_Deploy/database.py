"""
Database setup - SQLite with thread-safe connection handling
Fixed: SQLite threading error in async FastAPI endpoints
"""
import sqlite3, pathlib, bcrypt
from datetime import datetime

import os as _os
_DATA_DIR = pathlib.Path(_os.environ.get("DATA_DIR", "samvarddh_data"))
_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = _DATA_DIR / "samvarddh_portal.db"

def get_db():
    """
    Thread-safe SQLite connection.
    Key fix: check_same_thread=False allows SQLite to be used in async FastAPI
    endpoints where the coroutine may be resumed in a different thread.
    """
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()

def migrate_columns(c):
    """Safe column additions for existing databases — never fails on already-existing columns"""
    migrations = {
        "company_setup": [
            "authorised_signatory TEXT",
        ],
        "procurement": [
            "entry_type TEXT DEFAULT 'Material'",
            "employee_name TEXT",
            "conveyance_from TEXT",
            "conveyance_to TEXT",
            "conveyance_mode TEXT",
            "conveyance_purpose TEXT",
            "approval_status TEXT DEFAULT 'Pending'",
            "approved_by TEXT",
            "approved_date TEXT",
        ],
    }
    for table, cols in migrations.items():
        for col_def in cols:
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            except Exception:
                pass  # Column already exists — safe to ignore

def init_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    c = conn.cursor()

    # USERS
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'Viewer',
        designation TEXT,
        status TEXT DEFAULT 'Active',
        force_password_change INTEGER DEFAULT 1,
        created_date TEXT,
        last_login TEXT
    )""")

    # AUDIT LOG
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        module TEXT,
        details TEXT,
        created_at TEXT
    )""")

    # SETUP / COMPANY — complete schema
    c.execute("""CREATE TABLE IF NOT EXISTS company_setup (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        brand_name TEXT,
        legal_name TEXT,
        gstin TEXT,
        pan TEXT,
        phone TEXT,
        email TEXT,
        website TEXT,
        city TEXT,
        state TEXT,
        address TEXT,
        bank_name TEXT,
        bank_account TEXT,
        bank_ifsc TEXT,
        bank_branch TEXT,
        default_terms TEXT,
        default_footer TEXT,
        logo_path TEXT,
        signature_path TEXT,
        authorised_signatory TEXT
    )""")

    # EMPLOYEES
    c.execute("""CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT,
        phone TEXT,
        email TEXT,
        designation TEXT,
        status TEXT DEFAULT 'Active',
        created_date TEXT
    )""")

    # CLIENTS
    c.execute("""CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        gstin TEXT,
        billing_address TEXT,
        site_address TEXT,
        project_type TEXT,
        referred_by TEXT,
        lead_designer TEXT,
        project_manager TEXT,
        project_engineer TEXT,
        status TEXT DEFAULT 'Active',
        created_date TEXT
    )""")

    # SUPPLIERS
    c.execute("""CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        supplier_name TEXT NOT NULL,
        contact_person TEXT,
        phone TEXT,
        email TEXT,
        gstin TEXT,
        address TEXT,
        category TEXT,
        payment_terms TEXT,
        bank_name TEXT,
        bank_account TEXT,
        bank_ifsc TEXT,
        status TEXT DEFAULT 'Active',
        notes TEXT,
        created_by TEXT,
        created_date TEXT
    )""")

    # QUOTATIONS
    c.execute("""CREATE TABLE IF NOT EXISTS quotations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quotation_number TEXT UNIQUE NOT NULL,
        client_id INTEGER REFERENCES clients(id),
        quotation_date TEXT,
        project_name TEXT,
        financial_year TEXT,
        gst_rate REAL DEFAULT 18,
        gst_type TEXT DEFAULT 'Intra-State',
        discount REAL DEFAULT 0,
        negotiated_amount REAL DEFAULT 0,
        approver_name TEXT,
        terms TEXT,
        payment_terms TEXT,
        status TEXT DEFAULT 'Draft',
        created_by TEXT,
        created_date TEXT,
        finalised_date TEXT
    )""")

    # QUOTATION LINE ITEMS
    c.execute("""CREATE TABLE IF NOT EXISTS quotation_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quotation_id INTEGER REFERENCES quotations(id) ON DELETE CASCADE,
        location TEXT,
        element TEXT,
        length_ft REAL DEFAULT 0,
        breadth_ft REAL DEFAULT 1,
        height_ft REAL DEFAULT 0,
        qty REAL DEFAULT 0,
        rate REAL DEFAULT 0,
        amount REAL DEFAULT 0,
        remarks TEXT,
        sort_order INTEGER DEFAULT 0
    )""")

    # DESIGN FILES
    c.execute("""CREATE TABLE IF NOT EXISTS design_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER REFERENCES clients(id),
        quotation_id INTEGER REFERENCES quotations(id),
        version TEXT,
        designer_names TEXT,
        notes TEXT,
        file_path TEXT,
        drive_link TEXT,
        uploaded_by TEXT,
        upload_date TEXT
    )""")

    # PROCUREMENT — complete schema with all conveyance + approval columns
    c.execute("""CREATE TABLE IF NOT EXISTS procurement (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER REFERENCES clients(id),
        quotation_id INTEGER REFERENCES quotations(id),
        entry_type TEXT DEFAULT 'Material',
        procurement_date TEXT,
        vendor_name TEXT,
        item_name TEXT,
        category TEXT,
        bill_number TEXT,
        amount REAL DEFAULT 0,
        payment_status TEXT DEFAULT 'Pending',
        file_path TEXT,
        drive_link TEXT,
        remarks TEXT,
        employee_name TEXT,
        conveyance_from TEXT,
        conveyance_to TEXT,
        conveyance_mode TEXT,
        conveyance_purpose TEXT,
        approval_status TEXT DEFAULT 'Pending',
        approved_by TEXT,
        approved_date TEXT,
        created_by TEXT,
        created_date TEXT
    )""")

    # WORK PROGRESS LOG
    c.execute("""CREATE TABLE IF NOT EXISTS work_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER REFERENCES clients(id),
        quotation_id INTEGER REFERENCES quotations(id),
        location TEXT,
        task TEXT,
        target_date TEXT,
        actual_completion_date TEXT,
        status TEXT DEFAULT 'Not Started',
        project_engineer TEXT,
        work_done TEXT,
        issues TEXT,
        next_action TEXT,
        created_by TEXT,
        created_date TEXT
    )""")

    # INVOICES
    c.execute("""CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        invoice_type TEXT NOT NULL,
        client_id INTEGER REFERENCES clients(id),
        quotation_id INTEGER REFERENCES quotations(id),
        invoice_date TEXT,
        gst_type TEXT,
        taxable_value REAL DEFAULT 0,
        reimbursement_amount REAL DEFAULT 0,
        cgst REAL DEFAULT 0,
        sgst REAL DEFAULT 0,
        igst REAL DEFAULT 0,
        total_amount REAL DEFAULT 0,
        terms TEXT,
        payment_terms TEXT,
        notes TEXT,
        status TEXT DEFAULT 'Draft',
        created_by TEXT,
        created_date TEXT,
        finalised_date TEXT
    )""")

    # RECEIPTS
    c.execute("""CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER REFERENCES invoices(id),
        invoice_number TEXT,
        invoice_type TEXT,
        receipt_date TEXT,
        amount REAL DEFAULT 0,
        mode TEXT,
        reference_number TEXT,
        remarks TEXT,
        created_by TEXT,
        created_date TEXT
    )""")

    conn.commit()

    # Run migrations for any existing databases missing new columns
    migrate_columns(c)
    conn.commit()

    # Create default admin user if not exists
    existing = c.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not existing:
        pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        c.execute("""INSERT INTO users
            (full_name,email,username,password_hash,role,designation,status,force_password_change,created_date)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            ("Administrator","admin@samvarddh.com","admin",pw_hash,
             "Admin","CXO","Active",1,datetime.now().isoformat()))
        c.execute("""INSERT INTO company_setup
            (brand_name,legal_name,city,state,website,default_terms)
            VALUES (?,?,?,?,?,?)""",
            ("SAMVARDDH","Samvarddh Associates Private Ltd.","Bengaluru","Karnataka",
             "www.samvarddh.com",
             "GST is charged under Section 15 on the supply of service and GST is not chargeable on the value of reimbursements for the expenses made as pure agent of the client as per Rule 33 of the CGST Rules, 2017."))
        conn.commit()

    conn.close()
    print("✅ Database initialised at:", DB_PATH)
