import wx
import field_integrity_checks

class RegisterPage:
    def __init__(self, parent):
        self.panel = wx.Panel(parent)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetBackgroundColour(wx.Colour(255, 182, 193))
        self.register_message = None
        self.register_name = None
        self.register_password = None
        self.register_email = None
        self.register_confirm = None
        self.show_password_cb = None
        self.password_sizer = None
        self.design = parent

    def create_register_page(self):
        self.password_sizer = wx.BoxSizer(wx.VERTICAL)
        # פונט גדול
        font_big = wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        # נוסיף תיבת טקסט להודעת שגיאה
        self.register_message = wx.StaticText(self.panel, label="")
        self.register_message.SetForegroundColour(wx.RED)  # צבע ההודעה
        self.register_message.SetFont(font_big)
        self.vbox.Add(self.register_message, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 20)

        label = wx.StaticText(self.panel, label="Registration page", pos=(160, 30))
        label.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.vbox.Add(label, 0, wx.CENTER | wx.TOP, 20)

        lbl_name = wx.StaticText(self.panel, label="Full Name:")
        self.register_name = wx.TextCtrl(self.panel, style=0)

        self.vbox.Add(lbl_name, 0, wx.CENTER | wx.TOP, 20)
        self.vbox.Add(self.register_name, 0, wx.CENTER | wx.TOP, 20)

        lbl_email = wx.StaticText(self.panel, label="Email:")
        self.register_email = wx.TextCtrl(self.panel, style=0)

        self.vbox.Add(lbl_email, 0, wx.CENTER | wx.TOP, 20)
        self.vbox.Add(self.register_email, 0, wx.CENTER | wx.TOP, 20)

        # תווית ותיבת טקסט לסיסמה
        lbl_password = wx.StaticText(self.panel, label="Password:")
        self.register_password = wx.TextCtrl(self.panel, style=wx.TE_PASSWORD)

        self.vbox.Add(lbl_password, 0, wx.CENTER | wx.TOP, 20)
        self.password_sizer.Add(self.register_password, 0, wx.CENTER | wx.TOP, 10)
        self.vbox.Add(self.password_sizer, 0, wx.EXPAND)

        self.show_password_cb = wx.CheckBox(self.panel,label="show password")
        self.vbox.Add(self.show_password_cb, 0, wx.CENTER | wx.TOP, 5)
        self.show_password_cb.Bind(wx.EVT_CHECKBOX, self.on_toggle_password)

        lbl_confirm = wx.StaticText(self.panel, label="Password verification:")
        self.register_confirm = wx.TextCtrl(self.panel, style=wx.TE_PASSWORD)

        self.vbox.Add(lbl_confirm, 0, wx.CENTER | wx.TOP, 20)
        self.vbox.Add(self.register_confirm, 0, wx.CENTER | wx.TOP, 20)

        # כפתור הרשמה
        btn_register = wx.Button(self.panel, label="Sign up")
        btn_register.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.vbox.Add(btn_register, 0, wx.CENTER | wx.TOP, 20)

        btn_back = wx.Button(self.panel, label="back", pos=(150, 130))
        btn_back.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.vbox.Add(btn_back, 0, wx.ALL | wx.CENTER, 10)

        # חיבור אירוע- לחיצה על התחברות
        btn_register.Bind(wx.EVT_BUTTON, self.on_register_click)

        btn_back.Bind(wx.EVT_BUTTON, lambda e: self.design.show_panel("home"))
        self.panel.SetSizer(self.vbox)
        return self.panel


    def on_register_click(self, event):
        f_name = self.register_name.GetValue()
        email = self.register_email.GetValue()
        password = self.register_password.GetValue()
        val_password = self.register_confirm.GetValue()

        if not field_integrity_checks.check_fields(f_name, email, password, val_password, self.register_message):
            return
        data = self.design.send_and_receive_data("register", f_name, email, password)

        # ניקוי השדות
        self.register_name.Clear()
        self.register_email.Clear()
        self.register_password.Clear()
        self.register_confirm.Clear()
        self.register_message.SetLabel("")

        self.design.login_page_obj.client_status_message_login.SetLabel(data)
        self.design.show_panel("login")

    def on_toggle_password(self, event):
        value = self.register_password.GetValue()
        # מוחקים לגמרי את השדה הקודם
        self.password_sizer.Clear(delete_windows=True)
        if self.show_password_cb.IsChecked():
            # שדה גלוי
            self.register_password = wx.TextCtrl(self.panel)
        else:
            # שדה מוסתר
            self.register_password = wx.TextCtrl(self.panel,style=wx.TE_PASSWORD)

        self.register_password.SetValue(value)
        self.password_sizer.Add(self.register_password, 0, wx.CENTER | wx.TOP, 10)
        self.panel.Layout()
