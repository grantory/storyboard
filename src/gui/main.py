from __future__ import annotations

import os
import sys
import customtkinter as ctk
from dotenv import load_dotenv

# Allow running from src/gui directory as `python main.py`
THIS_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.gui.app import MaestroApp


def main() -> None:
    # Load environment from project root .env before creating the app
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = MaestroApp()
    app.mainloop()


if __name__ == "__main__":
    main()


