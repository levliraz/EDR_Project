import wx
import os
import subprocess

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
        # self.search_ctrl = wx.TextCtrl(self.panel, style=wx.TE_PROCESS_ENTER)
        # self.search_ctrl.Bind(wx.EVT_TEXT, self.on_search)

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

        #אירוע שקורה בלחיצה כפולה על שורה מהטבלה
        self.alerts_table.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_row_click)


        columns = ["ID", "Timestamp", "Type", "File Name", "File Path",  "Risk", "Reason", "Status"]
        columns_widths = [40, 170, 170, 280, 300, 40, 250, 120]

        #alert: ['16', '7f6ec056-c437-4f36-b80c-c72b397e78d8', '2026-03-18 13:47:47', 'application/javascript', 'JS.js', 'C:\\Users\\TLV\\Downloads\\project4omer\\project4omer\\JS\\JS.js', '20', 'Suspicious extension', 'in_progress']

        #enumerate(columns) – זה פשוט נותן לנו מספר + שם של כל עמודה.
        for idx, col_name in enumerate(columns):
            #InsertColumn(idx, col_name) – מוסיף עמודה חדשה במיקום idx עם הכותרת col_name.
            self.alerts_table.InsertColumn(idx, col_name)
            self.alerts_table.SetColumnWidth(idx, columns_widths[idx])

        #self.alerts_data היא רשימה של רשימות. כל איבר ברשימה הזו הוא שורה אחת מהדאטהבייס
        for index, alert in enumerate(self.alerts_data):
            # סינון agent_id (אם הוא קיים במיקום 1)
            filtered_alert = alert[:1] + alert[2:] if len(alert) > 1 else alert

            #str(filtered_alert[0])
            self.alerts_table.InsertItem(index, str(index + 1))

            for col_idx in range(1, len(filtered_alert)):
                self.alerts_table.SetItem(index, col_idx, str(filtered_alert[col_idx]))

            # צביעה לפי Risk
            try:
                risk = int(filtered_alert[5])  # Risk במיקום 5 אחרי הסינון
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





