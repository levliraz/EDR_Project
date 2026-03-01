import wx
import field_integrity_checks


class LoginPage:
    def __init__(self, parent):
        self.panel = wx.Panel(parent)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetBackgroundColour(wx.Colour(255, 182, 193))
        self.login_message = None
        self.client_status_message_login = None
        self.login_name = None
        self.login_password = None
        self.login_email = None
        self.show_password_cb = None
        self.password_sizer = None
        self.design = parent

    def create_login_page(self):
        # Sizer ייעודי לסיסמה יוצרים
        self.password_sizer = wx.BoxSizer(wx.VERTICAL)
        # יצירת פונט גדול
        font_big = wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        # תיבת הודעת שגיאה
        self.login_message = wx.StaticText(self.panel, label="")
        self.login_message.SetForegroundColour(wx.RED)
        self.login_message.SetFont(font_big)
        self.vbox.Add(self.login_message, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 20)

        # הודעת סטטוס
        self.client_status_message_login = wx.StaticText(self.panel, label="")
        self.client_status_message_login.SetForegroundColour(wx.WHITE)
        self.client_status_message_login.SetFont(font_big)
        self.vbox.Add(self.client_status_message_login, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 20)

        # כותרת למסך
        label = wx.StaticText(self.panel, label="Login page")
        label.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.vbox.Add(label, 0, wx.CENTER | wx.TOP, 20)

        lbl_name = wx.StaticText(self.panel, label="Full Name:")
        self.login_name = wx.TextCtrl(self.panel, style=0)

        self.vbox.Add(lbl_name, 0, wx.CENTER | wx.TOP, 20)
        self.vbox.Add(self.login_name, 0, wx.CENTER | wx.TOP, 20)

        # תווית ותיבת טקסט לאימייל
        lbl_email = wx.StaticText(self.panel, label="Email:")
        self.login_email = wx.TextCtrl(self.panel, style=0)

        print("CREATED login_email:", id(self.login_email))

        self.vbox.Add(lbl_email, 0, wx.CENTER | wx.TOP, 20)
        self.vbox.Add(self.login_email, 0, wx.CENTER | wx.TOP, 20)

        # תווית ותיבת טקסט לסיסמה
        lbl_password = wx.StaticText(self.panel, label="Password:")
        self.login_password = wx.TextCtrl(self.panel, style=wx.TE_PASSWORD)

        self.vbox.Add(lbl_password, 0, wx.CENTER | wx.TOP, 20)
        #נוסיף לסידור של הסיסמא את הסיסמא ורק אז את הסידור של הסיסמא לסידור הכולל של הפאנל
        self.password_sizer.Add(self.login_password, 0, wx.CENTER | wx.TOP, 10)
        self.vbox.Add(self.password_sizer, 0, wx.EXPAND)

        #יצירת כפתור שמראה את הסיסמא
        self.show_password_cb = wx.CheckBox(self.panel,label="show password")
        self.vbox.Add(self.show_password_cb, 0, wx.CENTER | wx.TOP, 5)
        self.show_password_cb.Bind(wx.EVT_CHECKBOX, self.on_toggle_password)

        # כפתור התחברות
        btn_login = wx.Button(self.panel, label="log in")
        btn_login.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.vbox.Add(btn_login, 0, wx.CENTER | wx.TOP, 20)

        # כפתור חזרה
        btn_back = wx.Button(self.panel, label="back")
        btn_back.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.vbox.Add(btn_back, 0, wx.CENTER | wx.TOP, 20)

        # חיבור אירוע- לחיצה על התחברות
        btn_login.Bind(wx.EVT_BUTTON, self.on_login_click)

        # חיבור אירוע
        btn_back.Bind(wx.EVT_BUTTON, lambda e: self.design.show_panel("home"))

        self.panel.SetSizer(self.vbox)
        return self.panel


    def on_login_click(self, event):
        f_name = self.login_name.GetValue()
        email = self.login_email.GetValue()
        password = self.login_password.GetValue()
        print(password)

        if not field_integrity_checks.check_fields(f_name, email, password, password, self.login_message):
            return

        data = self.design.send_and_receive_data("login", f_name, email, password)
        if data.startswith("Welcome"):
            self.design.user_page_obj.user_status_message.SetLabel(data)
            self.design.show_panel("user")

        elif data.startswith("Wrong"):
            self.login_password.Clear()

        else:
            #ניקוי השדות
            self.login_name.Clear()
            self.login_email.Clear()
            self.login_password.Clear()
            self.login_message.SetLabel("")

        self.client_status_message_login.SetLabel(data)
        return data

    def on_toggle_password(self, event):
        value = self.login_password.GetValue()
        # מוחקים לגמרי את השדה הקודם
        self.password_sizer.Clear(delete_windows=True)
        if self.show_password_cb.IsChecked():
            # שדה גלוי
            self.login_password = wx.TextCtrl(self.panel)
        else:
            # שדה מוסתר
            self.login_password = wx.TextCtrl(self.panel,style=wx.TE_PASSWORD)

        self.login_password.SetValue(value)
        self.password_sizer.Add(self.login_password, 0, wx.CENTER | wx.TOP, 10)
        self.panel.Layout()

