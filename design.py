import wx
import encryption
from cryptography.hazmat.primitives import serialization
import socket
import user_page
import home_page
import login_page
import register_page
import uuid
import os
from getmac import get_mac_address
from threading import Lock

lock = Lock()

class MainFrame(wx.Frame):
    def __init__(self):

        super().__init__(None, title="Security project", size=(400, 300))
        self.Maximize()
        self.Center()
        self.Show()

        # יצירת סוקט שמחובר לשרת
        self.my_socket = socket.socket()
        self.my_socket.connect(("127.0.0.1", 1237))

        self.user_id = None
        self.create_user_id()

        # רשימת התראות שהתקבלו מהשרת
        self.alerts_list = []

        # ניצור משתנה כדי לדעת האם הסוכן כבר רץ במחשב.
        # בשביל שאם לקוח יתנתק ולקוח חדש יתחבר מאותו מחשב, שלא יהיו לי כמה סוכנים רצים.
        self.agent_started = False

        self.mac = get_mac_address()

        server_public_key_pem = self.my_socket.recv(2048)
        # print(server_public_key_pem)
        # הפונקצייה מפרקת את המחרוזת/קובץ PEM למפתח ציבורי שניתן להשתמש בו בקוד.
        #load_pem_public_key הופך את ה-PEM שקיבל הלקוח חזרה לאובייקט מפתח RSA שניתן לקרוא לו encrypt() עליו.
        self.server_public_key = serialization.load_pem_public_key(server_public_key_pem)

        if self.my_socket:
            print("connected")

        self.my_socket.send("GUI".encode())
        if self.my_socket.recv(1024).decode() == "welcome client!":
            user_id_to_send = encryption.encryption_data_server_and_client(self.user_id, self.server_public_key)
            self.my_socket.send(user_id_to_send)

            if self.my_socket.recv(1024).decode() == "Hi user_id":
                self.my_socket.send(self.mac.encode())

                if self.my_socket.recv(1024).decode() == "i got your mac":
                    # הגדרת הפאנלים
                    self.home_page_obj = home_page.HomePage(self)
                    self.panel_home = self.home_page_obj.create_home_page()

                    self.login_page_obj = login_page.LoginPage(self)
                    self.panel_login = self.login_page_obj.create_login_page()

                    self.panel_register = register_page.RegisterPage(self).create_register_page()

                    self.user_page_obj = user_page.UserPage(self)
                    self.panel_user = self.user_page_obj.create_user_page()

                    # הגדרת ה-sizer הראשי של ה-frame
                    self.sizer = wx.BoxSizer(wx.VERTICAL)
                    self.SetSizer(self.sizer)

                    # הוספת כל הפאנלים ל-frame
                    self.sizer.Add(self.panel_home, 1, wx.EXPAND)
                    self.sizer.Add(self.panel_login, 1, wx.EXPAND)
                    self.sizer.Add(self.panel_register, 1, wx.EXPAND)
                    self.sizer.Add(self.panel_user, 1, wx.EXPAND)

                    self.show_panel("home")
                    self.Show()


    def create_user_id(self):
        # ניצור user_id ונשלח אותו לשרת.
        # במחשב שלי
        #user_id_path = r"C:\Users\TLV\EDR_Project\user_id.txt"
        # במחשב בבית ספר
        user_id_path = r"C:\Users\Pc2\PycharmProjects\pythonProject\EDR_Project\user_id.txt"
        self.user_id = None
        if os.path.exists(user_id_path):
            self.user_id = open(user_id_path, "r").read().strip()

        if not self.user_id:
            self.user_id = str(uuid.uuid4())
            with open(user_id_path, "w") as f:
                f.write(self.user_id)

    def show_panel(self, name):
        self.panel_home.Hide()
        self.panel_login.Hide()
        self.panel_register.Hide()
        self.panel_user.Hide()

        if name == "home":
            self.panel_home.Show()
        elif name == "login":
            self.panel_login.Show()
        elif name == "register":
            self.panel_register.Show()
        elif name == "user":
            self.panel_user.Show()

        self.Layout()

    def disconnection(self):
        self.my_socket.close()  # סגירת החיבור לשרת
        self.Close()  # סגירת חלון ה־wx.Frame

    def send_and_receive_data(self, command, f_name, email, password):
        data = "not work"
        print(password)
        if not isinstance(f_name, list):
            message = f"{command}|{f_name}|{email}|{password}|{self.user_id}"
            print(message)
        else:
            id_alert = f_name[0]
            agent_id = f_name[1]
            file_name = f_name[4]
            message = f"{command}|{id_alert}|{agent_id}|{file_name}"
            print(message)

        encrypted_message = encryption.encryption_data_server_and_client(message, self.server_public_key)
        if self.my_socket:
            self.my_socket.send(encrypted_message)  # לא צריך להפוך לבייטים כי הוא כבר בייט
            data = self.my_socket.recv(4096).decode("utf-8")
            print("data-", data)
        return data


if __name__ == "__main__":
    app = wx.App()
    frame = MainFrame()
    app.MainLoop()
