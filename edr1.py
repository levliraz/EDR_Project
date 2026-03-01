import socket
import time
from datetime import datetime
import encryption
from cryptography.hazmat.primitives import serialization
import os
import mimetypes
import uuid
from getmac import get_mac_address

# כתובת השרת והפורט שלו
SERVER_IP = "127.0.0.1"
SERVER_PORT = 1237


class Agent:
    def __init__(self):
        self.all_suspicious = None
        """
        פונקציית האתחול יוצרת סוקט, מתחברת לשרת, מקבלת את המפתח הציבורי של השרת,
        שולחת סוג ה-Agent ומייצרת מפתח Fernet לשימוש בהצפנה סימטרית.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((SERVER_IP, SERVER_PORT))

        # קבלת המפתח הציבורי של השרת
        self.server_public_key_pem = self.sock.recv(2048)
        self.server_public_key = serialization.load_pem_public_key(self.server_public_key_pem)

        self.agent_id = None

        self.mac = get_mac_address()

        # שליחת סוג ה-Agent
        self.sock.send("Agent".encode())

        # יצירת מפתח Fernet להצפנה סימטרית
        self.my_encryption_fernet_key, self.my_fernet = encryption.encryption_agent_key(self.server_public_key)

        self.sent_files = set()# למנוע כפילויות

        # קריאה לפונקציה הראשית
        self.main()

    def create_agent_id(self):
        # נתיב תיקיית ה-Agent
        BASE_DIR = r"C:\Users\TLV\Documents\agent"
        FILES_DIR = os.path.join(BASE_DIR, "suspicious_files")
        agent_id_dir = os.path.join(BASE_DIR, "agent_id.txt")
        # קריאה או יצירה של agent_id
        agent_id = None
        if os.path.exists(agent_id_dir):
            agent_id = open(agent_id_dir, "r").read().strip()

        if not agent_id:
            agent_id = str(uuid.uuid4())
            with open(agent_id_dir, "w") as f:
                f.write(agent_id)

        print("AGENT ID:", agent_id)
        print(type(agent_id))

        print("BASE_DIR:", BASE_DIR)
        print("FILES_DIR:", FILES_DIR)
        print("Exists:", os.path.exists(FILES_DIR))

        return agent_id

    def main(self):
        """
        הפונקציה הראשית של ה-Agent:
        - מקבלת אישור מהשרת
        - שולחת את מפתח ההצפנה הסימטרי
        - סורקת תיקיות Desktop, Documents, Downloads
        - שולחת קבצים חשודים לשרת
        """
        try:
            if self.sock.recv(1024).decode() == "welcome agent!":
                # שליחת מפתח Fernet לשרת
                self.sock.send(self.my_encryption_fernet_key)

                if self.sock.recv(1024).decode().startswith("agent,your key"):

                    self.agent_id = self.create_agent_id()
                    agent_id_to_send = encryption.symmetric_encrypt_for_agent_server_message(self.my_fernet,self.agent_id)
                    self.sock.send(agent_id_to_send)
                    if self.sock.recv(1024).decode() == "Hi agent_id":
                        self.sock.send(self.mac.encode())
                        if self.sock.recv(1024).decode() == "i got your mac":

                            # נתיב תיקיית הבית של המשתמש
                            USER_HOME = os.path.expanduser("~")
                            print("USER_HOME:", USER_HOME)

                            # נתיבים של תיקיות נפוצות לסריקה
                            DESKTOP = os.path.join(USER_HOME, "Desktop")
                            DOCUMENTS = os.path.join(USER_HOME, "Documents")
                            DOWNLOADS = os.path.join(USER_HOME, "Downloads")

                            SCAN_DIRS = [DESKTOP, DOCUMENTS, DOWNLOADS]

                            # # נתיב תיקיית ה-Agent
                            # BASE_DIR = r"C:\Users\TLV\Documents\agent"
                            # FILES_DIR = os.path.join(BASE_DIR, "suspicious_files")
                            # agent_id_dir = os.path.join(BASE_DIR, "agent_id.txt")

                            while True:
                                # רשימה שתכיל את כל הקבצים החשודים
                                self.all_suspicious = []

                                # סריקה של כל תיקיות הסריקה
                                for path in SCAN_DIRS:
                                    if os.path.exists(path):
                                        self.scan_path(path)

                                #self.scan_path(BASE_DIR)

                                # שליחת המידע על הקבצים החשודים לשרת
                                self.send_messages_files(self.all_suspicious)

                                time.sleep(10)
                                #בסוף נשלח הודעה כדי שלא תהיה לולאה אינסופית
                                # encrypted_done = encryption.symmetric_encrypt_for_agent_server_message(self.my_fernet, "DONE")
                                # self.sock.sendall(encrypted_done)

                            #self.sock.close()

        except Exception as e:
            print("Connection failed:", e)

        time.sleep(5)  # השהייה לבדיקה, שלא ייסגר מיד


    def scan_path(self, path):
        try:
            if os.path.isfile(path):
                self.all_suspicious.extend(self.check_suspicious_file(path))

            elif os.path.isdir(path):
                for item in os.listdir(path):
                    full_path = os.path.join(path, item)
                    self.scan_path(full_path)

        except PermissionError:
            # אין הרשאה – מדלגים
            return


    def check_suspicious_file(self, file_path):
        file_name = os.path.basename(file_path)

        suspicious_files = []

        suspicious_extensions = [".js", ".bat"]

        #תוכנות זדוניות אוהבות לקרוא לעצמן svchost.exe או משהו דומה כדי להסתתר ולרמות את המשתמשים או את התוכנות שמנטרות קבצים.
        #, אם קובץ נקרא svchost.bat.docx או svchost.exe מקומי אבל לא בתיקיית מערכת, זה מעלה דגל אדום.
        #תוכנות זדוניות משתמשות בשמות כאלה כדי שכשמשתמש רואה את הקובץ, הוא יחשוב שזה חוקי ולא ימחוק אותו.
        # דוגמה: windows_security.cmd.txt – קובץ טקסט או סקריפט שמתחזה ל־Windows Security.
        # קיצור של Key Generator, כלומר כלי שמייצר מפתחות תוכנה פיראטיים.
        # בדרך כלל כלי פיראטיים כאלה מגיעים עם תוכנות זדוניות – בעיקר וירוסים או טרויאנים שמתחזים ל־Keygen.
        # לכן, כל קובץ עם keygen בשם שלו מוגדר כמסוכן אוטומטית.

        fake_system_names = ["svchost", "windows_security", "keygen"]
        known_extension = {
            "exe", "js", "bat", "cmd", "scr",
            "pdf", "doc", "docx", "txt",
            "jpg", "png", "zip", "rar"
        }

        risk_score = 0
        reasons = []

        name_lower = file_name.lower()

        # ניחוש סוג הקובץ לפי MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if mime_type.startswith("text"):
                file_type = "text_file"
            elif "zip" in mime_type or "compressed" in mime_type:
                file_type = "compressed_file"
            else:
                file_type = mime_type
        else:
            file_type = "unknown_file"

        # if extension == ".exe":
        #     risk_score += 5

        if any(name_lower.endswith(ext) for ext in suspicious_extensions):
            risk_score += 20
            reasons.append("Suspicious extension")

        if name_lower.count(".") >= 2:
            new_name_list = name_lower.split('.')
            end1 = new_name_list[-1]
            end2 = new_name_list[-2]
            if end1 in known_extension and end2 in known_extension:
                risk_score += 40
                reasons.append("Double file extension")

        if any(fake in name_lower for fake in fake_system_names):
            risk_score += 30
            reasons.append("Impersonating system file")

        # אם הקובץ חשוד, מוסיפים לרשימה
        if risk_score > 0:
            suspicious_files.append({
                "type": file_type,
                "file_name": file_name,
                "full_path": file_path,  # הוספנו נתיב מלא למניעת כפילות
                "risk_score": min(risk_score, 100),
                "reasons": reasons
            })

        return suspicious_files


    def send_messages_files(self, suspicious_files):
        """
        שולחת לשרת את המידע על הקבצים החשודים.
        - יוצרת agent_id ייחודי אם לא קיים
        - נמנעת משליחת קבצים כפולים
        - מוסיפה תאריך ושעה
        """

        #self.sent_files = set()  # למנוע כפילויות

        for file in suspicious_files:
            if file['full_path'] in self.sent_files:
                continue
            self.sent_files.add(file['full_path'])

            message = f"agent|{self.agent_id}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}|{file['type']}|{file['file_name']}|null|null|{file['risk_score']}|{','.join(file['reasons'])}|in_progress"
            encrypted_message = encryption.symmetric_encrypt_for_agent_server_message(self.my_fernet, message)

            try:
                self.sock.send(encrypted_message)
                try:
                    self.sock.settimeout(5)
                    data = self.sock.recv(1024).decode()
                    print("Server response:", data)
                except socket.timeout:
                    print("No response from server, continuing...")
            except Exception as e:
                print("Send failed:", e)

if __name__ == "__main__":
    Agent()
