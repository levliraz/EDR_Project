import wx
import os
import psutil


def terminate_process(pid):
    try:
        p = psutil.Process(int(pid))
        p.terminate()

        try:
            p.wait(timeout=3)
        except psutil.TimeoutExpired:
            p.kill()

        print("תהליך נסגר בהצלחה")

    except psutil.NoSuchProcess:
        print(f"התהליך {pid} כבר לא קיים")

    except psutil.AccessDenied:
        print(f"אין הרשאה לסגור תהליך {pid}")

    except Exception as e:
        print(f"שגיאה לא צפויה בסיום תהליך {pid}: {repr(e)}")


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
        self.btn_hide_files = None
        self.btn_processes = None
        self.btn_hide_processes = None
        self.lbl_name = None
        self.search_ctrl = None
        self.search_process_ctrl = None
        self.color_choice = None
        self.color_process_choice = None
        self.panel_scrolled_files = None
        self.panel_scrolled_processes = None
        self.selected_file_path = None
        self.selected_process_pid = None
        self.row_map = {}
        self.process_row_map = {}
        self.design = parent
        self.delete_file_button = None
        self.end_process_button = None
        self.timer_for_update = None
        self.timer_for_fetch = None
        self.selected_row_data = None
        self.files_sizer = None
        self.process_sizer = None
        self.current_search = ""
        self.process_current_search = ""
        self.current_color_filter = "הכל"
        self.current_process_color_filter = "הכל"

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

        self.lbl_name = wx.StaticText(self.panel, label="הראה לי קבצים ותהליכים חשודים שרצים במחשב")

        self.vbox.Add(self.lbl_name, 0, wx.CENTER | wx.TOP, 20)

        self.files_sizer = wx.BoxSizer(wx.VERTICAL)
        self.process_sizer = wx.BoxSizer(wx.VERTICAL)

        self.vbox.Add(self.files_sizer, 1, wx.EXPAND | wx.ALL, 5)
        self.vbox.Add(self.process_sizer, 1, wx.EXPAND | wx.ALL, 5)

        # כפתור הורדה
        self.btn_files = wx.Button(self.panel, label="הצג טבלת קבצים")
        self.btn_files.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.files_sizer.Add(self.btn_files, 0, wx.CENTER | wx.TOP, 20)

        self.btn_files.Bind(wx.EVT_BUTTON, self.on_files_click)

        # חיפוש לפי שם קובץ
        self.search_ctrl = wx.SearchCtrl(self.panel)
        self.search_ctrl.Hide()
        self.search_ctrl.Bind(wx.EVT_TEXT, self.on_search)

        self.files_sizer.Add(self.search_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # פילטר צבע לטבלת הקבצים
        self.color_choice = wx.Choice(
            self.panel,
            choices=["הכל", "אדום", "צהוב", "ירוק"]
        )
        self.color_choice.SetSelection(0)
        self.color_choice.Hide()
        self.color_choice.Bind(wx.EVT_CHOICE, self.on_color_filter)

        self.files_sizer.Add(self.color_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.btn_hide_files = wx.Button(self.panel, label="הסתר טבלת קבצים")
        self.btn_hide_files.Bind(wx.EVT_BUTTON, self.on_hide_files)
        self.files_sizer.Add(self.btn_hide_files, 0, wx.CENTER | wx.TOP, 10)
        self.btn_hide_files.Hide()

        self.btn_processes = wx.Button(self.panel,label="הצג טבלת תהליכים")
        self.btn_processes.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.process_sizer.Add(self.btn_processes,0,wx.CENTER | wx.TOP,10)

        self.btn_processes.Bind(wx.EVT_BUTTON,self.on_process_click)

        # חיפוש לפי שם תהליך
        self.search_process_ctrl = wx.SearchCtrl(self.panel)
        self.search_process_ctrl.Hide()
        self.search_process_ctrl.Bind(wx.EVT_TEXT, self.on_process_search)

        self.process_sizer.Add(self.search_process_ctrl, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        # פילטר צבע לטבלת התהליכים
        self.color_process_choice = wx.Choice(
            self.panel,
            choices=["הכל", "אדום", "צהוב", "ירוק"]
        )
        self.color_process_choice.SetSelection(0)
        self.color_process_choice.Hide()
        self.color_process_choice.Bind(wx.EVT_CHOICE, self.on_process_color_filter)

        self.process_sizer.Add(self.color_process_choice, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self.btn_hide_processes = wx.Button(self.panel, label="הסתר טבלת תהליכים")
        self.btn_hide_processes.Bind(wx.EVT_BUTTON, self.hide_process_table)
        self.process_sizer.Add(self.btn_hide_processes, 0, wx.CENTER | wx.TOP, 10)
        self.btn_hide_processes.Hide()

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

        #כפתור מחיקה של תהליך
        self.end_process_button = wx.Button(self.panel, label="סיים תהליך")
        self.end_process_button.SetBackgroundColour(wx.Colour(200, 0, 0))
        self.end_process_button.SetForegroundColour(wx.Colour(255, 255, 255))
        self.end_process_button.SetFont(font)
        self.end_process_button.SetMinSize((120, 45))  # גודל כפתור
        self.end_process_button.Hide()

        self.end_process_button.Bind(wx.EVT_BUTTON, self.end_process)
        self.vbox.Add(self.end_process_button, 0, wx.CENTER | wx.TOP, 10)

        # חיבור אירוע
        btn_disconnection.Bind(wx.EVT_BUTTON, lambda e: self.design.disconnection())

        self.vbox.Add(bottom_sizer, 0, wx.EXPAND)
        self.panel.SetSizer(self.vbox)

        return self.panel

    def request_new_alerts(self, event):
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

        print("FILES DATA:", data)

        if not data or data == "NO_ALERTS":
            return

        alerts_list = data.split("||")

        for alert in alerts_list:

            if not alert.strip():
                continue

            row = alert.split("|")
            print("FILE ROW:", row)

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
        if self.alerts_table:
            self.panel_scrolled_files.Show()
        else:
            self.show_alerts_table()

        self.search_ctrl.Show()
        self.color_choice.Show()

        self.btn_files.Hide()
        self.btn_hide_files.Show()

        self.lbl_name.Hide()
        self.user_status_message.Hide()

        self.panel.Layout()

    def on_process_click(self, event):
        if self.process_table:
            self.panel_scrolled_processes.Show()
        else:
            self.show_process_table()

        self.btn_processes.Hide()
        self.btn_hide_processes.Show()

        self.search_process_ctrl.Show()
        self.color_process_choice.Show()

        self.lbl_name.Hide()
        self.user_status_message.Hide()

        self.panel.Layout()

    def on_hide_files(self, event):
        if self.panel_scrolled_files:
            self.panel_scrolled_files.Hide()

        self.search_ctrl.Hide()
        self.color_choice.Hide()

        self.btn_hide_files.Hide()
        self.btn_files.Show()

        self.lbl_name.Show()
        self.user_status_message.Show()

        self.panel.Layout()

    def hide_process_table(self, event):
        if self.panel_scrolled_processes:
            self.panel_scrolled_processes.Hide()

        self.btn_hide_processes.Hide()
        self.btn_processes.Show()

        self.search_process_ctrl.Hide()
        self.color_process_choice.Hide()

        self.lbl_name.Show()
        self.user_status_message.Show()

        self.panel.Layout()

    # מזהה איזו שורה נלחצה,שומר את השורה ברשימה
    def on_row_click(self, event):
        index = event.GetIndex()
        self.selected_file_path = self.alerts_table.GetItem(index, 5).GetText()

        # לוקחים את ה-ID מהעמודה הראשונה בטבלה
        alert_id = self.alerts_table.GetItem(index, 1).GetText()

        #מביאים את כל המידע מהמילון
        self.selected_row_data = self.row_map[alert_id]

        self.delete_file_button.Show()
        self.panel.Layout()

    def on_process_row_click(self, event):
        index = event.GetIndex()
        self.selected_process_pid = self.process_table.GetItem(index, 4).GetText()

        alert_id = self.process_table.GetItem(index, 1).GetText()

        self.selected_row_data = self.process_row_map[alert_id]

        self.end_process_button.Show()
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

    def end_process(self, event):
        if not self.selected_process_pid:
            return

        dlg = wx.MessageDialog(
            self.panel,
            "האם אתה בטוח שתרצה לסיים את התהליך?",
            "אישור סיום",
            wx.YES_NO | wx.ICON_WARNING
        )

        result = dlg.ShowModal()
        dlg.Destroy()

        if result == wx.ID_YES:
            pid = self.selected_process_pid

            terminate_process(pid)

            row_data = self.selected_row_data
            self.design.send_and_receive_data("delete_process_alert", row_data, "null", "null")

            alert_id = row_data[0]

            for i, process in enumerate(self.process_data):
                if process[0] == alert_id:
                    self.process_data.pop(i)
                    break

            if alert_id in self.process_row_map:
                del self.process_row_map[alert_id]

            self.refresh_process_table()

        self.end_process_button.Hide()
        self.selected_process_pid = None
        self.panel.Layout()


    def show_alerts_table(self):
        if self.alerts_table:
            return

        self.panel_scrolled_files = wx.ScrolledWindow(self.panel, style=wx.VSCROLL)
        self.panel_scrolled_files.SetInitialSize((-1, 180))
        sizer_scrolled = wx.BoxSizer(wx.VERTICAL)
        self.panel_scrolled_files.SetSizer(sizer_scrolled)

        self.panel_scrolled_files.SetScrollRate(10, 10)

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

        self.files_sizer.Insert(1, self.panel_scrolled_files, 1, wx.EXPAND | wx.ALL, 10)

        self.refresh_table()
        self.panel.Layout()
        self.panel.Refresh()

    def show_process_table(self):
        if self.process_table:
            return

        self.panel_scrolled_processes = wx.ScrolledWindow(self.panel, style=wx.VSCROLL)
        self.panel_scrolled_processes.SetInitialSize((-1, 180))
        sizer_scrolled = wx.BoxSizer(wx.VERTICAL)
        self.panel_scrolled_processes.SetSizer(sizer_scrolled)

        self.panel_scrolled_processes.SetScrollRate(10, 10)

        self.process_table = wx.ListCtrl(
            self.panel_scrolled_processes,
            style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_HRULES | wx.LC_VRULES
        )

        self.process_table.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_process_row_click)

        columns = ["", "ID", "Timestamp", "Process", "PID", "Path", "Risk", "Reason", "Status"]
        widths = [40, 40, 170, 180, 80, 300, 50, 250, 120]

        for i, col in enumerate(columns):
            self.process_table.InsertColumn(i, col)
            self.process_table.SetColumnWidth(i, widths[i])

        sizer_scrolled.Add(self.process_table, 1, wx.EXPAND | wx.ALL, 5)

        self.process_sizer.Insert(1, self.panel_scrolled_processes, 1, wx.EXPAND | wx.ALL, 10)

        self.refresh_process_table()
        self.panel.Layout()
        self.panel.Refresh()

    def update_file_table(self, list_data):
        if not self.alerts_table:
            self.alerts_data.append(list_data)
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
            self.process_data.append(list_data)
            return

        if len(list_data) < 9:
            print("Bad row:", list_data)
            return

        self.process_data.append(list_data)

        alert_id = list_data[0]
        self.process_row_map[alert_id] = list_data

        self.refresh_process_table()

        if self.panel_scrolled_processes:
            self.panel_scrolled_processes.Layout()
            self.panel_scrolled_processes.FitInside()
            self.panel_scrolled_processes.Refresh()

    def on_search(self, event):
        self.current_search = self.search_ctrl.GetValue().lower()
        self.refresh_table()

    def on_process_search(self, event):
        self.process_current_search = self.search_process_ctrl.GetValue().lower()
        self.refresh_process_table()

    def on_color_filter(self, event):
        self.current_color_filter = self.color_choice.GetStringSelection()
        self.refresh_table()

    def on_process_color_filter(self, event):
        self.current_process_color_filter = self.color_process_choice.GetStringSelection()
        self.refresh_process_table()

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
        self.panel.Layout()

    def refresh_process_table(self):

        self.process_table.DeleteAllItems()

        row_number = 1

        for row_data in self.process_data:

            process_name = row_data[3].lower()

            # סינון לפי שם
            if self.process_current_search:
                if self.process_current_search not in process_name:
                    continue

            # סינון לפי צבע
            risk = int(row_data[6])

            if self.current_process_color_filter == "אדום":
                if risk < 50:
                    continue

            elif self.current_process_color_filter == "צהוב":
                if risk < 30 or risk >= 50:
                    continue

            elif self.current_process_color_filter == "ירוק":
                if risk >= 30:
                    continue

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
        self.panel.Layout()

        print("PROCESS TABLE EXISTS:", self.process_table is not None)
        print("ROWS:", len(self.process_data))
        print("VISIBLE ROWS:", self.process_table.GetItemCount())