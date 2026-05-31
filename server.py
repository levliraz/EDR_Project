import socket
from threading import Thread, Lock
import data_base
from cryptography.hazmat.primitives.asymmetric import rsa
import encryption

lock = Lock()

class Server:
    def __init__(self):
        self.listening_socket = socket.socket()
        self.listening_socket.bind(("0.0.0.0", 1237))
        self.listening_socket.listen(5)
        self.msg = ""
        self.logged_in_users = {}  # email : socket

        #שמירת last_id לכל משתמש
        # לכל משתמש נשמר ה־ID האחרון שנשלח אליו
        self.last_sent_alert_id = {}

        self.agent_dic = {}
        self.user_dic = {}
        self.mac_agent_user_dic = {}

        data_base.create_data_base()

        #בצד השרת: יצירת זוג מפתחות
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
                self.agent_id = encryption.symmetric_decrypt_for_agent_server_message(self.decrypted_fernet_agent_key,  decrypt_agent_id)

                client_socket.send("Hi agent_id".encode())

                #strip() היא פונקציה שמסירה רווחים ותווי ירידת שורה (\n, \r, \t) מתחילת וסוף המחרוזת.
                self.mac_agent = client_socket.recv(1024).decode('utf-8').strip()  # קוראים את ה-MAC ששלח הסוכן וממירים ל-string
                client_socket.send("i got your mac".encode())  # מאשרים לסוכן שקיבלנו


                #מונע מצב ששני threads יעדכנו את אותו MAC בו זמנית
                # חשוב כי כמה Agents יכולים להתחבר במקביל
                with lock:
                    mac = self.mac_agent
                    # אם ה-MAC לא קיים עדיין
                    if mac not in self.mac_agent_user_dic:

                        self.mac_agent_user_dic[mac] = {
                            "agent_id": self.agent_id,
                            "users": []
                        }
                    else:
                        # אם כבר יש MAC כזה
                        # רק מעדכנים את ה-agent_id
                        self.mac_agent_user_dic[mac]["agent_id"] = self.agent_id

                    print("UPDATED mac_agent_user_dic:", self.mac_agent_user_dic)


                # הוספתי למילון מפתח שהוא הuser_id והערך שלו הוא הסוקט של הלקוח המחובר כרגע
                # שמירת socket לפי agent_id
                self.agent_dic[self.agent_id] = client_socket
                print("agents", self.agent_dic)

            elif client_status == "GUI":
                client_socket.send("welcome client!".encode())
                decrypt_user_id = client_socket.recv(1024)
                self.user_id = encryption.decryption_data_in_server(self.private_key, decrypt_user_id).decode()
                client_socket.send("Hi user_id".encode())

                self.mac_user = client_socket.recv(1024).decode('utf-8').strip()
                client_socket.send("i got your mac".encode())

                print("users", self.user_dic)

                self.link_user_to_agent_session()


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

                    decrypted_bytes = encryption.decryption_data_in_server(self.private_key, data)

                    try:
                        #המרה מטיפוס bytes לטיפוס utf-8 - str
                        list_data = decrypted_bytes.decode("utf-8").split('|')
                    except UnicodeDecodeError:
                        print("Cannot decode decrypted_bytes:", decrypted_bytes)
                        return

                print("list_data", list_data)

                command = list_data[0]

                if command == "agent":
                    #f"agent|{self.agent_id}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}|{file['type']}|{file['file_name']}|{file['full_path']}|{file['risk_score']}|{','.join(file['reasons'])}|in_progress"
                    file_name = list_data[4]

                    if (self.agent_id, file_name) not in self.already_alerted_files:
                        self.msg = data_base.handle_alerts(list_data)
                        self.already_alerted_files.add((self.agent_id, file_name))


                    else:
                        self.msg = f"File {file_name} already reported for this agent."


                elif command == "login":
                    email = list_data[2]
                    #  מונע מצב ששני login של אותו user קורים במקביל
                    # חשוב כדי למנוע כפילות התחברות
                    with lock:

                        if email in self.logged_in_users:
                            self.msg = "You are already login on the site"

                        else:
                            self.msg = data_base.handle_login(list_data)

                            if self.msg.startswith("Welcome"):
                                self.logged_in_users[email] = client_socket

                elif command == "register":
                    self.msg = data_base.handle_register(list_data)

                elif command == "get_alerts":
                    user_id = list_data[4]
                    # שליפה ממסד הנתונים
                    alerts = self.get_alerts_for_user(user_id)

                    print("alerts:", alerts)

                    if not alerts:
                        client_socket.send("NO_ALERTS".encode())
                        continue

                    rows_as_strings = ["|".join(row) for row in alerts]
                    print("rows_as_strings:",rows_as_strings)
                    self.msg = "||".join(rows_as_strings)

                elif command == "delete_alert":
                    id_alert = list_data[1]
                    agent_id = list_data[2]
                    file_name = list_data[3]

                    #משתמשים בdiscard כי אם הקובץ כבר לא נמצא ב־set,לא תהיה שגיאה והשרת לא יתקע
                    # שימוש ב-discard כדי למנוע קריסה אם הערך לא קיים
                    self.already_alerted_files.discard((agent_id, file_name))

                    #קוראים לפעולה שמוחקת שורה ממסד הנתונים
                    self.msg = data_base.delete_row_from_data_base(id_alert)

                else:
                    self.msg = f"Unknown command: {command}"

                # שליחת ההודעה חזרה ללקוח
                print("msg", self.msg)
                client_socket.send(self.msg.encode())


        except Exception as e:
            print(f"Error: {e}")
        finally:
            try:
                # ניקוי חיבור כשהלקוח מתנתק
                if list_data and len(list_data) > 4:
                    self.user_id = list_data[4]

                    if list_data and len(list_data) > 2:
                        email = list_data[2]

                        # הסרת משתמש מחובר בצורה בטוחה
                        # משתמשים בpop ולא בdelete כדי שאם הערך לא קיים במילון, זה לא יקרוס
                        self.logged_in_users.pop(email, None)

                        # ניקוי התראות אחרונות של המשתמש
                        if self.user_id in self.last_sent_alert_id:
                            del self.last_sent_alert_id[self.user_id]

            except Exception as e:
                print("finally error:", e)

            print(f"Connection with {client_address} closed")

    def link_user_to_agent_session(self):
        # ניקוי רווחים מה-MAC
        mac = self.mac_user

        # מונע מצב שבו כמה משתמשים נרשמים לאותו MAC במקביל
        with lock:
            # אם ה-MAC עדיין לא קיים במילון
            if mac not in self.mac_agent_user_dic:
                # יוצרים רשומה חדשה
                self.mac_agent_user_dic[mac] = {
                    "agent_id": None,
                    "users": []
                }

            # אם המשתמש עדיין לא קיים ברשימה
            if self.user_id not in self.mac_agent_user_dic[mac]["users"]:
                # מוסיפים אותו
                self.mac_agent_user_dic[mac]["users"].append(self.user_id)

                print(f"Added user {self.user_id} to MAC {mac}")

        print("self.mac_agent_user_dic →", self.mac_agent_user_dic)

    def get_alerts_for_user(self, user_id):
        agent_id = None

        for mac, data in self.mac_agent_user_dic.items():
            if user_id in data["users"]:
                agent_id = data["agent_id"]
                break

        if not agent_id:
            return []

        # ה-ID האחרון שכבר נשלח למשתמש
        last_id = self.last_sent_alert_id.get(user_id, 0)

        # שליפת רק התרעות חדשות
        alerts = data_base.get_alerts_by_agent(agent_id, last_id)
        print("alerts1:", alerts)

        result = []

        for alert in alerts:
            row = [
                str(alert[0]),  # id
                str(alert[1]),  #agent_id
                str(alert[2]),  # time
                str(alert[3]),  # type
                str(alert[4]),  # file name
                str(alert[5]),  # path
                str(alert[6]),  # risk
                str(alert[7]),  # reason
                str(alert[8])  # status
            ]

            result.append(row)

        # עדכון ה-ID האחרון שנשלח
        if alerts:
            last_alert_id = alerts[-1][0]

            self.last_sent_alert_id[user_id] = last_alert_id

        print("result:", result)

        return result


if __name__ == "__main__":
    server = Server()
    server.start()

