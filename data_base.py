import sqlite3
from pathlib import Path
from threading import Lock
import encryption
import bcrypt
import base64

lock = Lock()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "users.db"


def create_data_base():
    # connect() # – מתחבר לקובץ DB (אם לא קיים – יוצר).
    conn = sqlite3.connect(DB_PATH)
    # cursor() # – מאפשר לבצע פקודות SQL.
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users
        (email TEXT PRIMARY KEY, password TEXT, full_name TEXT)
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS files_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            timestamp TEXT,
            file_type TEXT,
            file_name TEXT NOT NULL,
            full_path TEXT NOT NULL,
            risk_score INTEGER,
            reasons TEXT,
            status TEXT,
            UNIQUE(agent_id, file_name) 
        )
    """)
    # UNIQUE - השילוב של agent_id + file_name חייב להיות ייחודי בכל הטבלה

    c.execute("""
        CREATE TABLE IF NOT EXISTS process_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            timestamp TEXT,
            process_name TEXT,
            pid TEXT NOT NULL,
            exe_path TEXT NOT NULL,
            risk_score INTEGER,
            reasons TEXT,
            status TEXT,
            UNIQUE(agent_id, process_name, exe_path)
        )
    """)

    conn.commit()#שמירת השינויים
    conn.close()

#type -- email / file / process, from_email,subject,link-רלוונטי רק למיילים
#file_name- רלוונטי רק לקבצים, process_name- רלוונטי רק לתהליכים, pid- PID רלוונטי רק לתהליכים

#id-מזהה ייחודי לכל התרעה, agent_id-שם ה-Agent/מחשב ששלח את ההתרעה, timestamp-זמן בו נוצרה ההתרעה
#from_email-מי שלח את המייל החשוד, subject-נושא המייל, link-לינק חשוד במייל (אם יש)
#risk_score-ציון סיכון (0–100), status-מצב ההתרעה: חדש / טופל / מתעלם


def handle_login(list_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    email = list_data[2]
    password_from_client = list_data[3]  # טקסט רגיל
    user_id = list_data[4]
    print(password_from_client)

    c.execute("SELECT password FROM users WHERE email = ?", (email,))
    row = c.fetchone()

    if row is None:
        return "You are not registered on the site."

    stored_hash_b64 = row[0]  # מחזירים ל-bytes, חילוץ הסיסמה מה־DB
    print(stored_hash_b64)

    stored_hash_bytes = base64.b64decode(stored_hash_b64)

    conn.close()
    if bcrypt.checkpw(password_from_client.encode("utf-8"), stored_hash_bytes):
        return f"Welcome user:{list_data[1]}"
    else:
        return "Wrong password"


def handle_register(list_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    full_name = list_data[1]
    email = list_data[2]
    password = list_data[3]
    print(password)
    hashed_password = encryption.encryption_password(password)
    print(hashed_password)

    c.execute("SELECT full_name FROM users WHERE email = ?", (email,))
    row = c.fetchone()

    if row is not None:
        return "You are already registered on the site,log in"

    #with lock: מבטיח שרק Thread אחד ירשום משתמש בזמן אמת.
    with lock:
        c.execute(
            "INSERT INTO users (email, password, full_name) VALUES (?, ?, ?)",
            (email, hashed_password, full_name)
        )
        conn.commit()

    conn.close()
    return "Registration to the site was successful!,log in"


def handle_files_alerts(list_data):
    #f"agent|{self.agent_id}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}|{file['type']}|{file['file_name']}|{file['full_path']}|{file['risk_score']}|{','.join(file['reasons'])}|in_progress"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ננקה רווחים
    list_data = [x.strip() for x in list_data]

    agent_id = list_data[1]
    timestamp = list_data[2]
    file_type = list_data[3]
    file_name = list_data[4]
    full_path = list_data[5]
    risk_score = int(list_data[6])
    reasons = list_data[7]
    status = list_data[8]

    print("Inserting alert:", agent_id, timestamp, file_type, file_name, full_path, risk_score, reasons,
          status)

    try:
        c.execute(
            "INSERT INTO files_alerts (agent_id, timestamp, file_type, file_name, full_path, risk_score, reasons, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (agent_id, timestamp, file_type, file_name, full_path, risk_score, reasons, status)
        )
        conn.commit()
        return f"Warning! A suspicious file named {file_name} was found on your computer."

    except sqlite3.IntegrityError:
        # כפילות – UNIQUE הפר
        print(f"Duplicate alert ignored: {agent_id} - {file_name}")
        return f"File {file_name} already reported for this agent."

    finally:
        conn.close()


def handle_process_alerts(list_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ננקה רווחים
    list_data = [x.strip() for x in list_data]

    #"process|{agent_id}|{time}|{process_name}|{pid}|{exe_path}|{risk_score}|{reasons}|in_progress"
    agent_id = list_data[1]
    timestamp = list_data[2]
    process_name = list_data[3]
    pid = list_data[4]
    exe_path = list_data[5]
    risk_score = int(list_data[6])
    reasons = list_data[7]
    status = list_data[8]

    print("Inserting alert:", agent_id, timestamp, process_name, pid, exe_path, risk_score, reasons,
          status)

    try:
        c.execute(
            "INSERT INTO process_alerts (agent_id, timestamp, process_name, pid, exe_path, risk_score, reasons, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (agent_id, timestamp, process_name, pid, exe_path, risk_score, reasons, status)
        )
        conn.commit()
        return f"Warning! A suspicious process named {process_name} was found on your computer."

    except sqlite3.IntegrityError:
        # כפילות – UNIQUE הפר
        print(f"Duplicate alert ignored: {agent_id} - {process_name}")
        return f"Process {process_name} already reported for this agent."

    finally:
        conn.close()


def get_alerts_about_files(agent_id, last_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
        SELECT id, agent_id, timestamp, file_type, file_name, full_path, risk_score, reasons, status
        FROM files_alerts
        WHERE agent_id = ? AND id > ?
        ORDER BY id ASC
    """

    cursor.execute(query, (agent_id, last_id))
    rows = cursor.fetchall()
    conn.close()

    print("rows_in files_alerts:", rows)

    return rows


def get_alerts_about_process(agent_id, last_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = """
            SELECT id, agent_id, timestamp, process_name, pid, exe_path, risk_score, reasons, status
            FROM process_alerts
            WHERE agent_id = ? AND id > ?
            ORDER BY id ASC
        """

    cursor.execute(query, (agent_id, last_id))
    rows = cursor.fetchall()
    conn.close()

    print("rows_in process_alerts:", rows)

    return rows

#הפעולה מוחקת שורה ממסד הנתונים לפי מספר השורה(ID)
def delete_row_from_data_base(alert_id):

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    alert_id = int(alert_id)

    c.execute(
        "DELETE FROM files_alerts WHERE id = ?",
        (alert_id,)
    )

    conn.commit()
    conn.close()

    print("Deleted alert:", alert_id)

    return "The file deleted successfully"