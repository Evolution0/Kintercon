#!/usr/bin/env python3
import ctypes
from queue import Queue
from tkinter import StringVar, IntVar, END, INSERT, W

from customtkinter import *
from PIL import Image
from mctools import RCONClient
from paramiko import SSHClient

import util

# Constants
GWL_STYLE = -16
GWLP_HWNDPARENT = -8
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000

# Defining functions
GetWindowLongPtrW = ctypes.windll.user32.GetWindowLongPtrW
SetWindowLongPtrW = ctypes.windll.user32.SetWindowLongPtrW


def get_handle(root) -> int:
    root.update_idletasks()
    # This gets the window's parent same as `ctypes.windll.user32.GetParent`
    return GetWindowLongPtrW(root.winfo_id(), GWLP_HWNDPARENT)

# TODO: Add OS checks to toggle specific features (windll taskbar icon stuff)
# TODO: Optional SSH support for live console log.
# TODO: Test on vanilla server and/or figure out why certain commands fail via Kintercon and not the terminal when
# TODO: connecting to a Cardboard server. (Possibly an issue with Bukkit, Spigot, Paper, etc)
# TODO: In a clean vanilla or Fabric server the command works fine though help returns nothing in server log.

version = "0.1.0"

# TODO: Replace everything but my CTk code with MCTools RCONClient
# Set the maximum number of recent commands to be displayed.
MAX_QUEUE_SIZE = 50


class KinterconException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

# TODO: Store last N commands, allow arrow up/down to navigate them from the command input.
# TODO: Toggleable side-frame for running server log via SSH.


