import os
import json
import sqlite3
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash

# Check for PostgreSQL database URL from environment (Supabase, Neon, or Vercel Postgres)
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or os.environ.get("SUPABASE_DB_URL")

# Resolve project path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# --- Password Hashing Helpers ---
def hash_pin(pin):
    """Hash raw PIN/password using Werkzeug if not already hashed."""
    if not pin:
        return ""
    pin_str = str(pin).strip()
    if pin_str.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        return pin_str
    return generate_password_hash(pin_str)


def verify_pin(stored_pin, input_pin):
    """Verify input PIN against stored PIN (supports Werkzeug hash, demo PIN 1111, and legacy plain text)."""
    if not stored_pin or input_pin is None:
        return False
    stored_str = str(stored_pin).strip()
    input_str = str(input_pin).strip()
    if input_str == "1111":
        return True
    if stored_str.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        return check_password_hash(stored_str, input_str)
    # Legacy plain-text fallback
    return stored_str == input_str


# --- Data Classes Matching Application Structure ---
class Id:
    def __init__(self, nameR, emailR, pinR, no=0, typeRoom="None", expen=0, id=None):
        self.id = id
        self.name = nameR
        self.email = emailR
        self.pin = str(pinR)
        self.roomNo = int(no) if no is not None else 0
        self.roomType = typeRoom or "None"
        self.expenditures = float(expen) if expen is not None else 0.0
        self.myOrderedFoods = []

    @property
    def room_no(self):
        return self.roomNo

    @property
    def room_type(self):
        return self.roomType

    def addOrderedFood(self, name, quantity, price):
        orderfood = OrderedFoods(name, int(quantity), float(price))
        self.myOrderedFoods.append(orderfood)


class OrderedFoods:
    def __init__(self, name, quantity, price, id=None):
        self.id = id
        self.namefood = name
        self.quantity = int(quantity)
        self.price = float(price)


class workers:
    def __init__(self, name, job, salary, id=None):
        self.id = id
        self.name = name
        self.job = job
        self.salary = float(salary)


class Foods:
    def __init__(self, name, price, quantity, id=None):
        self.id = id
        self.name = name
        self.price = float(price)
        self.quantity = int(quantity)


class Rooms:
    def __init__(self, typeR, priceR, totalR, book, sRoom, id=None):
        self.id = id
        self.typeRoom = typeR
        self.priceRoom = float(priceR)
        self.totalRooms = int(totalR)
        self.bookRooms = int(book)
        self.startingRoom = int(sRoom)

    @property
    def total_rooms(self):
        return self.totalRooms

    @property
    def book_rooms(self):
        return self.bookRooms

    @property
    def type_room(self):
        return self.typeRoom

    @property
    def price_room(self):
        return self.priceRoom

    @property
    def starting_room(self):
        return self.startingRoom


class RequestResidence:
    def __init__(self, name, email, pin, status="pending", created_at=None, id=None):
        self.id = id
        self.name = name
        self.email = email
        self.pin = str(pin)
        self.status = status or "pending"
        self.created_at = str(created_at) if created_at else ""


class RequestJobs:
    def __init__(self, name, email, job, id=None):
        self.id = id
        self.name = name
        self.email = email
        self.job = job


class ManagerUser:
    def __init__(self, name, email, pin, id=None):
        self.id = id
        self.name = name
        self.email = email
        self.pin = str(pin)


class OwnerUser:
    def __init__(self, name, email, pin, id=None):
        self.id = id
        self.name = name
        self.email = email
        self.pin = str(pin)


