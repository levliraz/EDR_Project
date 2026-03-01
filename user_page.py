import wx


class UserPage:
    def __init__(self,parent):
        self.panel = wx.Panel(parent)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetBackgroundColour(wx.Colour(255, 182, 193))
        self.alerts_table = None  # טבלת ה-ListCtrl
        self.agent = None
        self.user_status_message = None
        self.btn_agent = None
        self.lbl_name = None
        self.alerts_data = []
        self.design = parent

    def create_user_page(self):
        # פונט גדול
        font_big = wx.Font(18, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)

        # הודעת סטטוס
        self.user_status_message = wx.StaticText(self.panel, label="")
        self.user_status_message.SetForegroundColour(wx.WHITE)
        self.user_status_message.SetFont(font_big)
        self.vbox.Add(self.user_status_message, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 20)

        self.lbl_name = wx.StaticText(self.panel, label="הראה לי קבצים חשודים שרצים במחשב")

        self.vbox.Add(self.lbl_name, 0, wx.CENTER | wx.TOP, 20)

        # כפתור הורדה
        self.btn_agent = wx.Button(self.panel, label="Enter")
        self.btn_agent.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.vbox.Add(self.btn_agent, 0, wx.CENTER | wx.TOP, 20)

        # דוחף את הכפתור התחתון למטה
        self.vbox.AddStretchSpacer()
        # סייזר תחתון
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bottom_sizer.AddStretchSpacer()

        # כפתור התנתקות
        btn_disconnection = wx.Button(self.panel, label="התנתקות")
        btn_disconnection.SetBackgroundColour(wx.Colour(255, 255, 255))
        btn_disconnection.SetFont(font_big)
        bottom_sizer.Add(btn_disconnection, 0, wx.RIGHT | wx.BOTTOM, 20)

        # חיבור אירוע- לחיצה על התחברות
        self.btn_agent.Bind(wx.EVT_BUTTON, self.on_agent_click)

        # חיבור אירוע
        btn_disconnection.Bind(wx.EVT_BUTTON, lambda e: self.design.disconnection())

        self.vbox.Add(bottom_sizer, 0, wx.EXPAND)
        self.panel.SetSizer(self.vbox)
        return self.panel

    def on_agent_click(self, event):
        self.lbl_name.Hide()
        self.btn_agent.Hide()
        self.panel.Layout()

        data = self.design.send_and_receive_data("client", "null", "null", "null")
        if data == "hi client":
            self.design.my_socket.send("show me the data that the agent collectd".encode())

            self.alerts_data.clear()  # מנקה – זה כבר טוב

            while True:
                raw_data = self.design.my_socket.recv(2048).decode(errors='ignore').strip()
                print("Received from server:", repr(raw_data))  # debug – תראי מה באמת מגיע

                if not raw_data:
                    continue  # אם ריק – דלג

                if raw_data == "END":
                    print("Received END – stopping")
                    break

                list_data = raw_data.split("|")
                self.alerts_data.append(list_data)
                print("Added row:", list_data)

                self.design.my_socket.send("send more".encode())

            print(f"Total rows collected: {len(self.alerts_data)}")
            self.show_alerts_table()

    def show_alerts_table(self):
        # ===== מחיקת כל מה שהיה קודם באזור הטבלה =====
        # אם קיים panel_scrolled ישן – מחק אותו
        if hasattr(self, 'panel_scrolled') and self.panel_scrolled:
            self.panel_scrolled.Destroy()
            del self.panel_scrolled

        # אם קיים ListCtrl ישן – מחק גם אותו (ליתר ביטחון)
        if hasattr(self, 'alerts_table') and self.alerts_table:
            self.alerts_table.Destroy()
            del self.alerts_table

        # ===== יצירה מחדש =====
        self.panel_scrolled = wx.ScrolledWindow(self.panel, style=wx.VSCROLL)
        sizer_scrolled = wx.BoxSizer(wx.VERTICAL)
        self.panel_scrolled.SetSizer(sizer_scrolled)

        self.alerts_table = wx.ListCtrl(
            self.panel_scrolled,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_VRULES
        )

        columns = ["ID", "Timestamp", "Type", "File Name", "Risk", "Reason", "Status", "Process Name", "PID"]
        columns_widths = [40, 170, 200, 350, 40, 250, 120, 220, 80]

        for idx, col_name in enumerate(columns):
            self.alerts_table.InsertColumn(idx, col_name)
            self.alerts_table.SetColumnWidth(idx, columns_widths[idx])

        for index, alert in enumerate(self.alerts_data):
            # סינון agent_id (אם הוא קיים במיקום 1)
            filtered_alert = alert[:1] + alert[2:] if len(alert) > 1 else alert

            self.alerts_table.InsertItem(index, str(filtered_alert[0]))

            for col_idx in range(1, len(filtered_alert)):
                self.alerts_table.SetItem(index, col_idx, str(filtered_alert[col_idx]))

            # צביעה לפי Risk
            try:
                risk = int(filtered_alert[4])  # Risk במיקום 4 אחרי הסינון
                if risk >= 50:
                    self.alerts_table.SetItemBackgroundColour(index, wx.Colour(255, 0, 0))
                elif risk >= 30:
                    self.alerts_table.SetItemBackgroundColour(index, wx.Colour(255, 255, 0))
                else:
                    self.alerts_table.SetItemBackgroundColour(index, wx.Colour(144, 238, 144))
            except (ValueError, IndexError):
                pass

        sizer_scrolled.Add(self.alerts_table, 1, wx.EXPAND | wx.ALL, 5)

        # הוספה ל-vbox – אבל רק אם לא קיים כבר (או תמיד במקום 3)
        # כדי למנוע כפילות – קודם נסיר את כל מה שבין index 3 ומטה אם צריך
        if len(self.vbox.GetChildren()) > 3:
            for i in range(len(self.vbox.GetChildren()) - 1, 2, -1):
                child = self.vbox.GetItem(i).GetWindow()
                if child:
                    child.Destroy()

        self.vbox.Insert(3, self.panel_scrolled, 1, wx.EXPAND | wx.ALL, 10)

        self.panel.Layout()
        self.panel.Refresh()  # חשוב – מרענן את התצוגה
        self.panel.Update()  # עוזר לפעמים







