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

        # שמירת last_id לכל משתמש
        # לכל משתמש נשמר ה־ID האחרון שנשלח אליו
        self.last_sent_alert_id_files = {}

        self.last_sent_alert_id_process = {}

        self.agent_dic = {}
        # self.user_dic = {}
        self.mac_agent_user_dic = {}
        # self.already_alerted_files = set()

        data_base.create_data_base()

        # בצד השרת: יצירת זוג מפתחות
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.public_key = self.private_key.public_key()

        # set הוא קולקשן של ערכים ייחודיים ב־Python.
        # לא מאפשר כפילויות – אם תנסה להוסיף את אותו ערך פעמיים, הוא יישאר רק פעם אחת.
        # מאפשר בדיקה מהירה אם משהו קיים (value in my_set), הרבה יותר מהירה מ־list.
        # אין סדר– אין אינדקסים, זה לא רשימה, רק אוסף של ערכים ייחודיים.

        # הפונקציה מקבלת לקוחות ומוסיפה אותם לשרת

    def start(self):
        print("Server is listening on port 1236...")
        while True:
            client_socket, client_address = self.listening_socket.accept()

            client = Thread(target=self.handle_client, args=(client_socket, client_address), daemon=True)
            client.start()

    def handle_client(self, client_socket, client_address):
        list_data = None
        user_id = None
        email = None
        decrypted_fernet_agent_key = None

        # נשלח את המפתח הציבורי של השרת ללקוח לאחר "שהכנו" את המפתח הציבורי של השרת
        # שליחת המפתח הציבורי בלבד
        pem_public = encryption.server_asymmetric_encryption(self.public_key)
        client_socket.sendall(pem_public)

        try:
            client_status = client_socket.recv(1024).decode()

            if client_status == "Agent":
                client_socket.send("welcome agent!".encode())

                # נקבל את המפתח המוצפן של הagent
                encrypted_agent_key = client_socket.recv(2048)
                decrypted_fernet_agent_key = encryption.decryption_agent_key(self.private_key, encrypted_agent_key)

                client_socket.send("agent,your key has arrived".encode())

                decrypt_agent_id = client_socket.recv(1024)
                agent_id = encryption.symmetric_decrypt_for_agent_server_message(decrypted_fernet_agent_key,
                                                                                 decrypt_agent_id)

                client_socket.send("Hi agent_id".encode())

                # strip() היא פונקציה שמסירה רווחים ותווי ירידת שורה (\n, \r, \t) מתחילת וסוף המחרוזת.
                mac_agent = client_socket.recv(1024).decode(
                    'utf-8').strip()  # קוראים את ה-MAC ששלח הסוכן וממירים ל-string

                client_socket.send("i got your mac".encode())  # מאשרים לסוכן שקיבלנו

                # מונע מצב ששני threads יעדכנו את אותו MAC בו זמנית
                # חשוב כי כמה Agents יכולים להתחבר במקביל
                with lock:

                    mac = mac_agent

                    # אם ה-MAC לא קיים עדיין
                    if mac not in self.mac_agent_user_dic:

                        self.mac_agent_user_dic[mac] = {
                            "agent_id": agent_id,
                            "users": []
                        }
                    else:
                        # אם כבר יש MAC כזה
                        # רק מעדכנים את ה-agent_id
                        self.mac_agent_user_dic[mac]["agent_id"] = agent_id

                    print("UPDATED mac_agent_user_dic:", self.mac_agent_user_dic)

                # הוספתי למילון מפתח שהוא הuser_id והערך שלו הוא הסוקט של הלקוח המחובר כרגע
                # שמירת socket לפי agent_id
                self.agent_dic[agent_id] = client_socket

                print("agents", self.agent_dic)

            elif client_status == "GUI":
                client_socket.send("welcome client!".encode())
                decrypt_user_id = client_socket.recv(1024)
                user_id = encryption.decryption_data_in_server(self.private_key, decrypt_user_id).decode()
                print(f"GUI connected with user_id = {user_id}")
                client_socket.send("Hi user_id".encode())

                mac_user = client_socket.recv(1024).decode('utf-8').strip()
                client_socket.send("i got your mac".encode())

                self.link_user_to_agent_session(user_id, mac_user)
                # self.link_user_to_agent_session(client_socket, mac_user)

            while True:
                if client_status == "Agent":
                    encrypted_data = client_socket.recv(1024)
                    data = encryption.symmetric_decrypt_for_agent_server_message(decrypted_fernet_agent_key,
                                                                                 encrypted_data)
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
                        if email:
                            self.logged_in_users.pop(email, None)

                        if user_id and user_id in self.last_sent_alert_id_files:
                            del self.last_sent_alert_id_files[user_id]

                        if user_id and user_id in self.last_sent_alert_id_process:
                            del self.last_sent_alert_id_process[user_id]
                        return

                    decrypted_bytes = encryption.decryption_data_in_server(self.private_key, data)

                    try:
                        # המרה מטיפוס bytes לטיפוס utf-8 - str
                        list_data = decrypted_bytes.decode("utf-8").split('|')
                    except UnicodeDecodeError:
                        print("Cannot decode decrypted_bytes:", decrypted_bytes)
                        return

                print("list_data", list_data)

                command = list_data[0]

                if command == "file":
                    # f"file|{self.agent_id}|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}|{file['type']}|{file['file_name']}|{file['full_path']}|{file['risk_score']}|{','.join(file['reasons'])}|in_progress"
                    agent_id = list_data[1]
                    file_name = list_data[4]

                    # if (agent_id, file_name) not in self.already_alerted_files:
                    #     self.msg = data_base.handle_files_alerts(list_data)
                    #     self.already_alerted_files.add((agent_id, file_name))
                    self.msg = data_base.handle_files_alerts(list_data)
                    # else:
                    # self.msg = f"File {file_name} already reported for this agent."


                elif command == "process":
                    self.msg = data_base.handle_process_alerts(list_data)


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

                elif command == "get_files_alerts":
                    user_id = list_data[4]
                    print(f"get_alerts requested by user_id = {user_id}")
                    # שליפה ממסד הנתונים
                    alerts = self.get_alerts_for_user(user_id, command)

                    print("alerts:", alerts)

                    if not alerts:
                        client_socket.send("NO_ALERTS".encode())
                        continue

                    rows_as_strings = ["|".join(row) for row in alerts]
                    print("rows_as_strings:", rows_as_strings)
                    self.msg = "||".join(rows_as_strings)

                elif command == "get_process_alerts":
                    user_id = list_data[4]
                    print(f"get_alerts requested by user_id = {user_id}")
                    # שליפה ממסד הנתונים
                    alerts = self.get_alerts_for_user(user_id, command)

                    print("alerts:", alerts)

                    if not alerts:
                        client_socket.send("NO_ALERTS".encode())
                        continue

                    rows_as_strings = ["|".join(row) for row in alerts]
                    print("rows_as_strings:", rows_as_strings)
                    self.msg = "||".join(rows_as_strings)


                elif command == "delete_alert":
                    id_alert = list_data[1]
                    # משתמשים בdiscard כי אם הקובץ כבר לא נמצא ב־set,לא תהיה שגיאה והשרת לא יתקע
                    # שימוש ב-discard כדי למנוע קריסה אם הערך לא קיים
                    # self.already_alerted_files.discard((agent_id, file_name))

                    # קוראים לפעולה שמוחקת שורה ממסד הנתונים
                    self.msg = data_base.delete_row_from_data_base(id_alert)

                elif command == "delete_process_alert":
                    id_alert = list_data[1]
                    self.msg = data_base.delete_row_from_process_data_base(id_alert)

                else:
                    self.msg = f"Unknown command: {command}"

                # שליחת ההודעה חזרה ללקוח
                print("msg", self.msg)
                client_socket.send(self.msg.encode())


        except Exception as e:
            print(f"Error: {e}")
        finally:
            try:

                if email:
                    self.logged_in_users.pop(email, None)

                if user_id and user_id in self.last_sent_alert_id_files:
                    del self.last_sent_alert_id_files[user_id]

                if user_id and user_id in self.last_sent_alert_id_process:
                    del self.last_sent_alert_id_process[user_id]


            except Exception as e:
                print("finally error:", e)

            print(f"Connection with {client_address} closed")

    def link_user_to_agent_session(self, user_id, mac_user):
        # ניקוי רווחים מה-MAC
        mac = mac_user

        # מונע מצב שבו כמה משתמשים נרשמים לאותו MAC במקביל
        with lock:
            # אם ה-MAC עדיין לא קיים במילון
            if mac not in self.mac_agent_user_dic:
                # יוצרים רשומה חדשה
                self.mac_agent_user_dic[mac] = {
                    "agent_id": None,
                    "users": []
                }

            # if client_socket not in self.mac_agent_user_dic[mac]["users"]:
            #     # מוסיפים אותו
            #     self.mac_agent_user_dic[mac]["users"].append(client_socket)
            #
            #     print(f"Added user {client_socket} to MAC {mac}")
            #
            # print("self.mac_agent_user_dic →", self.mac_agent_user_dic)

            # אם המשתמש עדיין לא קיים ברשימה
            if user_id not in self.mac_agent_user_dic[mac]["users"]:
                # מוסיפים אותו
                self.mac_agent_user_dic[mac]["users"].append(user_id)

                print(f"Added user {user_id} to MAC {mac}")

        print("self.mac_agent_user_dic →", self.mac_agent_user_dic)

    def get_alerts_for_user(self, user_id, command):
        print(f"Searching alerts for user {user_id}")
        print("Current MAC dictionary:", self.mac_agent_user_dic)
        agent_id = None

        for mac, data in self.mac_agent_user_dic.items():
            print(
                f"Checking MAC={mac}, users={data['users']}, "
                f"agent_id={data['agent_id']}"
            )
            if user_id in data["users"]:
                agent_id = data["agent_id"]
                print(f"Found matching agent_id = {agent_id}")
                break

        if not agent_id:
            print(f"No agent found for user {user_id}")
            return []

        if command == "get_files_alerts":
            # ה-ID האחרון שכבר נשלח למשתמש
            last_id = self.last_sent_alert_id_files.get(user_id, 0)

            # שליפת רק התרעות חדשות
            alerts = data_base.get_alerts_about_files(agent_id, last_id)
            print("alerts1:", alerts)

            result = []

            for alert in alerts:
                row = [
                    str(alert[0]),  # id
                    str(alert[1]),  # agent_id
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

                self.last_sent_alert_id_files[user_id] = last_alert_id

            print("result:", result)
            return result

        else:
            # ה-ID האחרון שכבר נשלח למשתמש
            last_id = self.last_sent_alert_id_process.get(user_id, 0)
            # שליפת רק התרעות חדשות
            alerts = data_base.get_alerts_about_process(agent_id, last_id)
            print("alerts1:", alerts)

            result = []
            for alert in alerts:
                row = [
                    str(alert[0]),  # id
                    str(alert[1]),  # agent_id
                    str(alert[2]),  # time
                    str(alert[3]),  # process_name
                    str(alert[4]),  # pid
                    str(alert[5]),  # exe_path
                    str(alert[6]),  # risk
                    str(alert[7]),  # reason
                    str(alert[8])  # status
                ]

                result.append(row)

            # עדכון ה-ID האחרון שנשלח
            if alerts:
                last_alert_id = alerts[-1][0]

                self.last_sent_alert_id_process[user_id] = last_alert_id

            print("result:", result)
            return result


if __name__ == "__main__":
    server = Server()
    server.start()

