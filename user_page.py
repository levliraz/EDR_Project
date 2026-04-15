import wx
import os
import subprocess
import threading

class UserPage:
    def __init__(self, parent):
        self.panel = wx.Panel(parent)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetBackgroundColour(wx.Colour(255, 182, 193))

        # טבלת ה-ListCtrl
        self.alerts_table = None
        self.alerts_data = []

        # שאר משתנים
        self.agent = None
        self.user_status_message = None
        self.btn_agent = None
        self.lbl_name = None
        self.search_ctrl = None
        self.panel_scrolled = None
        self.design = parent

        # ===== יצירת טיימר לבדיקה אוטומטית של קבצים שנמחקו =====
        self.timer = wx.Timer()  # יוצרים את הטיימר
        self.timer.Bind(wx.EVT_TIMER, self.check_deleted_files)  # מחברים אירוע טיימר לפונקציה
        self.timer.Start(3000)  # כל 3 שניות

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

            self.alerts_data.clear()  # מנקה – מאפס דאטה

            # יוצר טבלה פעם אחת (ריקה)
            self.show_alerts_table()

            # recv() הוא blocking function
            # הוא עוצר את כל התוכנית עד שמגיע מידע מהשרת
            # בלי תרד, ה־GUI נתקע. ב־ wxPython יש רק thread אחד שמותר לו לצייר ולעדכן את המסך:Main UI Thread
            # עם תרד, הפונקציה של קבלת נתונים תרוץ ברקע, בלי לעצור את המסך

            #  מתחיל thread שמקבל נתונים
            threading.Thread(target=self.receive_data, daemon=True).start()

    def receive_data(self):
        while True:
            raw_data = self.design.my_socket.recv(2048).decode(errors='ignore').strip()
            print("Received from server:", repr(raw_data))  # debug – תראי מה באמת מגיע

            if not raw_data:
                continue  # אם ריק – דלג

            # סינון הודעות שלא שייכות לטבלה
            if "|" not in raw_data:
                print("Ignored non-table message:", raw_data)
                continue

            list_data = raw_data.split("|")
            print("Added row:", list_data)

            wx.CallAfter(self.update_table, list_data)

            self.design.my_socket.send("send more".encode())

        print(f"Total rows collected: {len(self.alerts_data)}")
        # self.show_alerts_table()

    # מזהה איזו שורה נלחצה, שולף את כתובת הקובץ ומציג אותו בסייר הקבצים(פתיחת חלון)
    def on_row_click(self, event):
        index = event.GetIndex()
        file_path = self.alerts_table.GetItem(index, 4).GetText()

        if os.path.exists(file_path):
            # פותח את סייר הקבצים ומסמן את הקובץ
            subprocess.run(f'explorer /select,"{file_path}"')
        else:
            print("הקובץ לא נמצא")

    def show_alerts_table(self):
        # אם כבר קיימת טבלה לא לבנות מחדש
        if self.alerts_table:
            return

        self.panel_scrolled = wx.ScrolledWindow(self.panel, style=wx.VSCROLL)

        sizer_scrolled = wx.BoxSizer(wx.VERTICAL)
        self.panel_scrolled.SetSizer(sizer_scrolled)

        self.alerts_table = wx.ListCtrl(
            self.panel_scrolled,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_VRULES
        )

        self.alerts_table.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_row_click)

        columns = ["ID", "Timestamp", "Type", "File Name", "File Path", "Risk", "Reason", "Status"]
        widths = [40, 170, 170, 280, 300, 40, 250, 120]

        for i, col in enumerate(columns):
            self.alerts_table.InsertColumn(i, col)
            self.alerts_table.SetColumnWidth(i, widths[i])

        sizer_scrolled.Add(self.alerts_table, 1, wx.EXPAND | wx.ALL, 5)

        self.vbox.Insert(3, self.panel_scrolled, 1, wx.EXPAND | wx.ALL, 10)

        self.panel.Layout()

    def check_deleted_files(self, event):
        if not self.alerts_table:
            return  # אם עדיין אין טבלה – דלג

        rows_to_delete = []

        for row in range(self.alerts_table.GetItemCount()):
            file_path = self.alerts_table.GetItem(row, 4).GetText()
            if not os.path.exists(file_path):
                rows_to_delete.append(row)

        for row in reversed(rows_to_delete):
            self.alerts_table.DeleteItem(row)
            # אם רוצים – נמחק גם מה-alerts_data
            if row < len(self.alerts_data):
                self.alerts_data.pop(row)

    def update_table(self, list_data):
        if not self.alerts_table:
            return

        # שמירת הנתונים בזיכרון
        self.alerts_data.append(list_data)

        # חיתוך אינדקסים 0,1
        filtered = list_data[:1] + list_data[2:] if len(list_data) > 2 else list_data

        index = self.alerts_table.GetItemCount()

        # ID
        self.alerts_table.InsertItem(index, str(index + 1))

        # שאר העמודות
        for col_idx in range(1, len(filtered)):
            self.alerts_table.SetItem(index, col_idx, str(filtered[col_idx]))

        # צבע לפי Risk
        try:
            risk = int(filtered[5])

            if risk >= 50:
                color = wx.Colour(255, 0, 0)
            elif risk >= 30:
                color = wx.Colour(255, 255, 0)
            else:
                color = wx.Colour(144, 238, 144)

            self.alerts_table.SetItemBackgroundColour(index, color)

        except:
            pass