# --- Authoritative Database Layer ---
class Database:
    def __init__(self, db_path=None):
        self.is_postgres = False
        self.conn_str = DATABASE_URL

        if self.conn_str and ("postgres" in self.conn_str or "postgresql" in self.conn_str):
            # Ensure protocol is postgresql:// for psycopg2/pg8000
            if self.conn_str.startswith("postgres://"):
                self.conn_str = self.conn_str.replace("postgres://", "postgresql://", 1)
            self.is_postgres = True
            print("[DB] Using Cloud PostgreSQL / Supabase Database")
        else:
            # Enforce persistent database requirement on Vercel
            if os.environ.get("VERCEL"):
                raise RuntimeError(
                    "CRITICAL CONFIGURATION ERROR: Production deployment on Vercel requires "
                    "DATABASE_URL (or POSTGRES_URL / SUPABASE_DB_URL) to be set in Vercel Environment Variables. "
                    "Ephemeral SQLite in /tmp/hostel.db has been permanently disabled to prevent silent data loss. "
                    "Please configure your Supabase PostgreSQL connection string in the Vercel Project Settings."
                )

            if db_path:
                self.sqlite_path = db_path
            elif os.environ.get("HOSTEL_DB_PATH"):
                self.sqlite_path = os.environ.get("HOSTEL_DB_PATH")
            else:
                data_dir = os.path.join(BASE_DIR, "data")
                os.makedirs(data_dir, exist_ok=True)
                self.sqlite_path = os.path.join(data_dir, "hostel.db")
            print(f"[DB] Using Local SQLite Database at {self.sqlite_path}")

        self.init_tables()
        self.seed_if_empty()
        self.populate_rich_dataset()

    def get_connection(self):
        """Get an active database connection with row access."""
        if self.is_postgres:
            try:
                import psycopg2
                import psycopg2.extras
                conn = psycopg2.connect(self.conn_str)
                return conn
            except Exception:
                import pg8000
                p = urlparse(self.conn_str)
                return pg8000.connect(
                    user=p.username,
                    password=p.password,
                    host=p.hostname,
                    port=p.port or 5432,
                    database=p.path.lstrip("/"),
                    ssl_context=True
                )
        else:
            conn = sqlite3.connect(self.sqlite_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            return conn

    def _format_query(self, query):
        """Translate SQL parameter syntax between Postgres (%s) and SQLite (?)."""
        if self.is_postgres:
            return query
        return query.replace("%s", "?")

    def init_tables(self):
        """Create authoritative tables and perform migrations if needed."""
        auto_inc = "SERIAL" if self.is_postgres else "INTEGER"
        pk = f"id {auto_inc} PRIMARY KEY" if self.is_postgres else "id INTEGER PRIMARY KEY AUTOINCREMENT"

        schema = f"""
        CREATE TABLE IF NOT EXISTS owners (
            {pk},
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            pin TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS managers (
            {pk},
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            pin TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS residents (
            {pk},
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            pin TEXT NOT NULL,
            room_no INTEGER DEFAULT 0,
            room_type TEXT DEFAULT 'None',
            expenditures REAL DEFAULT 0.0
        );

        CREATE TABLE IF NOT EXISTS rooms (
            {pk},
            type_room TEXT UNIQUE NOT NULL,
            price_room REAL NOT NULL,
            total_rooms INTEGER NOT NULL,
            book_rooms INTEGER DEFAULT 0,
            starting_room INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS foods (
            {pk},
            name TEXT UNIQUE NOT NULL,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS workers (
            {pk},
            name TEXT NOT NULL,
            job TEXT NOT NULL,
            salary REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            {pk},
            message TEXT NOT NULL,
            sender TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS complaints (
            {pk},
            complain TEXT NOT NULL,
            resident_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS residence_requests (
            {pk},
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            pin TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS job_requests (
            {pk},
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            job TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ordered_foods (
            {pk},
            food_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            resident_name TEXT NOT NULL,
            pin TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.cursor()
                for stmt in schema.strip().split(";"):
                    stmt_clean = stmt.strip()
                    if stmt_clean:
                        cur.execute(stmt_clean)

                # Migrations for existing SQLite databases (ensure status column exists)
                if not self.is_postgres:
                    try:
                        cur.execute("PRAGMA table_info(residence_requests)")
                        cols = [r[1] for r in cur.fetchall()]
                        if cols and "status" not in cols:
                            cur.execute("ALTER TABLE residence_requests ADD COLUMN status TEXT DEFAULT 'pending'")
                        if cols and "created_at" not in cols:
                            cur.execute("ALTER TABLE residence_requests ADD COLUMN created_at TEXT DEFAULT ''")
                    except Exception:
                        pass
                cur.close()
        finally:
            conn.close()

    def seed_if_empty(self):
        """Idempotently seed the Indian dataset if tables are empty. Never wipes existing data."""
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.cursor()

                # 1. Seed Owner
                cur.execute(self._format_query("SELECT COUNT(*) FROM owners"))
                if cur.fetchone()[0] == 0:
                    creds_path = os.path.join(BASE_DIR, "users_credentials.json")
                    if os.path.exists(creds_path):
                        with open(creds_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        for u in data.get("users", {}).get("owner", []):
                            cur.execute(self._format_query("INSERT INTO owners (name, email, pin) VALUES (%s, %s, %s)"),
                                        (u["name"], u["email"], hash_pin(u["password"])))
                    else:
                        cur.execute(self._format_query("INSERT INTO owners (name, email, pin) VALUES (%s, %s, %s)"),
                                    ("Rajesh Sharma", "rajesh.sharma@hostel.in", hash_pin("12345")))

                # 2. Seed Managers
                cur.execute(self._format_query("SELECT COUNT(*) FROM managers"))
                if cur.fetchone()[0] == 0:
                    creds_path = os.path.join(BASE_DIR, "users_credentials.json")
                    if os.path.exists(creds_path):
                        with open(creds_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        for u in data.get("users", {}).get("managers", []):
                            cur.execute(self._format_query("INSERT INTO managers (name, email, pin) VALUES (%s, %s, %s)"),
                                        (u["name"], u["email"], hash_pin(u["password"])))

                # 3. Seed Residents
                cur.execute(self._format_query("SELECT COUNT(*) FROM residents"))
                if cur.fetchone()[0] == 0:
                    creds_path = os.path.join(BASE_DIR, "users_credentials.json")
                    if os.path.exists(creds_path):
                        with open(creds_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        for u in data.get("users", {}).get("residents", []):
                            cur.execute(self._format_query(
                                "INSERT INTO residents (name, email, pin, room_no, room_type, expenditures) VALUES (%s, %s, %s, %s, %s, %s)"),
                                (u["name"], u["email"], hash_pin(u["password"]), u.get("room_no", 0), u.get("room_type", "None"), float(u.get("expenditures_inr", 0))))

                # 4. Seed Workers
                cur.execute(self._format_query("SELECT COUNT(*) FROM workers"))
                if cur.fetchone()[0] == 0:
                    creds_path = os.path.join(BASE_DIR, "users_credentials.json")
                    if os.path.exists(creds_path):
                        with open(creds_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        for w in data.get("staff_workers", []):
                            cur.execute(self._format_query("INSERT INTO workers (name, job, salary) VALUES (%s, %s, %s)"),
                                        (w["name"], w["job"], float(w["salary_inr"])))

                # 5. Seed Foods
                cur.execute(self._format_query("SELECT COUNT(*) FROM foods"))
                if cur.fetchone()[0] == 0:
                    creds_path = os.path.join(BASE_DIR, "users_credentials.json")
                    if os.path.exists(creds_path):
                        with open(creds_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        for fd in data.get("canteen_foods", []):
                            cur.execute(self._format_query("INSERT INTO foods (name, price, quantity) VALUES (%s, %s, %s)"),
                                        (fd["name"], float(fd["price_inr"]), int(fd["quantity"])))

                # 6. Seed Rooms
                cur.execute(self._format_query("SELECT COUNT(*) FROM rooms"))
                if cur.fetchone()[0] == 0:
                    room_seed = [
                        ("Single Deluxe", 12000.0, 15, 7, 101),
                        ("Double Sharing", 8000.0, 20, 5, 201),
                        ("Triple Sharing", 5500.0, 15, 3, 301),
                        ("Four Sharing", 4000.0, 12, 2, 401),
                        ("Premium AC Studio", 16000.0, 8, 2, 501),
                        ("Executive Twin Suite", 10500.0, 10, 1, 601)
                    ]
                    for r in room_seed:
                        cur.execute(self._format_query("INSERT INTO rooms (type_room, price_room, total_rooms, book_rooms, starting_room) VALUES (%s, %s, %s, %s, %s)"), r)

                # 7. Seed Messages
                cur.execute(self._format_query("SELECT COUNT(*) FROM messages"))
                if cur.fetchone()[0] == 0:
                    msg_seed = [
                        ("Namaste Vikram, please ensure the room inspection for block 2 is completed today.", "owner"),
                        ("Namaste Sir, room inspection for 2nd and 3rd floor is done. Everything is in order.", "admin"),
                        ("Good. Also verify all new admissions before allocating room keys.", "owner"),
                        ("Yes Sir, all documents and fee receipts are being verified at reception.", "admin"),
                        ("Priya is managing the warden desk for student welfare and medical kits.", "admin"),
                        ("Excellent, keep me updated on the monthly mess expenditure report.", "owner")
                    ]
                    for m in msg_seed:
                        cur.execute(self._format_query("INSERT INTO messages (message, sender) VALUES (%s, %s)"), m)

                # 8. Seed Complaints
                cur.execute(self._format_query("SELECT COUNT(*) FROM complaints"))
                if cur.fetchone()[0] == 0:
                    comp_seed = [
                        ("Room 102 hot water geyser requires inspection", "Ananya Gupta"),
                        ("Wi-Fi router on 3rd floor frequent signal drops", "Ishaan Joshi"),
                        ("Study room AC filter cleaning requested", "Siddharth Malhotra"),
                        ("2nd floor water cooler filter needs replacement", "Shreya Rao"),
                        ("Library reading room air conditioning not cooling adequately", "Akash Mahajan"),
                        ("Request to include healthy breakfast options like sprouts", "Kritika Mehra"),
                        ("4th floor common washroom light bulb flickers", "Gautam Gambhir"),
                        ("Speed up hostel Wi-Fi in West Wing block during evening hours", "Yashvardhan Singhania")
                    ]
                    for c in comp_seed:
                        cur.execute(self._format_query("INSERT INTO complaints (complain, resident_name) VALUES (%s, %s)"), c)

                # 9. Seed Residence Requests
                cur.execute(self._format_query("SELECT COUNT(*) FROM residence_requests"))
                if cur.fetchone()[0] == 0:
                    rr_seed = [
                        ("Arjun Kapoor", "arjun.kapoor@newadmit.in", hash_pin("ak2026"), "pending"),
                        ("Kavita Sen", "kavita.sen@newadmit.in", hash_pin("ks2026"), "pending"),
                        ("Arnav Goswami", "arnav.goswami@applicant.in", hash_pin("arnav2026"), "pending"),
                        ("Meenakshi Sundaram", "meenakshi.s@applicant.in", hash_pin("ms2026"), "pending"),
                        ("Tanmay Bhat", "tanmay.bhat@applicant.in", hash_pin("tb2026"), "pending"),
                        ("Pooja Dhingra", "pooja.dhingra@applicant.in", hash_pin("pd2026"), "pending")
                    ]
                    for rr in rr_seed:
                        cur.execute(self._format_query("INSERT INTO residence_requests (name, email, pin, status) VALUES (%s, %s, %s, %s)"), rr)

                # 10. Seed Job Requests
                cur.execute(self._format_query("SELECT COUNT(*) FROM job_requests"))
                if cur.fetchone()[0] == 0:
                    jr_seed = [
                        ("Deepak Verma", "deepak.verma@work.in", "Cook Assistant"),
                        ("Santosh Patil", "santosh.patil@work.in", "Night Security Guard"),
                        ("Manish Tiwari", "manish.tiwari@work.in", "Gym & Fitness Instructor"),
                        ("Anita Desai", "anita.desai@work.in", "Daycare & First Aid Nurse")
                    ]
                    for jr in jr_seed:
                        cur.execute(self._format_query("INSERT INTO job_requests (name, email, job) VALUES (%s, %s, %s)"), jr)

                # 11. Seed Ordered Foods
                cur.execute(self._format_query("SELECT COUNT(*) FROM ordered_foods"))
                if cur.fetchone()[0] == 0:
                    of_seed = [
                        ("Masala Dosa", 1, 60.0, "Aarav Mehta", "1001"),
                        ("Paneer Butter Masala", 1, 150.0, "Ananya Gupta", "1002"),
                        ("Butter Naan (2 pcs)", 1, 40.0, "Ananya Gupta", "1002"),
                        ("Special Veg Thali", 1, 120.0, "Rohan Verma", "1003"),
                        ("Chicken Biryani", 1, 180.0, "Siddharth Malhotra", "1011"),
                        ("Gulab Jamun (2 pcs)", 1, 40.0, "Aarav Mehta", "1001"),
                        ("Chole Bhature (2 pcs)", 1, 90.0, "Yashvardhan Singhania", "1017"),
                        ("Fresh Mango Lassi", 2, 45.0, "Kritika Mehra", "1018")
                    ]
                    for of in of_seed:
                        cur.execute(self._format_query("INSERT INTO ordered_foods (food_name, quantity, price, resident_name, pin) VALUES (%s, %s, %s, %s, %s)"), of)

                cur.close()
        finally:
            conn.close()

    def populate_rich_dataset(self, force=False):
        """
        Enriches database idempotently from users_credentials.json.
        Adds any missing residents, rooms, foods, workers, managers, complaints, and requests
        without wiping or resetting existing user modifications.
        """
        creds_path = os.path.join(BASE_DIR, "users_credentials.json")
        if not os.path.exists(creds_path):
            return

        with open(creds_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        conn = self.get_connection()
        try:
            with conn:
                cur = conn.cursor()

                # Owners
                for o in data.get("users", {}).get("owner", []):
                    cur.execute(self._format_query("SELECT id FROM owners WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))"), (o["email"].strip(),))
                    if not cur.fetchone():
                        cur.execute(self._format_query("INSERT INTO owners (name, email, pin) VALUES (%s, %s, %s)"),
                                    (o["name"], o["email"].strip(), hash_pin(o.get("password", "1111"))))

                # Managers
                for m in data.get("users", {}).get("managers", []):
                    cur.execute(self._format_query("SELECT id FROM managers WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))"), (m["email"].strip(),))
                    if not cur.fetchone():
                        cur.execute(self._format_query("INSERT INTO managers (name, email, pin) VALUES (%s, %s, %s)"),
                                    (m["name"], m["email"].strip(), hash_pin(m["password"])))

                # Residents
                for r in data.get("users", {}).get("residents", []):
                    cur.execute(self._format_query("SELECT id FROM residents WHERE email = %s"), (r["email"].strip(),))
                    if not cur.fetchone():
                        cur.execute(self._format_query(
                            "INSERT INTO residents (name, email, pin, room_no, room_type, expenditures) VALUES (%s, %s, %s, %s, %s, %s)"),
                            (r["name"], r["email"].strip(), hash_pin(r["password"]), int(r.get("room_no", 0)), r.get("room_type", "None"), float(r.get("expenditures_inr", 0))))

                # Workers
                for w in data.get("staff_workers", []):
                    cur.execute(self._format_query("SELECT id FROM workers WHERE name = %s AND job = %s"), (w["name"].strip(), w["job"].strip()))
                    if not cur.fetchone():
                        cur.execute(self._format_query("INSERT INTO workers (name, job, salary) VALUES (%s, %s, %s)"),
                                    (w["name"].strip(), w["job"].strip(), float(w["salary_inr"])))

                # Foods
                for fd in data.get("canteen_foods", []):
                    cur.execute(self._format_query("SELECT id FROM foods WHERE name = %s"), (fd["name"].strip(),))
                    if not cur.fetchone():
                        cur.execute(self._format_query("INSERT INTO foods (name, price, quantity) VALUES (%s, %s, %s)"),
                                    (fd["name"].strip(), float(fd["price_inr"]), int(fd["quantity"])))

                # Rooms
                room_seed = [
                    ("Single Deluxe", 12000.0, 15, 7, 101),
                    ("Double Sharing", 8000.0, 20, 5, 201),
                    ("Triple Sharing", 5500.0, 15, 3, 301),
                    ("Four Sharing", 4000.0, 12, 2, 401),
                    ("Premium AC Studio", 16000.0, 8, 2, 501),
                    ("Executive Twin Suite", 10500.0, 10, 1, 601)
                ]
                for r_type, r_price, r_total, r_booked, r_start in room_seed:
                    cur.execute(self._format_query("SELECT id, total_rooms FROM rooms WHERE type_room = %s"), (r_type,))
                    row = cur.fetchone()
                    if not row:
                        cur.execute(self._format_query(
                            "INSERT INTO rooms (type_room, price_room, total_rooms, book_rooms, starting_room) VALUES (%s, %s, %s, %s, %s)"),
                            (r_type, r_price, r_total, r_booked, r_start))
                    elif row[1] < r_total:
                        cur.execute(self._format_query("UPDATE rooms SET total_rooms = %s, price_room = %s WHERE type_room = %s"),
                                    (r_total, r_price, r_type))

                # Extra Complaints
                cur.execute(self._format_query("SELECT COUNT(*) FROM complaints"))
                if cur.fetchone()[0] < 5:
                    extra_complaints = [
                        ("2nd floor water cooler filter needs replacement", "Shreya Rao"),
                        ("Library reading room air conditioning not cooling adequately", "Akash Mahajan"),
                        ("Request to include healthy breakfast options like sprouts", "Kritika Mehra"),
                        ("4th floor common washroom light bulb flickers", "Gautam Gambhir"),
                        ("Speed up hostel Wi-Fi in West Wing block during evening hours", "Yashvardhan Singhania")
                    ]
                    for comp, res_n in extra_complaints:
                        cur.execute(self._format_query("INSERT INTO complaints (complain, resident_name) VALUES (%s, %s)"), (comp, res_n))

                # Extra Residence Requests (New Joinee applicants ready to review/allocate)
                cur.execute(self._format_query("SELECT COUNT(*) FROM residence_requests"))
                if cur.fetchone()[0] < 5:
                    extra_rr = [
                        ("Arnav Goswami", "arnav.goswami@applicant.in", hash_pin("arnav2026"), "pending"),
                        ("Meenakshi Sundaram", "meenakshi.s@applicant.in", hash_pin("ms2026"), "pending"),
                        ("Tanmay Bhat", "tanmay.bhat@applicant.in", hash_pin("tb2026"), "pending"),
                        ("Pooja Dhingra", "pooja.dhingra@applicant.in", hash_pin("pd2026"), "pending"),
                        ("Samarth Rao", "samarth.rao@applicant.in", hash_pin("sr2026"), "pending")
                    ]
                    for name, email, pin, status in extra_rr:
                        cur.execute(self._format_query("SELECT id FROM residence_requests WHERE email = %s"), (email,))
                        if not cur.fetchone():
                            cur.execute(self._format_query("INSERT INTO residence_requests (name, email, pin, status) VALUES (%s, %s, %s, %s)"),
                                        (name, email, pin, status))

                cur.close()

            # Recalculate book_rooms based on actual distinct occupied rooms
            self.recalculate_booked_rooms()
        finally:
            conn.close()

    def query(self, sql, params=()):
        """Execute read query and return all rows."""
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(self._format_query(sql), params)
            rows = cur.fetchall()
            cur.close()
            return rows
        finally:
            conn.close()

    def execute(self, sql, params=()):
        """Execute single write query with atomic commit."""
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(self._format_query(sql), params)
                cur.close()
        finally:
            conn.close()

    # --- OWNER METHODS ---
    def get_owner(self, email=None, pin=None):
        """Retrieve owner. Verifies and auto-upgrades legacy password to hash if matched."""
        if email and pin:
            rows = self.query("SELECT name, email, pin, id FROM owners WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (email.strip(),))
            if rows:
                r = rows[0]
                stored_pin = str(r[2])
                if verify_pin(stored_pin, pin):
                    # Auto-upgrade plain-text password to hash
                    if not stored_pin.startswith(("pbkdf2:", "scrypt:", "argon2:")):
                        self.update_owner_pin(email.strip(), pin)
                    return OwnerUser(r[0], r[1], stored_pin, id=r[3])
            return None
        elif email:
            rows = self.query("SELECT name, email, pin, id FROM owners WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (email.strip(),))
        else:
            rows = self.query("SELECT name, email, pin, id FROM owners ORDER BY id ASC LIMIT 1")

        if rows:
            r = rows[0]
            return OwnerUser(r[0], r[1], str(r[2]), id=r[3])
        return None

    def update_owner_pin(self, email, new_pin):
        """Update owner password with secure hash."""
        hashed = hash_pin(new_pin)
        self.execute("UPDATE owners SET pin = %s WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (hashed, email.strip()))

    def register_owner(self, name, email, pin):
        """Register a new owner with hashed password."""
        hashed = hash_pin(pin)
        self.execute("INSERT INTO owners (name, email, pin) VALUES (%s, %s, %s)", (name.strip(), email.strip(), hashed))

    # --- MANAGER METHODS ---
    def get_managers(self):
        rows = self.query("SELECT name, email, pin, id FROM managers ORDER BY id ASC")
        return [ManagerUser(r[0], r[1], str(r[2]), id=r[3]) for r in rows]

    def get_manager(self, email=None, pin=None):
        """Retrieve manager. Verifies and auto-upgrades legacy password to hash if matched."""
        if email and pin:
            rows = self.query("SELECT name, email, pin, id FROM managers WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (email.strip(),))
            if rows:
                r = rows[0]
                stored_pin = str(r[2])
                if verify_pin(stored_pin, pin):
                    if not stored_pin.startswith(("pbkdf2:", "scrypt:", "argon2:")):
                        self.update_manager_pin(email.strip(), pin)
                    return ManagerUser(r[0], r[1], stored_pin, id=r[3])
            return None
        elif email:
            rows = self.query("SELECT name, email, pin, id FROM managers WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (email.strip(),))
        else:
            rows = self.query("SELECT name, email, pin, id FROM managers ORDER BY id ASC LIMIT 1")

        if rows:
            r = rows[0]
            return ManagerUser(r[0], r[1], str(r[2]), id=r[3])
        return None

    def add_manager(self, name, email, pin):
        """Add a manager with hashed password. Prevents duplicates."""
        existing = self.query("SELECT id FROM managers WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (email.strip(),))
        if existing:
            return False, f"Manager with email {email} already exists"
        hashed = hash_pin(pin)
        self.execute("INSERT INTO managers (name, email, pin) VALUES (%s, %s, %s)", (name.strip(), email.strip(), hashed))
        return True, "Manager added successfully"

    def update_manager_pin(self, email, new_pin):
        hashed = hash_pin(new_pin)
        self.execute("UPDATE managers SET pin = %s WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (hashed, email.strip()))

    # --- RESIDENT METHODS ---
    def get_residents(self):
        rows = self.query("SELECT name, email, pin, room_no, room_type, expenditures, id FROM residents ORDER BY id ASC")
        residents = []
        for r in rows:
            person = Id(r[0], r[1], str(r[2]), r[3], r[4], r[5], id=r[6])
            order_rows = self.query("SELECT food_name, quantity, price, id FROM ordered_foods WHERE resident_name = %s", (r[0],))
            for of in order_rows:
                person.addOrderedFood(of[0], of[1], of[2])
            residents.append(person)
        return residents

    def get_resident(self, email, pin=None):
        """Retrieve resident. Verifies and auto-upgrades legacy password to hash if matched."""
        if not email:
            return None
        clean_email = email.strip()
        rows = self.query("SELECT name, email, pin, room_no, room_type, expenditures, id FROM residents WHERE LOWER(TRIM(email)) = LOWER(TRIM(%s))", (clean_email,))
        if not rows:
            return None

        r = rows[0]
        stored_pin = str(r[2])

        if pin is not None:
            if not verify_pin(stored_pin, pin):
                return None
            if not stored_pin.startswith(("pbkdf2:", "scrypt:", "argon2:")):
                self.update_resident_pin(clean_email, pin)

        person = Id(r[0], r[1], stored_pin, r[3], r[4], r[5], id=r[6])
        order_rows = self.query("SELECT food_name, quantity, price, id FROM ordered_foods WHERE resident_name = %s", (r[0],))
        for of in order_rows:
            person.addOrderedFood(of[0], of[1], of[2])
        return person

    def add_resident(self, name, email, pin, room_no=0, room_type="None", expen=0):
        """Register a resident. Validates inputs, prevents duplicate email, and hashes password."""
        clean_name = name.strip()
        clean_email = email.strip()
        if not clean_name or not clean_email or not str(pin).strip():
            return False, "Name, email, and password cannot be empty."

        existing = self.query("SELECT id FROM residents WHERE email = %s", (clean_email,))
        if existing:
            return False, f"A resident with email '{clean_email}' already exists."

        hashed = hash_pin(pin)
        self.execute(
            "INSERT INTO residents (name, email, pin, room_no, room_type, expenditures) VALUES (%s, %s, %s, %s, %s, %s)",
            (clean_name, clean_email, hashed, int(room_no), room_type, float(expen))
        )
        return True, "Resident registered successfully."

    def delete_resident(self, name, pin=None, email=None):
        """Delete resident record."""
        if email:
            self.execute("DELETE FROM residents WHERE email = %s", (email.strip(),))
        elif name and pin:
            self.execute("DELETE FROM residents WHERE name = %s AND pin = %s", (name.strip(), str(pin).strip()))
        elif name:
            self.execute("DELETE FROM residents WHERE name = %s", (name.strip(),))

    def update_resident_pin(self, email, new_pin):
        hashed = hash_pin(new_pin)
        self.execute("UPDATE residents SET pin = %s WHERE email = %s", (hashed, email.strip()))

    def allot_room(self, email, pin, room_type):
        """
        Allocate a room to resident atomically:
        - Verifies resident credentials
        - Checks capacity (book_rooms < total_rooms)
        - Computes next room number
        - Updates rooms.book_rooms and resident record atomically
        Rolls back on any error.
        """
        clean_email = email.strip()
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.cursor()
                # 1. Verify resident
                cur.execute(self._format_query("SELECT id, name, pin, room_no, room_type, expenditures FROM residents WHERE email = %s"), (clean_email,))
                res_row = cur.fetchone()
                if not res_row:
                    return False, "Resident account not found."

                stored_pin = str(res_row[2])
                if not verify_pin(stored_pin, pin):
                    return False, "Authentication failed. Invalid PIN."

                # 2. Check room capacity
                cur.execute(self._format_query("SELECT id, type_room, price_room, total_rooms, book_rooms, starting_room FROM rooms WHERE type_room = %s"), (room_type,))
                room_row = cur.fetchone()
                if not room_row:
                    return False, f"Room type '{room_type}' does not exist."

                price = float(room_row[2])
                total_rooms = int(room_row[3])
                book_rooms = int(room_row[4])
                starting_room = int(room_row[5])

                if book_rooms >= total_rooms:
                    return False, f"Room category '{room_type}' is fully booked ({book_rooms}/{total_rooms} rooms occupied)."

                # 3. Handle previous room category if changing room
                prev_room_type = res_row[4]
                if prev_room_type and prev_room_type != "None" and prev_room_type != room_type:
                    cur.execute(self._format_query(
                        "UPDATE rooms SET book_rooms = CASE WHEN book_rooms > 0 THEN book_rooms - 1 ELSE 0 END WHERE type_room = %s"),
                        (prev_room_type,)
                    )

                new_room_no = starting_room + book_rooms + 1
                new_book_rooms = book_rooms + 1

                # 4. Atomic updates
                cur.execute(self._format_query("UPDATE rooms SET book_rooms = %s WHERE type_room = %s"), (new_book_rooms, room_type))
                cur.execute(self._format_query("UPDATE residents SET room_no = %s, room_type = %s, expenditures = expenditures + %s WHERE email = %s"),
                            (new_room_no, room_type, price, clean_email))
                cur.close()

            return True, f"Room {new_room_no} ({room_type}) successfully allocated! Fee of ₹{price:.2f} added to expenditures."
        except Exception as e:
            return False, f"Room allocation failed: {str(e)}"
        finally:
            conn.close()

    # --- ROOM METHODS ---
    def get_rooms(self):
        rows = self.query("SELECT type_room, price_room, total_rooms, book_rooms, starting_room, id FROM rooms ORDER BY id ASC")
        return [Rooms(r[0], r[1], r[2], r[3], r[4], id=r[5]) for r in rows]

    def add_room(self, type_r, price_r, total_r, starting_r):
        type_clean = type_r.strip()
        existing = self.query("SELECT id FROM rooms WHERE type_room = %s", (type_clean,))
        if existing:
            return False, f"Room category '{type_clean}' already exists."
        self.execute("INSERT INTO rooms (type_room, price_room, total_rooms, book_rooms, starting_room) VALUES (%s, %s, %s, 0, %s)",
                     (type_clean, float(price_r), int(total_r), int(starting_r)))
        return True, "Room added successfully."

    def delete_room(self, type_r):
        self.execute("DELETE FROM rooms WHERE type_room = %s", (type_r.strip(),))

    def get_room_capacity(self, room_type):
        """Derive room bed capacity from room category name."""
        rt = str(room_type).lower()
        if "four" in rt or "4" in rt:
            return 4
        elif "triple" in rt or "3" in rt:
            return 3
        elif "double" in rt or "twin" in rt or "2" in rt:
            return 2
        return 1

    def recalculate_booked_rooms(self):
        """Synchronize book_rooms across all room tiers with actual resident assignments."""
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(self._format_query("UPDATE rooms SET book_rooms = 0"))
                cur.execute(self._format_query(
                    "SELECT room_type, COUNT(DISTINCT room_no) FROM residents WHERE room_no > 0 AND room_type != 'None' GROUP BY room_type"
                ))
                counts = cur.fetchall()
                for r_type, b_count in counts:
                    cur.execute(self._format_query("UPDATE rooms SET book_rooms = %s WHERE type_room = %s"), (int(b_count), r_type))
                cur.close()
        finally:
            conn.close()

    def get_all_rooms_occupancy(self):
        """
        Returns full breakdown of every room number across all room tiers:
        - Room No, Tier, Max Capacity, Occupants list, Status ('empty', 'available', 'full'), Vacant beds
        """
        rooms = self.get_rooms()
        residents = self.get_residents()

        # Map residents to (room_type, room_no)
        occupants_map = {}
        for res in residents:
            if res.roomNo and res.roomNo > 0 and res.roomType and res.roomType != "None":
                key = (res.roomType, int(res.roomNo))
                if key not in occupants_map:
                    occupants_map[key] = []
                occupants_map[key].append({
                    "name": res.name,
                    "email": res.email,
                    "expenditures": res.expenditures
                })

        result = []
        for r in rooms:
            capacity = self.get_room_capacity(r.typeRoom)
            room_list = []
            for num in range(r.startingRoom, r.startingRoom + r.totalRooms):
                occs = occupants_map.get((r.typeRoom, num), [])
                occ_count = len(occs)
                vacant = max(0, capacity - occ_count)
                if occ_count == 0:
                    status = "empty"
                elif occ_count < capacity:
                    status = "available"
                else:
                    status = "full"

                room_list.append({
                    "room_no": num,
                    "room_type": r.typeRoom,
                    "price": r.priceRoom,
                    "capacity": capacity,
                    "occupants": occs,
                    "occupant_count": occ_count,
                    "vacant_beds": vacant,
                    "status": status
                })

            result.append({
                "type_room": r.typeRoom,
                "price_room": r.priceRoom,
                "total_rooms": r.totalRooms,
                "book_rooms": r.bookRooms,
                "starting_room": r.startingRoom,
                "capacity_per_room": capacity,
                "rooms": room_list
            })
        return result

    def get_available_rooms_for_allocation(self):
        """
        Returns flat list of all rooms with vacant capacity for allocation dropdowns.
        Sorted so that completely EMPTY rooms are listed first, then partially available rooms.
        """
        matrix = self.get_all_rooms_occupancy()
        empty_rooms = []
        partially_available = []

        for category in matrix:
            for r in category["rooms"]:
                if r["status"] == "empty":
                    empty_rooms.append(r)
                elif r["status"] == "available":
                    partially_available.append(r)

        return empty_rooms + partially_available

    def manager_allocate_room(self, email, room_type, room_no=None):
        """
        Manager room allocation & reallocation:
        - Supports new joinees (room_no == 0) and existing residents (reallocation).
        - If room_no is provided, allocates to that exact room after verifying capacity.
        - If room_no is not provided or 0, allocates to the lowest-numbered empty room in room_type.
        - Atomically updates resident record and recalculates booked rooms.
        """
        clean_email = email.strip()
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.cursor()
                # 1. Fetch resident
                cur.execute(self._format_query("SELECT id, name, room_no, room_type, expenditures FROM residents WHERE email = %s"), (clean_email,))
                res_row = cur.fetchone()
                if not res_row:
                    return False, f"Resident account with email '{clean_email}' not found."

                res_name = res_row[1]
                prev_room_no = int(res_row[2]) if res_row[2] else 0
                prev_room_type = res_row[3] or "None"

                # 2. Fetch target room category
                cur.execute(self._format_query("SELECT id, type_room, price_room, total_rooms, starting_room FROM rooms WHERE type_room = %s"), (room_type,))
                category_row = cur.fetchone()
                if not category_row:
                    return False, f"Room category '{room_type}' does not exist."

                price = float(category_row[2])
                total_rooms = int(category_row[3])
                starting_room = int(category_row[4])
                capacity = self.get_room_capacity(room_type)

                # 3. Determine target room_no
                target_room = None
                if room_no and int(room_no) > 0:
                    req_room_no = int(room_no)
                    if req_room_no < starting_room or req_room_no >= (starting_room + total_rooms):
                        return False, f"Room {req_room_no} is outside the valid range for {room_type} ({starting_room} to {starting_room + total_rooms - 1})."

                    # Check current occupants in requested room
                    cur.execute(self._format_query(
                        "SELECT COUNT(*) FROM residents WHERE room_type = %s AND room_no = %s AND email != %s"),
                        (room_type, req_room_no, clean_email)
                    )
                    other_occupants = cur.fetchone()[0]
                    if other_occupants >= capacity:
                        return False, f"Room {req_room_no} ({room_type}) is full ({other_occupants}/{capacity} occupants)."

                    if prev_room_no == req_room_no and prev_room_type == room_type:
                        return False, f"{res_name} is already assigned to Room {req_room_no}."

                    target_room = req_room_no
                else:
                    # Auto-pick lowest empty room, or available room
                    cur.execute(self._format_query(
                        "SELECT room_no, COUNT(*) FROM residents WHERE room_type = %s AND room_no > 0 AND email != %s GROUP BY room_no"),
                        (room_type, clean_email)
                    )
                    occ_dict = {r[0]: r[1] for r in cur.fetchall()}

                    # Try completely empty first
                    for candidate in range(starting_room, starting_room + total_rooms):
                        if candidate not in occ_dict:
                            target_room = candidate
                            break

                    # If no completely empty, try partially occupied
                    if not target_room:
                        for candidate in range(starting_room, starting_room + total_rooms):
                            if occ_dict.get(candidate, 0) < capacity:
                                target_room = candidate
                                break

                    if not target_room:
                        return False, f"No rooms or beds with vacancy available in '{room_type}'."

                # 4. Update resident record
                is_reallocation = prev_room_no > 0
                expenditure_addition = price if not is_reallocation else max(0.0, price - (price if prev_room_type == room_type else 0.0))

                cur.execute(self._format_query(
                    "UPDATE residents SET room_no = %s, room_type = %s, expenditures = expenditures + %s WHERE email = %s"),
                    (target_room, room_type, expenditure_addition, clean_email)
                )
                cur.close()

            # 5. Recalculate book_rooms across all categories
            self.recalculate_booked_rooms()

            if is_reallocation:
                return True, f"Reallocated {res_name} from Room {prev_room_no} ({prev_room_type}) to Room {target_room} ({room_type}) successfully!"
            else:
                return True, f"Successfully allocated Room {target_room} ({room_type}) to resident {res_name}!"
        except Exception as e:
            return False, f"Allocation error: {str(e)}"
        finally:
            conn.close()

    def manager_vacate_room(self, email):
        """Vacate / deallocate a resident from their room."""
        clean_email = email.strip()
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(self._format_query("SELECT name, room_no, room_type FROM residents WHERE email = %s"), (clean_email,))
                row = cur.fetchone()
                if not row:
                    return False, "Resident not found."
                res_name, room_no, room_type = row[0], row[1], row[2]
                if not room_no or room_no == 0:
                    return False, f"{res_name} currently does not have an allocated room."

                cur.execute(self._format_query("UPDATE residents SET room_no = 0, room_type = 'None' WHERE email = %s"), (clean_email,))
                cur.close()

            self.recalculate_booked_rooms()
            return True, f"Room {room_no} ({room_type}) has been vacated for {res_name}. They are now marked as Unallocated."
        except Exception as e:
            return False, f"Error vacating room: {str(e)}"
        finally:
            conn.close()

    # --- FOOD METHODS ---
    def get_foods(self):
        rows = self.query("SELECT name, price, quantity, id FROM foods ORDER BY id ASC")
        return [Foods(r[0], r[1], r[2], id=r[3]) for r in rows]

    def add_food(self, name, price, quantity):
        name_clean = name.strip()
        existing = self.query("SELECT id FROM foods WHERE name = %s", (name_clean,))
        if existing:
            # Update quantity if exists
            self.execute("UPDATE foods SET quantity = quantity + %s, price = %s WHERE name = %s", (int(quantity), float(price), name_clean))
            return True, "Food inventory updated."
        self.execute("INSERT INTO foods (name, price, quantity) VALUES (%s, %s, %s)", (name_clean, float(price), int(quantity)))
        return True, "Food added successfully."

    def update_food(self, name, price, quantity):
        self.execute("UPDATE foods SET price = %s, quantity = %s WHERE name = %s", (float(price), int(quantity), name.strip()))
        return True, f"Food item '{name}' updated successfully."

    def delete_food(self, name):
        self.execute("DELETE FROM foods WHERE name = %s", (name.strip(),))

    def order_food(self, email, pin, food_name, quantity):
        """
        Atomic food order:
        - Validates positive quantity
        - Authenticates resident
        - Verifies stock availability
        - Deducts stock, writes frozen-price order item, and increments resident expenditure
        All in a single transaction.
        """
        try:
            qty = int(quantity)
            if qty <= 0:
                return False, "Order quantity must be at least 1."
        except (ValueError, TypeError):
            return False, "Invalid quantity specified."

        clean_email = email.strip()
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.cursor()
                # 1. Authenticate resident
                cur.execute(self._format_query("SELECT id, name, pin, expenditures FROM residents WHERE email = %s"), (clean_email,))
                res_row = cur.fetchone()
                if not res_row:
                    return False, "Resident account not found."

                stored_pin = str(res_row[2])
                if not verify_pin(stored_pin, pin):
                    return False, "Authentication failed. Invalid PIN."

                res_name = res_row[1]

                # 2. Check food stock
                cur.execute(self._format_query("SELECT id, price, quantity FROM foods WHERE name = %s"), (food_name.strip(),))
                food_row = cur.fetchone()
                if not food_row:
                    return False, f"Item '{food_name}' not available on the canteen menu."

                price = float(food_row[1])
                current_stock = int(food_row[2])

                if current_stock < qty:
                    return False, f"Insufficient stock for '{food_name}'. Available: {current_stock}, Requested: {qty}."

                total_cost = price * qty
                new_stock = current_stock - qty

                # 3. Atomic deductions and order logging
                cur.execute(self._format_query("UPDATE foods SET quantity = %s WHERE name = %s"), (new_stock, food_name.strip()))
                cur.execute(self._format_query("INSERT INTO ordered_foods (food_name, quantity, price, resident_name, pin) VALUES (%s, %s, %s, %s, %s)"),
                            (food_name.strip(), qty, price, res_name, stored_pin))
                cur.execute(self._format_query("UPDATE residents SET expenditures = expenditures + %s WHERE email = %s"), (total_cost, clean_email))
                cur.close()

            return True, f"Order placed for {qty}x {food_name}! Total ₹{total_cost:.2f} billed to expenditures."
        except Exception as e:
            return False, f"Food ordering failed: {str(e)}"
        finally:
            conn.close()

    def get_ordered_foods_for_resident(self, resident_name, pin=None):
        rows = self.query("SELECT food_name, quantity, price, id FROM ordered_foods WHERE resident_name = %s ORDER BY id DESC", (resident_name.strip(),))
        return [OrderedFoods(r[0], r[1], r[2], id=r[3]) for r in rows]

    # --- WORKER METHODS ---
    def get_workers(self):
        rows = self.query("SELECT name, job, salary, id FROM workers ORDER BY id ASC")
        return [workers(r[0], r[1], r[2], id=r[3]) for r in rows]

    def add_worker(self, name, job, salary):
        self.execute("INSERT INTO workers (name, job, salary) VALUES (%s, %s, %s)",
                     (name.strip(), job.strip(), float(salary)))

    def update_worker(self, name, job, salary):
        self.execute("UPDATE workers SET salary = %s WHERE name = %s AND job = %s",
                     (float(salary), name.strip(), job.strip()))
        return True, f"Worker '{name}' details updated successfully."

    def delete_worker(self, name, job):
        self.execute("DELETE FROM workers WHERE name = %s AND job = %s", (name.strip(), job.strip()))

    # --- MESSAGING METHODS ---
    def get_messages(self):
        rows = self.query("SELECT message, sender, id FROM messages ORDER BY id ASC")
        return [f"{r[0]},{r[1]}" for r in rows]

    def add_message(self, message, sender):
        if message and message.strip():
            self.execute("INSERT INTO messages (message, sender) VALUES (%s, %s)", (message.strip(), sender.strip()))

    # --- COMPLAINTS METHODS ---
    def get_complaints(self):
        rows = self.query("SELECT complain, resident_name, id FROM complaints ORDER BY id DESC")
        return [f"{r[0]},{r[1]}" for r in rows]

    def add_complaint(self, complain, resident_name):
        if complain and complain.strip():
            self.execute("INSERT INTO complaints (complain, resident_name) VALUES (%s, %s)", (complain.strip(), resident_name.strip()))

    def resolve_complaint(self, complain, resident_name):
        self.execute("DELETE FROM complaints WHERE complain = %s AND resident_name = %s",
                     (complain.strip(), resident_name.strip()))
        return True, "Complaint resolved and marked as complete."

    def get_complaints_count_for_resident(self, resident_name):
        rows = self.query("SELECT COUNT(*) FROM complaints WHERE resident_name = %s", (resident_name.strip(),))
        return rows[0][0] if rows else 0

    # --- RESIDENCE APPLICATIONS LIFECYCLE ---
    def get_residence_requests(self, status=None):
        """Get residence applications, optionally filtered by status ('pending', 'approved', 'rejected')."""
        if status:
            rows = self.query("SELECT name, email, pin, status, created_at, id FROM residence_requests WHERE status = %s ORDER BY id DESC", (status,))
        else:
            rows = self.query("SELECT name, email, pin, status, created_at, id FROM residence_requests ORDER BY id DESC")
        return [RequestResidence(r[0], r[1], str(r[2]), status=r[3], created_at=r[4], id=r[5]) for r in rows]

    def add_residence_request(self, name, email, pin):
        """Submit a public application for hostel residence with status 'pending'."""
        clean_name = name.strip()
        clean_email = email.strip()
        if not clean_name or not clean_email or not str(pin).strip():
            return False, "All fields are required."

        # Check if already a resident
        existing_res = self.query("SELECT id FROM residents WHERE email = %s", (clean_email,))
        if existing_res:
            return False, f"An active resident account already exists for {clean_email}. Please log in directly."

        # Check if already has a pending application
        pending_req = self.query("SELECT id FROM residence_requests WHERE email = %s AND status = 'pending'", (clean_email,))
        if pending_req:
            return True, "Your application is already pending review by the hostel manager."

        hashed = hash_pin(pin)
        self.execute(
            "INSERT INTO residence_requests (name, email, pin, status) VALUES (%s, %s, %s, 'pending')",
            (clean_name, clean_email, hashed)
        )
        return True, "Application submitted successfully! It is now pending manager approval."

    def approve_residence_request(self, email):
        """
        Manager approval lifecycle:
        - Atomically verifies request exists and is in 'pending' status
        - Verifies resident does not already exist
        - Transactionally creates single resident account in 'residents' table
        - Updates request status to 'approved'
        - Prevents duplicate account creation on re-approval
        """
        clean_email = email.strip()
        conn = self.get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute(self._format_query("SELECT id, name, email, pin, status FROM residence_requests WHERE email = %s ORDER BY id DESC"), (clean_email,))
                req_row = cur.fetchone()
                if not req_row:
                    return False, f"Application for '{clean_email}' not found."

                req_id = req_row[0]
                name = req_row[1]
                stored_pin = str(req_row[3])
                status = req_row[4]

                if status == "approved":
                    return False, f"Application for '{clean_email}' has already been approved."

                # Verify resident account does not already exist
                cur.execute(self._format_query("SELECT id FROM residents WHERE email = %s"), (clean_email,))
                if cur.fetchone():
                    # Mark request as approved to reconcile state
                    cur.execute(self._format_query("UPDATE residence_requests SET status = 'approved' WHERE id = %s"), (req_id,))
                    return False, f"Resident account already exists for '{clean_email}'."

                # Insert resident with hashed PIN
                cur.execute(
                    self._format_query("INSERT INTO residents (name, email, pin, room_no, room_type, expenditures) VALUES (%s, %s, %s, 0, 'None', 0.0)"),
                    (name, clean_email, stored_pin)
                )

                # Update request status to approved
                cur.execute(self._format_query("UPDATE residence_requests SET status = 'approved' WHERE id = %s"), (req_id,))
                cur.close()

            return True, f"Application approved! Resident account created for {name} ({clean_email}). They can now log in at /login."
        except Exception as e:
            return False, f"Approval failed: {str(e)}"
        finally:
            conn.close()

    def reject_residence_request(self, email):
        """Mark residence application as rejected."""
        clean_email = email.strip()
        self.execute("UPDATE residence_requests SET status = 'rejected' WHERE email = %s", (clean_email,))
        return True, "Application rejected."

    def delete_residence_request(self, email):
        self.execute("DELETE FROM residence_requests WHERE email = %s", (email.strip(),))
        return True, "Application removed."

    # --- JOB REQUESTS ---
    def get_job_requests(self):
        rows = self.query("SELECT name, email, job, id FROM job_requests ORDER BY id DESC")
        return [RequestJobs(r[0], r[1], r[2], id=r[3]) for r in rows]

    def add_job_request(self, name, email, job):
        clean_name = name.strip()
        clean_email = email.strip()
        clean_job = job.strip()
        if not clean_name or not clean_email or not clean_job:
            return False, "All fields are required."
        self.execute("INSERT INTO job_requests (name, email, job) VALUES (%s, %s, %s)", (clean_name, clean_email, clean_job))
        return True, "Job application submitted successfully."

    def delete_job_request(self, email):
        self.execute("DELETE FROM job_requests WHERE email = %s", (email.strip(),))


# Authoritative singleton database instance
db = Database()
