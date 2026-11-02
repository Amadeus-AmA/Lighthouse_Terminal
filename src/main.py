import os
import sys
import tkinter as tk

from gui_app import LighthouseConsoleApp


def _icon_path():
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        for cand in (os.path.join(base, "assets", "lighthouse.ico"),
                     os.path.join(base, "_internal", "assets", "lighthouse.ico"),
                     os.path.join(base, "lighthouse.ico")):
            if os.path.exists(cand):
                return cand
        return ""
    cand = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "assets", "lighthouse.ico")
    return cand if os.path.exists(cand) else ""


def main():
    root = tk.Tk()
    icon = _icon_path()
    if icon:
        try:
            root.iconbitmap(default=icon)
            root.iconbitmap(icon)
        except tk.TclError:
            pass
    LighthouseConsoleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
