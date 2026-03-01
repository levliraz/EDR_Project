import wx

class HomePage:
    def __init__(self, parent):
        self.panel = wx.Panel(parent)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetBackgroundColour(wx.Colour(255, 182, 193))
        self.design = parent

    def create_home_page(self):
        # פונט גדול
        font_big = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        label = wx.StaticText(self.panel, label="welcome!")
        label.SetFont(wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        btn_login = wx.Button(self.panel, label="Login", size=(150, 40))
        btn_register = wx.Button(self.panel, label="Register", size=(150, 40))
        btn_disconnection = wx.Button(self.panel, label="Logout", size=(150, 40))

        btn_login.SetFont(font_big)
        btn_register.SetFont(font_big)
        btn_disconnection.SetFont(font_big)

        btn_login.SetBackgroundColour(wx.Colour(255, 255, 255))
        btn_register.SetBackgroundColour(wx.Colour(255, 255, 255))
        btn_disconnection.SetBackgroundColour(wx.Colour(255, 255, 255))

        # הוספה ל-Sizer – רק Spacer מלמטה כדי שהכול יישאר למעלה
        self.vbox.Add(label, 0, wx.CENTER | wx.TOP, 30)
        self.vbox.Add(btn_login, 0, wx.CENTER | wx.TOP, 20)
        self.vbox.Add(btn_register, 0, wx.CENTER | wx.TOP, 20)
        self.vbox.Add(btn_disconnection, 0, wx.CENTER | wx.TOP, 20)

        self.vbox.AddStretchSpacer()  # דוחף הכול למעלה

        # אירועים
        btn_login.Bind(wx.EVT_BUTTON, lambda e: self.design.show_panel("login"))
        btn_register.Bind(wx.EVT_BUTTON, lambda e: self.design.show_panel("register"))
        btn_disconnection.Bind(wx.EVT_BUTTON, lambda e: self.design.disconnection())

        self.panel.SetSizer(self.vbox)
        return self.panel