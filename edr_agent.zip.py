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
SERVER_PORT = 1236


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
        self.suspicious_files = []
        self.suspicious_files_to_send = []

        # קריאה לפונקציה הראשית
        self.main()

    def create_agent_id(self):
        # נתיב תיקיית ה-Agent
        #במחשב שלי
        BASE_DIR = r"C:\Users\TLV\Documents\agent"
        #במחשב הבית ספר
        #BASE_DIR = r"C:\Users\Pc2\Documents\agent"
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
                    agent_id_to_send = encryption.symmetric_encrypt_for_agent_server_message(self.my_fernet, self.agent_id)
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
                            count=0
                            while True:
                                print("in while true", count)

                                self.all_suspicious = []  # נקה
                                self.suspicious_files = []  # נקה – חשוב!
                                self.suspicious_files_to_send = []  # נקה

                                # סריקה מלאה של כל התיקיות
                                for path in SCAN_DIRS:
                                    if os.path.exists(path):
                                        self.scan_path(path)

                                print("after full scan – suspicious_files:", len(self.suspicious_files))

                                # עכשיו בדוק מה חדש
                                self.if_file_exist()

                                print("after if_file_exist – to send:", len(self.suspicious_files_to_send))

                                # שלח רק את החדשים
                                self.send_messages_files()

                                print("after send")
                                count += 1
                                time.sleep(10)

        except Exception as e:
            print("Connection failed:", e)

        time.sleep(5)  # השהייה לבדיקה, שלא ייסגר מיד
    # הפונקציה עוברת ברקורסיה על כל הקבצים הנמצאים בשולחן עבודה, מסמכים והורדות.
    #כל קובת נשלח לבדיקה כדי לחשב את רמת הסיכון שלו
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
            self.suspicious_files.append({
                "type": file_type,
                "file_name": file_name,
                "full_path": file_path,  # הוספנו נתיב מלא למניעת כפילות
                "risk_score": min(risk_score, 100),
                "reasons": reasons
            })

        self.if_file_exist()
        return self.suspicious_files_to_send

    def if_file_exist(self):
        #self.suspicious_files_to_send = []  # נקה כל פעם, כדי שלא יצטברו דברים ישנים

        for file_dict in self.suspicious_files:  # ← שינוי: file_dict הוא dict!
            full_path = file_dict['full_path']  # לוקחים את הנתיב מה-dict
            if full_path not in self.sent_files:  # בודקים אם לא נשלח כבר
                self.sent_files.add(full_path)  # מוסיפים ל-set
                self.suspicious_files_to_send.append(file_dict)  # ← מוסיף dict מלא!
                print(f"Added new suspicious file to send: {file_dict['file_name']}")

        print("suspicious_files_to_send-", self.suspicious_files_to_send)

    def send_messages_files(self):
        """
        שולחת לשרת את המידע על הקבצים החשודים.
        - יוצרת agent_id ייחודי אם לא קיים
        - נמנעת משליחת קבצים כפולים
        - מוסיפה תאריך ושעה
        """

        if not self.suspicious_files_to_send:
            print("No new suspicious files to send this cycle")

            message = "No new suspicious files to send this cycle"
            encrypted_message = encryption.symmetric_encrypt_for_agent_server_message(self.my_fernet, message)
            self.sock.send(encrypted_message)
            self.sock.recv(1024).decode()
            return

        print("suspicious_files:", self.suspicious_files)
        print("self.suspicious_files_to_send:", self.suspicious_files_to_send)

        for file in self.suspicious_files_to_send:
            #print("246")
            message = f"agent|{self.agent_id}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}|{file['type']}|{file['file_name']}|{file['full_path']}|{file['risk_score']}|{','.join(file['reasons'])}|in_progress"
            encrypted_message = encryption.symmetric_encrypt_for_agent_server_message(self.my_fernet, message)

            try:
                print("enc", encrypted_message)
                self.sock.send(encrypted_message)
                #print("254")
                try:
                    self.sock.settimeout(5)
                    #print("237")
                    data = self.sock.recv(1024).decode()
                    print("Server response:", data)
                except socket.timeout:
                    print("No response from server, continuing...")
            except Exception as e:
                print("Send failed:", e)

        # אחרי שליחה – ננקה את הרשימה, כדי שלא נשלח שוב באותו סיבוב
        self.suspicious_files_to_send = []


if __name__ == "__main__":
    Agent()
