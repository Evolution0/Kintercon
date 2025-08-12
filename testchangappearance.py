from hidden.customtkinter import *
from tkinter import StringVar
import util


class App(CTk):
    # Set defaults
    set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
    set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

    appearance_modes = ["Light", "Dark", "System"]

    def __init__(self):
        super().__init__()

        self.WIDTH = 780
        self.HEIGHT = 520

        self.drag_id = ''

        self.title("CustomTkinter complex_example.py")
        self.geometry(f"{self.WIDTH}x{self.HEIGHT}")

        # Create vars for appearance
        self.current_appearance = StringVar(value="System")
        self.current_theme = StringVar(value="blue")

        self.optionmenu_1 = CTkOptionMenu(self, values=self.appearance_modes, command=self.change_appearance_mode,
                                          variable=self.current_appearance)
        self.optionmenu_1.grid(row=10, column=0, pady=10, padx=20, sticky="w")

        self.center_window(self)
        self.login = self.LoginModal(self)

    @staticmethod
    def change_appearance_mode(new_appearance_mode):
        set_appearance_mode(new_appearance_mode)

    def unbind_and_delete(self):
        self.unbind('<Configure>')
        self.login.destroy()

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
        self.anchor_window(self.login)
        # Force focus to the login page, otherwise it can get stuck behind its parent on drag.
        self.login.focus_force()
        self.drag_id = ''

    def anchor_window(self, window):
        """Anchor Tkinter window relative to another Tkinter window"""
        parent_window_position = self.geometry().split('x')
        parent_window_info = {
            "width": int(parent_window_position[0]),
            "height": int(parent_window_position[1].split('+')[0]),
            "x": int(parent_window_position[1].split('+')[1]),
            "y": int(parent_window_position[1].split('+')[2]),
        }

        vertical_offset = parent_window_info['y']
        window.geometry(f"{self.WIDTH}x{self.HEIGHT}+{int(parent_window_info['x'])+8}+{int(vertical_offset)+31}")

    @staticmethod
    def center_window(window):
        screen_resolution = util.get_curr_screen_geometry()
        center_h = (screen_resolution[0] // 2) - (window.WIDTH // 2)
        center_v = (screen_resolution[1] // 2) - (window.HEIGHT // 2)
        window.geometry(f"{window.WIDTH}x{window.HEIGHT}+{center_h}+{center_v}")

    class LoginModal(CTkToplevel):
        def __init__(self, parent):
            super().__init__()
            self.title("Login")
            parent_geometry = parent.geometry().split("+")
            self.geometry(f"{parent.WIDTH}x{parent.HEIGHT}+{int(parent_geometry[1])+8}+{int(parent_geometry[2])+31}")

            # Shutdown resizing or dragging then anchor login over main window.
            self.resizable(False, False)
            self.overrideredirect(True)
            parent.anchor_window(self)
            parent.bind('<Configure>', parent.dragging)
            # Need to unbind before deleting the modal otherwise you will be error spammed by dragging()
            parent.login.protocol('WM_DELETE_WINDOW', parent.unbind_and_delete)

            appearance_menu = CTkOptionMenu(self, values=parent.appearance_modes, command=parent.change_appearance_mode,
                                            variable=parent.current_appearance)
            appearance_menu.grid(row=0, column=0, pady=10, padx=20, sticky="nsew")


if __name__ == "__main__":
    app = App()
    app.mainloop()
