import wx
import os

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
        self.selected_file_path = None
        self.row_map = {}
        self.design = parent
        self.timer_for_delete = None
        self.delete_file_button = None
        self.timer_for_update = None
        self.timer_for_fetch = None
        self.selected_row_data = None

    def create_user_page(self):
        # טיימר לשליחת בקשה לשרת כל דקה
        self.timer_for_fetch = wx.Timer(self.panel)
        self.panel.Bind(wx.EVT_TIMER, self.request_new_alerts, self.timer_for_fetch)
        self.timer_for_fetch.Start(30_000)  # 30 שניות

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

        self.btn_agent.Bind(wx.EVT_BUTTON, self.on_agent_click)

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

        # כפתור מחיקה של קובץ
        self.delete_file_button = wx.Button(self.panel, label="מחק")
        self.delete_file_button.SetBackgroundColour(wx.Colour(200, 0, 0))  # אדום חזק
        self.delete_file_button.SetForegroundColour(wx.Colour(255, 255, 255))  # טקסט לבן
        font = wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
        self.delete_file_button.SetFont(font)
        self.delete_file_button.SetMinSize((120, 45))  # גודל כפתור
        self.delete_file_button.Hide()
        self.delete_file_button.Bind(wx.EVT_BUTTON, self.delete_file)

        self.vbox.Add(self.delete_file_button, 0, wx.CENTER | wx.TOP, 10)

        # חיבור אירוע
        btn_disconnection.Bind(wx.EVT_BUTTON, lambda e: self.design.disconnection())

        self.vbox.Add(bottom_sizer, 0, wx.EXPAND)
        self.panel.SetSizer(self.vbox)

        return self.panel

    def request_new_alerts(self, event=None):
        try:
            data = self.design.send_and_receive_data("get_alerts", "null", "null", "null")

            if not data:
                return

            if data == "NO_ALERTS":
                return

            alerts_list = data.split("||")  # מפריד בין שורות

            print("alerts_list:", alerts_list)

            for alert in alerts_list:
                print("alert:", alert)

                if alert.strip():
                    row = alert.split("|")
                    print("row:", row)

                    if len(row) < 9:
                        print("Bad row (skipped):", row)
                        continue

                    wx.CallAfter(self.update_table, row)

        except Exception as e:
            print("error fetching alerts:", e)

    def on_agent_click(self, event):
        self.lbl_name.Hide()
        self.btn_agent.Hide()
        self.panel.Layout()

        self.alerts_data.clear()  # מנקה – מאפס דאטה

        # יוצר טבלה פעם אחת (ריקה)
        self.show_alerts_table()

    # מזהה איזו שורה נלחצה,שומר את השורה ברשימה
    def on_row_click(self, event):
        index = event.GetIndex()
        self.selected_file_path = self.alerts_table.GetItem(index, 5).GetText()

        # לוקחים את ה-ID מהעמודה הראשונה בטבלה
        alert_id = self.alerts_table.GetItem(index, 1).GetText()

        # מביאים את כל המידע מהמילון
        self.selected_row_data = self.row_map[alert_id]

        self.delete_file_button.Show()
        self.panel.Layout()

    def delete_file(self, event):
        if not self.selected_file_path:
            return

        print("PATH FROM DB:", self.selected_file_path)
        print("EXISTS?:", os.path.exists(self.selected_file_path))

        dlg = wx.MessageDialog(
            self.panel,
            "האם אתה בטוח שתרצה למחוק את הקובץ?",
            "אישור מחיקה",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING
        )

        result = dlg.ShowModal()
        dlg.Destroy()

        if result == wx.ID_YES:
            if os.path.exists(self.selected_file_path):
                os.remove(self.selected_file_path)
                print("נמחק בהצלחה")

                # נבצע שליחה של הקובץ לשרת
                row_data = self.selected_row_data
                if row_data:
                    print("row_data:", row_data)
                    self.design.send_and_receive_data("delete_alert", row_data, "null", "null")

                # מחיקה מהטבלה ומהזיכרון
                for row in range(self.alerts_table.GetItemCount()):
                    path = self.alerts_table.GetItem(row, 5).GetText()
                    if path == self.selected_file_path:
                        self.alerts_table.DeleteItem(row)
                        #מסדרים מחדש את המספרים
                        self.refresh_ui_numbers()
                        if row < len(self.alerts_data):
                            #מוחק מהזיכרון את אותה שורה שנמחקה מהטבלה
                            self.alerts_data.pop(row)

                        break

                self.alerts_table.Refresh()
                self.panel.Layout()
                self.panel.Refresh()

            else:
                print("הקובץ לא נמצא")

        self.delete_file_button.Hide()
        self.selected_file_path = None
        self.panel.Layout()


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

        columns = ["", "ID", "Timestamp", "Type", "File Name", "File Path", "Risk", "Reason", "Status"]
        widths = [40, 40, 170, 170, 280, 300, 40, 250, 120]

        for i, col in enumerate(columns):
            self.alerts_table.InsertColumn(i, col)
            self.alerts_table.SetColumnWidth(i, widths[i])

        sizer_scrolled.Add(self.alerts_table, 1, wx.EXPAND | wx.ALL, 5)

        self.vbox.Insert(3, self.panel_scrolled, 1, wx.EXPAND | wx.ALL, 10)

        self.panel.Layout()


    def update_table(self, list_data):
        if not self.alerts_table:
            return

        # שמירת הנתונים בזיכרון
        self.alerts_data.append(list_data)

        # בדיקת אורך בטיחות
        if len(list_data) < 9:
            print("Bad row:", list_data)
            return

        # אינדקס שורה
        index = self.alerts_table.GetItemCount()

        alert_id = list_data[0]
        # שמירת כל השורה המקורית (כולל agent_id)
        self.row_map[alert_id] = list_data

        self.alerts_table.InsertItem(index, str(index + 1))  # UI number
        self.alerts_table.SetItem(index, 1, list_data[0])  # DB ID

        self.alerts_table.SetItem(index, 2, list_data[2])
        self.alerts_table.SetItem(index, 3, list_data[3])
        self.alerts_table.SetItem(index, 4, list_data[4])
        self.alerts_table.SetItem(index, 5, list_data[5])
        self.alerts_table.SetItem(index, 6, list_data[6])
        self.alerts_table.SetItem(index, 7, list_data[7])
        self.alerts_table.SetItem(index, 8, list_data[8])

        # צבע לפי Risk
        try:
            risk = int(list_data[6])  # לא filtered!

            if risk >= 50:
                color = wx.Colour(255, 0, 0)
            elif risk >= 30:
                color = wx.Colour(255, 255, 0)
            else:
                color = wx.Colour(144, 238, 144)

            self.alerts_table.SetItemBackgroundColour(index, color)

        except Exception as e:
            print("Risk error:", e)

        self.alerts_table.Refresh()
        self.panel_scrolled.Layout()
        self.panel_scrolled.FitInside()
        self.panel_scrolled.Refresh()

    def refresh_ui_numbers(self):
        for row in range(self.alerts_table.GetItemCount()):
            self.alerts_table.SetItem(row, 0, str(row + 1))

