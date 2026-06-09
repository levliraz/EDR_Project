import wx
import os

class UserPage:
    def __init__(self, parent):
        self.panel = wx.Panel(parent)
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetBackgroundColour(wx.Colour(255, 182, 193))

        # טבלאות ה-ListCtrl
        self.alerts_table = None
        self.alerts_data = []

        self.process_table = None
        self.process_data = []

        self.show_files = False
        self.show_processes = False

        self.files_visible = False
        self.process_visible = False

        # שאר משתנים
        self.agent = None
        self.user_status_message = None
        self.btn_files = None
        self.lbl_name = None
        self.search_ctrl = None
        self.panel_scrolled_files = None
        self.panel_scrolled_processes = None
        self.selected_file_path = None
        self.row_map = {}
        self.design = parent
        self.timer_for_delete = None
        self.delete_file_button = None
        self.timer_for_update = None
        self.timer_for_fetch = None
        self.selected_row_data = None
        self.current_search = ""
        self.current_color_filter = "הכל"

    def create_user_page(self):
        # טיימר לשליחת בקשה לשרת כל חצי דקה
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
        self.btn_files = wx.Button(self.panel, label="הצג טבלת קבצים")
        self.btn_files.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.vbox.Add(self.btn_files, 0, wx.CENTER | wx.TOP, 20)

        self.btn_files.Bind(wx.EVT_BUTTON, self.on_files_click)

        self.btn_processes = wx.Button(self.panel,label="הצג טבלת תהליכים")
        self.btn_processes.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.vbox.Add(self.btn_processes,0,wx.CENTER | wx.TOP,10)

        self.btn_processes.Bind(wx.EVT_BUTTON,self.on_process_click)

        self.btn_hide_files = wx.Button(self.panel, label="הסתר טבלת קבצים")
        self.btn_hide_files.Bind(wx.EVT_BUTTON, self.on_hide_files)
        self.vbox.Add(self.btn_hide_files, 0, wx.CENTER | wx.TOP, 10)
        self.btn_hide_files.Hide()

        self.btn_hide_processes = wx.Button(self.panel, label="הסתר טבלת תהליכים")
        self.btn_hide_processes.Bind(wx.EVT_BUTTON, self.hide_process_table)
        self.vbox.Add(self.btn_hide_processes, 0, wx.CENTER | wx.TOP, 10)
        self.btn_hide_processes.Hide()

        # חיפוש לפי שם קובץ
        self.search_ctrl = wx.SearchCtrl(self.panel)
        self.search_ctrl.Hide()
        self.search_ctrl.Bind(wx.EVT_TEXT, self.on_search)

        self.vbox.Add(self.search_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # פילטר צבע
        self.color_choice = wx.Choice(
            self.panel,
            choices=["הכל", "אדום", "צהוב", "ירוק"]
        )
        self.color_choice.SetSelection(0)
        self.color_choice.Hide()
        self.color_choice.Bind(wx.EVT_CHOICE, self.on_color_filter)

        self.vbox.Add(self.color_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

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
        self.fetch_file_alerts()
        self.fetch_process_alerts()

    # עדכון טבלת קבצים
    def fetch_file_alerts(self):
        data = self.design.send_and_receive_data(
            "get_files_alerts",
            "null",
            "null",
            "null"
        )

        print("PROCESS DATA:", data)

        if not data or data == "NO_ALERTS":
            return

        alerts_list = data.split("||")

        for alert in alerts_list:

            if not alert.strip():
                continue

            row = alert.split("|")
            print("PROCESS ROW:", row)

            if len(row) < 9:
                continue

            wx.CallAfter(self.update_file_table, row)

    # עדכון טבלת תהליכים
    def fetch_process_alerts(self):
        data = self.design.send_and_receive_data(
            "get_process_alerts",
            "null",
            "null",
            "null"
        )

        print("PROCESS DATA:", data)

        if not data or data == "NO_ALERTS":
            return

        alerts_list = data.split("||")

        for alert in alerts_list:

            if not alert.strip():
                continue

            row = alert.split("|")
            print("PROCESS ROW:", row)

            if len(row) < 9:
                continue

            wx.CallAfter(self.update_process_table, row)

    def on_files_click(self, event):
        self.show_alerts_table()
        self.set_state(files=True, processes=False)

    def on_process_click(self, event):
        self.show_process_table()
        self.set_state(files=False, processes=True)

    def on_hide_files(self, event):
        self.set_state(files=False, processes=self.process_visible)

    def hide_process_table(self, event):
        self.set_state(files=self.files_visible, processes=False)

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

                alert_id = row_data[0]

                if row_data:
                    print("row_data:", row_data)
                    self.design.send_and_receive_data("delete_alert", row_data, "null", "null")

                # מחיקה מהטבלה ומהזיכרון
                for i, alert in enumerate(self.alerts_data):
                    if alert[0] == alert_id:
                        self.alerts_data.pop(i)
                        break

                # מחיקה מהמילון
                if alert_id in self.row_map:
                    del self.row_map[alert_id]

                # רענון הטבלה
                self.refresh_table()

            else:
                print("הקובץ לא נמצא")

        self.delete_file_button.Hide()
        self.selected_file_path = None
        self.panel.Layout()

    def show_alerts_table(self):
        if self.alerts_table:
            return

        self.panel_scrolled_files = wx.ScrolledWindow(self.panel, style=wx.VSCROLL)
        sizer_scrolled = wx.BoxSizer(wx.VERTICAL)
        self.panel_scrolled_files.SetSizer(sizer_scrolled)

        self.alerts_table = wx.ListCtrl(
            self.panel_scrolled_files,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_VRULES
        )

        self.alerts_table.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_row_click)

        columns = ["", "ID", "Timestamp", "Type", "File Name", "File Path", "Risk", "Reason", "Status"]
        widths = [40, 40, 170, 170, 230, 300, 40, 250, 120]

        for i, col in enumerate(columns):
            self.alerts_table.InsertColumn(i, col)
            self.alerts_table.SetColumnWidth(i, widths[i])

        sizer_scrolled.Add(self.alerts_table, 1, wx.EXPAND | wx.ALL, 5)

        self.vbox.Insert(3, self.panel_scrolled_files, 1, wx.EXPAND | wx.ALL, 10)

        self.panel.Layout()

    def show_process_table(self):
        if self.process_table:
            return

        self.panel_scrolled_processes = wx.ScrolledWindow(self.panel, style=wx.VSCROLL)
        sizer_scrolled = wx.BoxSizer(wx.VERTICAL)
        self.panel_scrolled_processes.SetSizer(sizer_scrolled)

        self.process_table = wx.ListCtrl(
            self.panel_scrolled_processes,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_VRULES
        )

        columns = ["", "ID", "Timestamp", "Process", "PID", "Path", "Risk", "Reason", "Status"]
        widths = [40, 40, 170, 180, 80, 300, 50, 250, 120]

        for i, col in enumerate(columns):
            self.process_table.InsertColumn(i, col)
            self.process_table.SetColumnWidth(i, widths[i])

        sizer_scrolled.Add(self.process_table, 1, wx.EXPAND | wx.ALL, 5)

        self.vbox.Insert(4, self.panel_scrolled_processes, 1, wx.EXPAND | wx.ALL, 10)

        self.panel.Layout()

    def update_file_table(self, list_data):
        if not self.alerts_table:
            return

        if len(list_data) < 9:
            print("Bad row:", list_data)
            return

        self.alerts_data.append(list_data)

        alert_id = list_data[0]
        self.row_map[alert_id] = list_data

        self.refresh_table()

        if self.panel_scrolled_files:
            self.panel_scrolled_files.Layout()
            self.panel_scrolled_files.FitInside()
            self.panel_scrolled_files.Refresh()

    def update_process_table(self, list_data):
        if not self.process_table:
            return

        if len(list_data) < 9:
            print("Bad row:", list_data)
            return

        self.process_data.append(list_data)

        self.refresh_process_table()

        if self.panel_scrolled_processes:
            self.panel_scrolled_processes.Layout()
            self.panel_scrolled_processes.FitInside()
            self.panel_scrolled_processes.Refresh()

    def on_search(self, event):
        self.current_search = self.search_ctrl.GetValue().lower()
        self.refresh_table()

    def on_color_filter(self, event):
        self.current_color_filter = self.color_choice.GetStringSelection()
        self.refresh_table()

    def refresh_table(self):
        self.alerts_table.DeleteAllItems()

        row_number = 1

        for row_data in self.alerts_data:

            file_name = row_data[4].lower()

            # סינון לפי שם
            if self.current_search:
                if self.current_search not in file_name:
                    continue

            # סינון לפי צבע
            risk = int(row_data[6])

            if self.current_color_filter == "אדום":
                if risk < 50:
                    continue

            elif self.current_color_filter == "צהוב":
                if risk < 30 or risk >= 50:
                    continue

            elif self.current_color_filter == "ירוק":
                if risk >= 30:
                    continue

            index = self.alerts_table.GetItemCount()

            self.alerts_table.InsertItem(index, str(row_number))
            self.alerts_table.SetItem(index, 1, row_data[0])
            self.alerts_table.SetItem(index, 2, row_data[2])
            self.alerts_table.SetItem(index, 3, row_data[3])
            self.alerts_table.SetItem(index, 4, row_data[4])
            self.alerts_table.SetItem(index, 5, row_data[5])
            self.alerts_table.SetItem(index, 6, row_data[6])
            self.alerts_table.SetItem(index, 7, row_data[7])
            self.alerts_table.SetItem(index, 8, row_data[8])

            if risk >= 50:
                color = wx.Colour(255, 0, 0)
            elif risk >= 30:
                color = wx.Colour(255, 255, 0)
            else:
                color = wx.Colour(144, 238, 144)

            self.alerts_table.SetItemBackgroundColour(index, color)

            row_number += 1

        self.alerts_table.Refresh()

    def refresh_process_table(self):

        self.process_table.DeleteAllItems()

        row_number = 1

        for row_data in self.process_data:

            risk = int(row_data[6])

            index = self.process_table.GetItemCount()

            self.process_table.InsertItem(index, str(row_number))
            self.process_table.SetItem(index, 1, row_data[0])
            self.process_table.SetItem(index, 2, row_data[2])
            self.process_table.SetItem(index, 3, row_data[3])
            self.process_table.SetItem(index, 4, row_data[4])
            self.process_table.SetItem(index, 5, row_data[5])
            self.process_table.SetItem(index, 6, row_data[6])
            self.process_table.SetItem(index, 7, row_data[7])
            self.process_table.SetItem(index, 8, row_data[8])

            if risk >= 50:
                color = wx.Colour(255, 0, 0)
            elif risk >= 30:
                color = wx.Colour(255, 255, 0)
            else:
                color = wx.Colour(144, 238, 144)

            self.process_table.SetItemBackgroundColour(index, color)

            row_number += 1

        self.process_table.Refresh()

    def set_state(self, files=False, processes=False):
        self.files_visible = files
        self.process_visible = processes
        self.update_ui()

    def update_ui(self):
        # FILES
        if self.files_visible:
            self.btn_files.Hide()
            self.btn_hide_files.Show()

            self.search_ctrl.Show()
            self.color_choice.Show()

            if self.panel_scrolled_files:
                self.panel_scrolled_files.Show()
        else:
            self.btn_hide_files.Hide()
            self.btn_files.Show()

            self.search_ctrl.Hide()
            self.color_choice.Hide()

            if self.panel_scrolled_files:
                self.panel_scrolled_files.Hide()

        # PROCESSES
        if self.process_visible:
            self.btn_processes.Hide()
            self.btn_hide_processes.Show()
            if self.panel_scrolled_processes:
                self.panel_scrolled_processes.Show()
        else:
            self.btn_hide_processes.Hide()
            self.btn_processes.Show()
            if self.panel_scrolled_processes:
                self.panel_scrolled_processes.Hide()

        self.panel.Layout()