class Kintercon(CTk):
    def __init__(self):
        super().__init__()
        self.title(f"Kintercon v{version}")
        self.iconbitmap("cmd-terminal-icon-light.ico")
        self.window_height = 500
        self.window_width = 500
        self.center_window(self)
        self.resizable(False, False)

        # self.strip_wm_styling(self)
        kintercon_appid = u'evolution0.kintercon.0-1-0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(kintercon_appid)

        self.connect_icon = CTkImage(dark_image=Image.open("electric-plugin-icon-light.png"),
                                     light_image=Image.open("electric-plugin-icon.png"))

        # Main vars
        self.current_command = StringVar()
        self.current_theme = StringVar(value="blue")
        self.connected = False
        # submenu vars
        self.host = StringVar(value="localhost")
        self.port = IntVar(value=25575)
        self.password = StringVar()
        self.username = StringVar()
        self.drag_id = ''

        set_appearance_mode("system")
        set_default_color_theme(self.current_theme.get())

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)
        self.grid_columnconfigure(0, weight=1)

        # Tab container for additional RCON terminals/SSH, etc
        self.tabs = CTkTabview(self)

        self.tabs.add("RCON")
        self.tabs.add("SSH")

        self.tabs_nav_pos = StringVar(value="RCON")
        self.tabs_nav = CTkSegmentedButton(self, values=["RCON", "SSH"], variable=self.tabs_nav_pos,
                                           command=lambda t: self.tabs_nav_callback())

        self.output_field = CTkTextbox(self)
        self.input_field = CTkEntry(self, placeholder_text="Enter command...")
        self.settings = CTkButton(self, image=self.connect_icon, text="", border_spacing=0, border_width=0, width=32,
                                  command=self.connect_menu)

        self.tabs_nav.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="nsew")
        self.output_field.grid(row=1, column=0, columnspan=2, padx=10, pady=(10, 0),  sticky="nsew")
        self.input_field.grid(row=2, column=0, padx=10, pady=10,  sticky="nsew")
        self.settings.grid(row=2, column=1, padx=(0, 10), pady=10, sticky="nsew")

        self.input_field.bind('<Return>', self.multi_bind)

        self.command_queue = Queue(MAX_QUEUE_SIZE)

        self.print_text(program_text="Awaiting connection...")
        self.output_field.configure(state='disabled')

        self.connect_window_active = False

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        # TODO: Once more than one connection is allowed, close all of them.
        self.rcon_connection.stop()
        print("Closing all connections...")

    @staticmethod
    def center_window(window):
        screen_resolution = util.get_curr_screen_geometry()
        center_h = (screen_resolution[0] // 2) - (window.window_width // 2)
        center_v = (screen_resolution[1] // 2) - (window.window_height // 2)
        window.geometry(f"{window.window_width}x{window.window_height}+{center_h}+{center_v}")

    def anchor_window(self, window):
        """Anchor Tkinter window relative to another Tkinter window"""
        # TODO: Add support to update this live while its parent is moving (True anchoring)
        # TODO: Add support later for centering a window in its parent (Modals)
        screen_resolution = util.get_curr_screen_geometry()
        parent_window_position = self.geometry().split('x')
        parent_window_info = {
            "width": int(parent_window_position[0]),
            "height": int(parent_window_position[1].split('+')[0]),
            "x": int(parent_window_position[1].split('+')[1]),
            "y": int(parent_window_position[1].split('+')[2]),
        }

        if parent_window_info['x'] + parent_window_info['width'] + window.window_width > screen_resolution[0]:
            window.anchor_direction = "W"
            horizontal_offset = parent_window_info['x'] - window.window_width
        else:
            window.anchor_direction = "E"
            horizontal_offset = parent_window_info['width'] + parent_window_info['x']

        vertical_offset = parent_window_info['y']
        window.geometry(f"{window.window_width}x{window.window_height}+{horizontal_offset}+{vertical_offset}")

    def dragging(self, event):
        """https://stackoverflow.com/questions/45183914/tkinter-detecting-a-window-drag-event"""
        if event.widget is self:  # do nothing if the event is triggered by one of root's children
            if self.drag_id == '':
                # action on drag start
                pass
            else:
                # cancel scheduled call to stop_drag
                self.after_cancel(self.drag_id)
            # schedule stop_drag
            self.drag_id = self.after(10, self.stop_drag)

    def stop_drag(self):
        """https://stackoverflow.com/questions/45183914/tkinter-detecting-a-window-drag-event"""
        self.anchor_window(self.connect_window)
        self.drag_id = ''

    @staticmethod
    def strip_wm_styling(window):
        # Strip WM styling
        hwnd: int = get_handle(window)
        style: int = GetWindowLongPtrW(hwnd, GWL_STYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME)
        SetWindowLongPtrW(hwnd, GWL_STYLE, style)

    def tabs_nav_callback(self):
        self.print_text(program_text=f"{self.tabs_nav_pos.get()} awaiting command...")

    def connect_menu(self):
        # TODO: Prevent spawning an endless amount of these windows.
        if self.connect_window_active:
            self.unbind_and_delete()
        self.connect_window_active = True
        self.connect_window = CTkToplevel(self)
        self.connect_window.window_width = 240
        self.connect_window.window_height = 160
        self.connect_window.title("Connect")

        self.disconnect_command = self.terminate_rcon_connection
        self.connect_command = self.initiate_rcon_connection

        offset = 0
        if self.tabs_nav_pos.get() == "SSH":
            # Shift all widgets down one row so username input makes sense
            offset = 1
            # Add 20px so that the extra row doesn't squish everything
            self.connect_window.window_height += 20
            self.disconnect_command = self.terminate_ssh_connection
            self.connect_command = self.initiate_ssh_connection

        self.anchor_window(self.connect_window)
        self.connect_window.resizable(False, False)
        self.connect_window.iconbitmap("electric-plugin-icon-light.ico")

        # Didn't look as good as expected, left just in case.
        # self.strip_wm_styling(self.connect_window)

        self.connect_window.grid_rowconfigure(0, weight=1)
        self.connect_window.grid_rowconfigure(1, weight=1)
        self.connect_window.grid_rowconfigure(2, weight=1)
        self.connect_window.grid_rowconfigure(3, weight=1)
        if self.tabs_nav_pos.get() == "SSH":
            # Add a row for our username input
            self.connect_window.grid_rowconfigure(4, weight=1)
        self.connect_window.grid_columnconfigure(0, weight=1)
        self.connect_window.grid_columnconfigure(1, weight=1)

        self.host_label = CTkLabel(self.connect_window, text="HOST", anchor=W)
        self.host_input = CTkEntry(self.connect_window, textvariable=self.host)

        self.port_label = CTkLabel(self.connect_window, text="PORT", anchor=W)
        self.port_input = CTkEntry(self.connect_window, textvariable=self.port)

        if self.tabs_nav_pos.get() == "SSH":
            self.username_label = CTkLabel(self.connect_window, text="USER", anchor=W)
            self.username_input = CTkEntry(self.connect_window, textvariable=self.username)
            self.username_label.grid(row=2, column=0, padx=10, pady=(10, 0), sticky="nsew")
            self.username_input.grid(row=2, column=1, padx=5, pady=(10, 0), sticky="nsew")

        self.password_label = CTkLabel(self.connect_window, text="PASS", anchor=W)
        self.password_input = CTkEntry(self.connect_window, show="*", textvariable=self.password)

        self.connect_button = CTkButton(self.connect_window, text="Connect", command=self.connect_command)
        self.disconnect_button = CTkButton(self.connect_window, text="Disconnect", command=self.disconnect_command)

        self.host_label.grid(row=0, column=0, padx=10, pady=(10, 0),  sticky="nsew")
        self.host_input.grid(row=0, column=1, padx=5, pady=(10, 0), sticky="nsew")

        self.port_label.grid(row=1, column=0, padx=10, pady=(10, 0), sticky="nsew")
        self.port_input.grid(row=1, column=1, padx=5, pady=(10, 0), sticky="nsew")

        self.password_label.grid(row=2+offset, column=0, padx=10, pady=(10, 0), sticky="nsew")
        self.password_input.grid(row=2+offset, column=1, padx=5, pady=(10, 0), sticky="nsew")

        self.connect_button.grid(row=3+offset, column=0, padx=(10, 5), pady=(10, 10), sticky="nsew")
        self.disconnect_button.grid(row=3+offset, column=1, padx=(5, 10), pady=(10, 10), sticky="nsew")

        # TODO: Replace when an .invoke() method is added.
        self.password_input.bind('<Return>', command=self.connect_button._clicked)

        if self.connected:
            self.connect_button.configure(state="disabled")
            self.disconnect_button.configure(state="normal")
        else:
            self.connect_button.configure(state="normal")
            self.disconnect_button.configure(state="disabled")

        self.bind('<Configure>', self.dragging)
        self.connect_window.protocol('WM_DELETE_WINDOW', self.unbind_and_delete)

    def unbind_and_delete(self):
        self.unbind('<Configure>')
        self.connect_window.destroy()

    def terminate_ssh_connection(self):
        pass

    def initiate_ssh_connection(self):
        self.ssh_connection = SSHClient()
        self.ssh_connection.load_system_host_keys()
        # TODO: When SSH tab open, adding additional input fields and such to the connect window.
        self.ssh_connection.connect(self.host.get(), self.port.get(), self.username.get(), self.password.get())

    def terminate_rcon_connection(self):
        self.rcon_connection.stop()
        self.print_text(f"Disconnected from {self.host.get()}:{self.port.get()}...")
        self.connect_button.configure(state="normal")
        self.disconnect_button.configure(state="disabled")

    def initiate_rcon_connection(self):
        self.rcon_connection = RCONClient(self.host.get(), self.port.get())
        if self.rcon_connection.login(self.password.get()):
            try:
                self.print_text(f"Connected to {self.host.get()}:{self.port.get()}...")
                self.connected = True
                self.connect_button.configure(state="disabled")
                self.disconnect_button.configure(state="normal")
            except ConnectionRefusedError:
                print("The server refused the connection!")
            except ConnectionError as error:
                print(error)

    def multi_bind(self, event):
        self.send_command()
        self.print_text()

    def send_command(self):
        command_text = self.input_field.get()
        try:
            self.rcon_connection.command(command_text)
        except (ConnectionResetError, ConnectionAbortedError):
            print("Server connection terminated, perhaps it crashed or was stopped...")

    def add_to_queue(self, command):
        if self.command_queue.full():
            self.command_queue.get()
            self.command_queue.put(command)
        else:
            self.command_queue.put(command)

    def print_text(self, program_text=None):
        # TODO: Either figure out how to scroll command_log.textbox or wait for ScrolledText to be implemented in CTk.
        self.output_field.configure(state='normal')
        if program_text is None:
            input_text = self.input_field.get()
        else:
            input_text = program_text

        input_text = f"{input_text}\n"

        self.add_to_queue(input_text)

        self.input_field.delete(0, END)
        self.output_field.delete('1.0', END)

        for command in list(self.command_queue.queue):
            self.output_field.insert(INSERT, text=f"> {command}")
        self.output_field.configure(state='disabled')


if __name__ == "__main__":
    app = Kintercon()
    app.mainloop()
