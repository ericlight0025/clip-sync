"""
main.py — Shared Paste Dashboard 入口點
Distributed under the MIT License. (See LICENSE file for details)
"""
import tkinter as tk
from sync_service import SyncService
from ui_dashboard import SharedPasteDashboard


def main():
    root = tk.Tk()
    service = SyncService()
    SharedPasteDashboard(root, service)
    root.mainloop()


if __name__ == "__main__":
    main()
