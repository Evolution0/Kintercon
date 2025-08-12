# Modified from: https://stackoverflow.com/a/56913005
import tkinter as tk
import re


def get_curr_screen_geometry():
    """
    Workaround to get the size of the current screen in a multi-screen setup.

    Returns:
        geometry (List): The standard Tk geometry string broken up into separate values.
            width, height, left, top
    """
    root = tk.Tk()
    root.update_idletasks()
    root.attributes('-fullscreen', True)
    root.state('iconic')
    geometry = root.winfo_geometry()
    root.destroy()
    pattern = re.compile(r'(\d+)x(\d+)\+(\d+)\+(\d+)+')
    resolution = pattern.match(geometry)
    geometry = [int(i) for i in resolution.groups()]
    return geometry
