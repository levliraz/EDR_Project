import socket
from threading import Thread, Lock
import users_data_base
from cryptography.hazmat.primitives.asymmetric import rsa
import encryption
import sqlite3

lock = Lock()

class Server:
    def __init__(self):
        self.listening_socket = socket.socket()
        self.listening_socket.bind(("0.0.0.0", 1236))
        self.listening_socket.listen(5)
        self.msg = ""
        self.connect_users = []

        self.agent_dic = {}
        self.user_dic = {}
        self.mac_agent_user_dic = {}

        users_data_base.create_data_base()
        # --- בצד השרת: יצירת זוג מפתחות ---
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()
        self.decrypted_fernet_agent_key = None

        #set הוא קולקשן של ערכים ייחודיים ב־Python.
        #לא מאפשר כפילויות – אם תנסה להוסיף את אותו ערך פעמיים, הוא יישאר רק פעם אחת.
        #מאפשר בדיקה מהירה אם משהו קיים (value in my_set), הרבה יותר מהירה מ־list.
        #אין סדר– אין אינדקסים, זה לא רשימה, רק אוסף של ערכים ייחודיים.

        self.already_alerted_files = set()
        self.agent_id = None
        self.user_id = None
        self.mac_agent = None
        self.mac_user = None

        # הפונקציה מקבלת לקוחות ומוסיפה אותם לשרת
    def start(self):
        print("Server is listening on port 1236...")
        while True:
            client_socket, client_address = self.listening_socket.accept()

            client = Thread(target=self.handle_client, args=(client_socket, client_address), daemon=True)
            client.start()


    def handle_client(self, client_socket, client_address):
        # נשלח את המפתח הציבורי של השרת ללקוח לאחר "שהכנו" את המפתח הציבורי של השרת
        # שליחת המפתח הציבורי בלבד
        pem_public = encryption.server_asymmetric_encryption(self.public_key)
        client_socket.sendall(pem_public)

        list_data = None

        try:
            client_status = client_socket.recv(1024).decode()

            if client_status == "Agent":
                client_socket.send("welcome agent!".encode())

                # נקבל את המפתח המוצפן של הagent
                encrypted_agent_key = client_socket.recv(2048)
                self.decrypted_fernet_agent_key = encryption.decryption_agent_key(self.private_key, encrypted_agent_key)

                client_socket.send("agent,your key has arrived".encode())

                decrypt_agent_id = client_socket.recv(1024)
                self.agent_id = encryption.symmetric_decrypt_for_agent_server_message(self.decrypted_fernet_agent_key,
                                  decrypt_agent_id)
                client_socket.send("Hi agent_id".encode())

                self.mac_agent = client_socket.recv(1024).decode('utf-8').strip()  # קוראים את ה-MAC ששלח הסוכן וממירים ל-string
                client_socket.send("i got your mac".encode())  # מאשרים לסוכן שקיבלנו

                # כאן כבר יש לנו agent_id + mac → שומרים מיד!
                with lock:  # נועלים כדי ששני ת'רדים לא יתנגשו בו זמנית
                    mac = self.mac_agent.strip()  # מנקים רווחים מיותרים מסביב ל-MAC
                    if mac not in self.mac_agent_user_dic:  # אם ה-MAC הזה עדיין לא קיים במילון
                        self.mac_agent_user_dic[mac] = {  # יוצרים רשומה חדשה
                            "agent_id": self.agent_id,  # שומרים את ה-agent_id שזה עתה קיבלנו
                            "users": []  # רשימת משתמשים ריקה בהתחלה
                        }
                    elif self.mac_agent_user_dic[mac]["agent_id"] != self.agent_id:
                        # אם כבר יש MAC כזה אבל עם agent_id אחר – זה באג/תקלה
                        print(f"WARNING: אותו MAC עם agent_id שונה! {mac}")

                # הוספתי למילון מפתח שהוא הuser_id והערך שלו הוא הסוקט של הלקוח המחובר כרגע
                self.agent_dic[self.agent_id] = client_socket
                print("agents", self.agent_dic)


            elif client_status == "GUI":
                client_socket.send("welcome client!".encode())
                decrypt_user_id = client_socket.recv(1024)
                self.user_id = encryption.decryption_data(self.private_key, decrypt_user_id).decode()
                client_socket.send("Hi user_id".encode())

                self.mac_user = client_socket.recv(1024).decode('utf-8').strip()
                client_socket.send("i got your mac".encode())

                # הוספתי למילון מפתח שהוא הuser_id והערך שלו הוא הסוקט של הלקוח המחובר כרגע
                self.user_dic[self.user_id] = client_socket
                print("users", self.user_dic)

                self.stam()


            while True:
                if client_status == "Agent":
                    encrypted_data = client_socket.recv(1024)
                    data = encryption.symmetric_decrypt_for_agent_server_message(self.decrypted_fernet_agent_key, encrypted_data)
                    if not data:
                        print("Agent disconnected")
                        return
                        # שובר את הלולאה ולא סוגר את הסוקט כאן, נעשה בסוף
                    if data.startswith("No new suspicious"):
                        client_socket.send("ok".encode())
                        continue

                    list_data = data.split('|')

                elif client_status == "GUI":
                    data = client_socket.recv(2048)
                    print("data", data)
                    if not data:
                        print("Client disconnected")
                        return

                    decrypted_bytes = encryption.decryption_data(self.private_key, data)

                    try:
                        list_data = decrypted_bytes.decode("utf-8").split('|')
                    except UnicodeDecodeError:
                        print("Cannot decode decrypted_bytes:", decrypted_bytes)
                        return

                print("list_data", list_data)

                command = list_data[0]

                if not client_socket:
                    self.connect_users.remove(list_data)

                if command == "agent":
                    #f"agent|{self.agent_id}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}|{file['type']}|{file['file_name']}|{file['full_path']}|{file['risk_score']}|{','.join(file['reasons'])}|in_progress"
                    file_name = list_data[4]

                    if (self.agent_id, file_name) not in self.already_alerted_files:
                        self.msg = users_data_base.handle_alerts(list_data)
                        self.already_alerted_files.add((self.agent_id, file_name))
                    else:
                        self.msg = f"File {file_name} already reported for this agent."

                elif command == "client":
                    #print("client")
                    user_id = list_data[4]
                    client_socket.send("hi client".encode())
                    if client_status == "GUI":
                        if client_socket.recv(1024).decode().startswith("show me the"):
                            self.handel_alerts_data(user_id)

                elif command == "login":
                    #print("login")
                    self.msg = users_data_base.handle_login(list_data, self.connect_users)

                    if client_socket and self.msg.startswith("Welcome"):
                        # אחרי התחברות מוצלחת
                        self.user_id = list_data[4]  # ה-UUID של המשתמש
                        if self.user_id not in self.connect_users:
                            self.connect_users.append(self.user_id)

                    print("connect_users", self.connect_users)

                elif command == "register":
                    #print("register")
                    self.msg = users_data_base.handle_register(list_data)

                else:
                    self.msg = f"Unknown command: {command}"

                # שליחת ההודעה חזרה ללקוח
                print(self.msg)
                client_socket.send(self.msg.encode())


        except Exception as e:
            print(f"Error: {e}")
        finally:
            if list_data is not None:
                self.user_id = list_data[4]
                if self.user_id in self.connect_users:
                    self.connect_users.remove(self.user_id)
            print(f"Connection with {client_address} closed")

    def stam(self):
        # לוקחים את ה-MAC של ה-GUI (שנשלח מהלקוח) ומנקים
        mac = self.mac_user.decode('utf-8').strip() if isinstance(self.mac_user, bytes) else self.mac_user.strip()

        with lock:  # נעילה כדי למנוע בעיות אם כמה GUI מתחברים בו זמנית
            if mac in self.mac_agent_user_dic:  # אם כבר יש רשומה למכונה הזו (כלומר הסוכן כבר התחבר)
                if self.user_id not in self.mac_agent_user_dic[mac]["users"]:
                    # אם המשתמש הזה עדיין לא ברשימה – מוסיפים אותו
                    self.mac_agent_user_dic[mac]["users"].append(self.user_id)
                    print(f"הוספתי user {self.user_id} למכונה {mac}")
            else:
                # אם אין עדיין סוכן על המכונה הזו
                print(f"אזהרה: GUI התחבר ממכונה {mac} אבל אין עדיין סוכן רשום על ה-MAC הזה!")
                # כאן אפשר להוסיף התנהגות: לשלוח הודעה ללקוח "אין סוכן פעיל" וכו'

        print("self.mac_agent_user_dic →", self.mac_agent_user_dic)
        print("self.mac_agent_user_dic", self.mac_agent_user_dic)


    def handel_alerts_data(self, user_id):
        client_socket = self.user_dic[user_id]
        print("client_socket", client_socket)

        # מחפשים איזה MAC מכיל את המשתמש הזה
        agent_id = None
        for mac, mac_entry in self.mac_agent_user_dic.items():
            if user_id in mac_entry["users"]:
                agent_id = mac_entry["agent_id"]
                print(f"User {user_id} belongs to agent {agent_id} on MAC {mac}")
                break

        if not agent_id:
            print(f"No agent found for user {user_id}!")
            return

        # מתחברים למסד הנתונים
        conn = sqlite3.connect("users.db")
        c = conn.cursor()

        # שולפים רק את השורות ששייכות לסוכן הזה
        # c.execute("SELECT * FROM alerts WHERE agent_id = ?", (agent_id,))
        # row = c.fetchone()

        c.execute("""
            SELECT * FROM alerts 
            WHERE agent_id = ? 
            ORDER BY id ASC
        """, (agent_id,))

        rows = c.fetchall()

        for row in rows:
            row_list = list(row)
            result = "|".join(map(str, row_list))
            client_socket.send(result.encode())

            if client_socket.recv(1024).decode() == "send more":
                row = c.fetchone()
            else:
                break

        conn.close()
        client_socket.send("END".encode())


if __name__ == "__main__":
    server = Server()
    server.start()


#liraz|liraz@gmail.com|Liraz@28