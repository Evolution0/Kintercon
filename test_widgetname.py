from hidden import customtkinter
from tkinter import *


def test(event):
    print(root.focus_get())
    if root.focus_get() == custom_entry:
        print("custom_entry")
    elif root.focus_get() == ttk_entry:
        print("ttk_entry")


root = customtkinter.CTk()

custom_entry = customtkinter.CTkEntry(root)   # CTkEntry
custom_entry.pack()

ttk_entry = Entry(root)                       # ttk_entry
ttk_entry.pack()

root.bind("<Return>", test)
root.mainloop()
