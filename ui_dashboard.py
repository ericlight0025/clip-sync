"""
ui_dashboard.py — Shared Paste Dashboard 主介面
新功能：Ctrl+滾輪縮放、多向拖曳調整大小（左/底/右下/左下）、全螢幕、主題即時切換、嵌入式設定面板。
所有 UI 魔法數字均引用 config.py。
Distributed under the MIT License. (See LICENSE file for details)
"""
import tkinter as tk
from tkinter import messagebox, ttk
import time
import re

import config
import settings_manager
from config import (
    WINDOW_TITLE, WINDOW_GEOMETRY, WINDOW_MIN_W, WINDOW_MIN_H,
    SIDEBAR_WIDTH, ALPHA_FOCUSED, ALPHA_UNFOCUSED,
    START_SIMPLE_MODE,
    CHECK_INTERVAL_MS, WRITE_DEBOUNCE_MS,
    HIGHLIGHT_DELAY_MS, HIGHLIGHT_MAX_LEN,
    DEFAULT_FONT_SIZE, MIN_FONT_SIZE, MAX_FONT_SIZE,
    FONT_UI, FONT_BAR, FONT_CODE_NAME,
    HOSTNAME_LABEL, THEMES, CURRENT_THEME,
    RESIZE_HANDLE_SIZE,
)
from sync_service import SyncService


class SharedPasteDashboard:
    def __init__(self, root: tk.Tk, sync_service: SyncService):
        self.root = root
        self.sync = sync_service

        # 主題狀態（使用實例色彩，支援即時切換）
        self._theme_name = CURRENT_THEME
        self._t          = dict(THEMES[self._theme_name])

        # 視窗設定
        self.root.title(f"{WINDOW_TITLE}{HOSTNAME_LABEL}")
        self.root.geometry(WINDOW_GEOMETRY)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", ALPHA_FOCUSED)
        self.root.configure(bg=self._t['BG'])
        self.root.overrideredirect(True)

        # 應用狀態
        self.current_file       = None
        self.last_text_hash     = ""
        self.last_file_mtime    = 0
        self.pending_write_job  = None
        self.highlight_job      = None
        self.updating_from_file = False
        self.font_size          = DEFAULT_FONT_SIZE
        self.simple_mode        = False
        self.auto_wrap          = False
        self._topmost           = True

        # 移動狀態
        self._move_x = 0
        self._move_y = 0

        # 調整大小狀態
        self._is_resizing    = False
        self._resize_dir     = 'br'
        self._resize_x       = 0
        self._resize_y       = 0
        self._resize_w       = 0
        self._resize_h       = 0
        self._resize_mouse_x = 0
        self._resize_mouse_y = 0

        # 全螢幕狀態
        self._is_maximized  = False
        self._prev_geometry = WINDOW_GEOMETRY

        self.build_ui()
        self.bind_events()
        self.safe_call(self.sync.ensure_base_dir)
        self.reload_clip_list()
        self.select_latest_clip()
        if START_SIMPLE_MODE:
            self.enter_simple_mode()
        self.root.after(CHECK_INTERVAL_MS, self.poll_file)

    # ----------------------------------------------------------
    # 主題顏色快捷
    # ----------------------------------------------------------

    def _c(self, key: str) -> str:
        """取得目前主題的顏色值。"""
        return self._t[key]

    # ----------------------------------------------------------
    # 事件綁定
    # ----------------------------------------------------------

    def bind_events(self):
        self.root.bind("<FocusIn>",       self.on_focus_in)
        self.root.bind("<FocusOut>",      self.on_focus_out)
        self.root.bind("<Map>",           self.on_window_map)
        self.root.bind("<Control-plus>",  lambda e: self.increase_font())
        self.root.bind("<Control-equal>", lambda e: self.increase_font())
        self.root.bind("<Control-minus>", lambda e: self.decrease_font())
        self.root.bind("<Escape>",        self.on_escape_pressed)
        # 雙擊標題列 → 全螢幕切換
        self.title_bar.bind("<Double-Button-1>",   self.toggle_maximize)
        self.title_label.bind("<Double-Button-1>", self.toggle_maximize)
        # Ctrl + 滾輪 → 縮放文字（如 VS Code）
        self.text.bind("<Control-MouseWheel>", self.on_ctrl_scroll)

    # ----------------------------------------------------------
    # UI 建構
    # ----------------------------------------------------------

    def build_ui(self):
        self._build_title_bar()
        self.main = tk.Frame(self.root, bg=self._c('BG'))
        self.main.pack(fill="both", expand=True)
        self._build_sidebar()
        self._build_content()
        self._build_resize_handles()

    def _build_title_bar(self):
        self.title_bar = tk.Frame(self.root, bg=self._c('TITLE_BG'), height=32)
        self.title_bar.pack(fill="x")
        self.title_bar.pack_propagate(False)

        self.title_label = tk.Label(
            self.title_bar,
            text=f"{WINDOW_TITLE}{HOSTNAME_LABEL}",
            bg=self._c('TITLE_BG'), fg=self._c('FG'), font=FONT_UI, anchor="w",
        )
        self.title_label.pack(side="left", fill="x", expand=True, padx=10)

        # 關閉
        self.btn_close = tk.Button(
            self.title_bar, text="✕", command=self.root.destroy,
            bg=self._c('TITLE_BG'), fg=self._c('FG'),
            activebackground="#c42b1c", activeforeground="#ffffff",
            relief="flat", width=4, font=(FONT_CODE_NAME, 12),
        )
        self.btn_close.pack(side="right")

        # 全螢幕
        self.btn_max = tk.Button(
            self.title_bar, text="□", command=self.toggle_maximize,
            bg=self._c('TITLE_BG'), fg=self._c('FG'),
            activebackground="#333333", activeforeground="#ffffff",
            relief="flat", width=4, font=(FONT_CODE_NAME, 11),
        )
        self.btn_max.pack(side="right")

        # 最小化
        self.btn_min = tk.Button(
            self.title_bar, text="─", command=self.minimize_window,
            bg=self._c('TITLE_BG'), fg=self._c('FG'),
            activebackground="#333333", activeforeground="#ffffff",
            relief="flat", width=4, font=(FONT_CODE_NAME, 11),
        )
        self.btn_min.pack(side="right")

        # 設定
        self.btn_settings = tk.Button(
            self.title_bar, text="⚙", command=self.open_settings,
            bg=self._c('TITLE_BG'), fg=self._c('FG'),
            activebackground="#333333", activeforeground="#ffffff",
            relief="flat", width=4, font=(FONT_CODE_NAME, 12),
        )
        self.btn_settings.pack(side="right")

        # 拖曳綁定
        for w in [self.title_bar, self.title_label]:
            w.bind("<ButtonPress-1>", self.start_move)
            w.bind("<B1-Motion>",     self.do_move)

    def _build_sidebar(self):
        self.sidebar = tk.Frame(self.main, bg=self._c('BAR_BG'), width=SIDEBAR_WIDTH)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self._sidebar_title = tk.Label(
            self.sidebar, text="CLIPS",
            bg=self._c('BAR_BG'), fg=self._c('MUTED_FG'),
            font=(FONT_CODE_NAME, 10, "bold"), anchor="w",
        )
        self._sidebar_title.pack(fill="x", padx=10, pady=(10, 6))

        self.clip_buttons_frame = tk.Frame(self.sidebar, bg=self._c('BAR_BG'))
        self.clip_buttons_frame.pack(fill="both", expand=True)

        self._tool_frame = tk.Frame(self.sidebar, bg=self._c('BAR_BG'))
        self._tool_frame.pack(fill="x", padx=8, pady=8)
        self.make_side_button(self._tool_frame, "+ 新增", self.add_clip).pack(fill="x", pady=(0, 4))
        self.make_side_button(self._tool_frame, "刪除",   self.delete_clip).pack(fill="x", pady=(0, 4))
        self.make_side_button(self._tool_frame, "重整",   self.reload_clip_list).pack(fill="x")

    def _build_content(self):
        self.content = tk.Frame(self.main, bg=self._c('BG'))
        self.content.pack(side="left", fill="both", expand=True)

        # 簡潔模式列
        self.simple_bar = tk.Frame(self.content, bg=self._c('BG'))
        self.simple_label = tk.Label(
            self.simple_bar, text="",
            bg=self._c('BG'), fg=self._c('MUTED_FG'),
            font=(FONT_CODE_NAME, 10, "bold"), anchor="w",
        )
        self.simple_label.pack(side="left", fill="x", expand=True, padx=8, pady=6)
        self.make_button(self.simple_bar, "完整模式", self.show_full_mode).pack(side="right", padx=8, pady=4)

        # 工具列
        self.top = tk.Frame(self.content, bg=self._c('BG'))
        self.top.pack(fill="x", padx=8, pady=(8, 4))
        self.current_label = tk.Label(
            self.top, text="",
            bg=self._c('BG'), fg=self._c('MUTED_FG'),
            font=(FONT_CODE_NAME, 10, "bold"), anchor="w",
        )
        self.current_label.pack(side="left", fill="x", expand=True)
        self.make_button(self.top, "複製",    self.copy_text).pack(side="right", padx=(4, 0))
        self.make_button(self.top, "清空",    self.clear_text).pack(side="right", padx=(4, 0))
        self.wrap_button = self.make_button(self.top, "換行：關", self.toggle_wrap)
        self.wrap_button.pack(side="right", padx=(4, 0))
        self.make_button(self.top, "置頂",     self.toggle_topmost).pack(side="right", padx=(4, 0))
        self.make_button(self.top, "簡潔模式", self.enter_simple_mode).pack(side="right", padx=(4, 0))
        self.make_button(self.top, "A+",       self.increase_font).pack(side="right", padx=(4, 0))
        self.make_button(self.top, "A-",       self.decrease_font).pack(side="right", padx=(4, 0))
        self.font_label = tk.Label(
            self.top, text=f"{self.font_size}px",
            bg=self._c('BG'), fg=self._c('MUTED_FG'),
            font=(FONT_CODE_NAME, 9), width=6,
        )
        self.font_label.pack(side="right", padx=(4, 0))

        # 編輯區
        self.editor_frame = tk.Frame(self.content, bg=self._c('BG'))
        self.editor_frame.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        self.text = tk.Text(
            self.editor_frame,
            wrap="none",
            font=(FONT_CODE_NAME, self.font_size),
            bg=self._c('TEXT_BG'), fg=self._c('TEXT_FG'),
            insertbackground=self._c('CURSOR'),
            selectbackground=self._c('SELECT_BG'), selectforeground="#ffffff",
            relief="flat", undo=True,
        )
        self.text.pack(side="left", fill="both", expand=True)
        self._apply_scrollbar_style()
        self.yscroll = ttk.Scrollbar(
            self.editor_frame,
            orient="vertical",
            command=self.text.yview,
            style="Themed.Vertical.TScrollbar",
        )
        self.yscroll.pack(side="right", fill="y")
        self.text.config(yscrollcommand=self.yscroll.set)
        self.text.bind("<<Modified>>", self.on_text_modified)
        self.setup_code_tags()
        self.apply_wrap_mode()

        # 狀態列
        self.bottom = tk.Frame(self.content, bg=self._c('BG'))
        self.bottom.pack(fill="x", padx=8, pady=(0, 8))
        self.status = tk.Label(
            self.bottom, text="就緒",
            bg=self._c('BG'), fg=self._c('MUTED_FG'),
            font=(FONT_CODE_NAME, 9), anchor="w",
        )
        self.status.pack(side="left", fill="x", expand=True)
        # 右側主題名稱標示
        self._theme_label = tk.Label(
            self.bottom, text=f"● {self._theme_name}",
            bg=self._c('BG'), fg=self._c('MUTED_FG'),
            font=(FONT_CODE_NAME, 9), anchor="e",
        )
        self._theme_label.pack(side="right")

    def _build_resize_handles(self):
        """建立四向拖曳調整大小的感應框。"""
        s = RESIZE_HANDLE_SIZE

        # 右下角
        self._grip_br = tk.Frame(self.root, bg=self._c('BAR_HOVER'), width=12, height=12, cursor="size_nw_se")
        self._grip_br.place(relx=1.0, rely=1.0, x=-2, y=-2, anchor="se")
        self._grip_br.bind("<ButtonPress-1>",   lambda e: self.start_resize(e, 'br'))
        self._grip_br.bind("<B1-Motion>",       self.do_resize)
        self._grip_br.bind("<ButtonRelease-1>", self.stop_resize)

        # 底部邊緣
        self._grip_b = tk.Frame(self.root, bg=self._c('BG'), cursor="size_ns")
        self._grip_b.place(relx=0.0, rely=1.0, x=12, y=-s, relwidth=1.0, width=-24, height=s, anchor="sw")
        self._grip_b.bind("<ButtonPress-1>",   lambda e: self.start_resize(e, 'b'))
        self._grip_b.bind("<B1-Motion>",       self.do_resize)
        self._grip_b.bind("<ButtonRelease-1>", self.stop_resize)

        # 左側邊緣
        self._grip_l = tk.Frame(self.root, bg=self._c('BG'), cursor="size_we")
        self._grip_l.place(relx=0.0, rely=0.0, x=0, y=32, width=s, relheight=1.0, height=-44, anchor="nw")
        self._grip_l.bind("<ButtonPress-1>",   lambda e: self.start_resize(e, 'l'))
        self._grip_l.bind("<B1-Motion>",       self.do_resize)
        self._grip_l.bind("<ButtonRelease-1>", self.stop_resize)

        # 左下角
        self._grip_bl = tk.Frame(self.root, bg=self._c('BAR_HOVER'), width=12, height=12, cursor="size_ne_sw")
        self._grip_bl.place(relx=0.0, rely=1.0, x=2, y=-2, anchor="sw")
        self._grip_bl.bind("<ButtonPress-1>",   lambda e: self.start_resize(e, 'bl'))
        self._grip_bl.bind("<B1-Motion>",       self.do_resize)
        self._grip_bl.bind("<ButtonRelease-1>", self.stop_resize)

    # ----------------------------------------------------------
    # 按鈕工廠
    # ----------------------------------------------------------

    def make_button(self, parent, text: str, command) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command,
            bg=self._c('BTN_BG'), fg=self._c('BTN_FG'),
            activebackground="#444444", activeforeground="#ffffff",
            relief="flat", padx=10, pady=3, font=FONT_UI,
        )

    def make_side_button(self, parent, text: str, command) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command,
            bg=self._c('BTN_BG'), fg=self._c('BTN_FG'),
            activebackground=self._c('BAR_HOVER'), activeforeground="#ffffff",
            relief="flat", padx=8, pady=4, font=FONT_UI,
        )

    # ----------------------------------------------------------
    # Scrollbar 樣式
    # ----------------------------------------------------------

    def _apply_scrollbar_style(self):
        """以 ttk.Style 設定 Scrollbar 顏色，讓它跟隨目前主題。"""
        t = self._t
        style = ttk.Style(self.root)
        style.theme_use('clam')  # clam 主題支援顏色自訂
        style.configure(
            "Themed.Vertical.TScrollbar",
            background=t['BAR_BG'],
            troughcolor=t['BG'],
            arrowcolor=t['MUTED_FG'],
            bordercolor=t['BG'],
            darkcolor=t['BAR_BG'],
            lightcolor=t['BAR_HOVER'],
            gripcount=0,
            relief="flat",
            arrowsize=12,
        )
        style.map(
            "Themed.Vertical.TScrollbar",
            background=[("active", t['BAR_HOVER']), ("!active", t['BAR_BG'])],
            arrowcolor=[("active", t['FG']), ("!active", t['MUTED_FG'])],
        )

    # ----------------------------------------------------------
    # 主題即時切換
    # ----------------------------------------------------------

    def apply_theme(self, theme_name: str):
        """即時套用主題到所有 widget。"""
        if theme_name not in THEMES:
            return
        self._theme_name = theme_name
        self._t = dict(THEMES[theme_name])
        t = self._t

        self.root.configure(bg=t['BG'])

        # 標題列
        self.title_bar.configure(bg=t['TITLE_BG'])
        self.title_label.configure(bg=t['TITLE_BG'], fg=t['FG'])
        for btn in [self.btn_close, self.btn_max, self.btn_min, self.btn_settings]:
            btn.configure(bg=t['TITLE_BG'], fg=t['FG'])

        # 主框架 / 側邊欄
        self.main.configure(bg=t['BG'])
        self.sidebar.configure(bg=t['BAR_BG'])
        self._sidebar_title.configure(bg=t['BAR_BG'], fg=t['MUTED_FG'])
        self.clip_buttons_frame.configure(bg=t['BAR_BG'])
        self._tool_frame.configure(bg=t['BAR_BG'])
        for w in self._tool_frame.winfo_children():
            if isinstance(w, tk.Button):
                w.configure(bg=t['BTN_BG'], fg=t['BTN_FG'], activebackground=t['BAR_HOVER'])

        # 內容區各 frame
        for frame in [self.content, self.simple_bar, self.top, self.editor_frame, self.bottom]:
            frame.configure(bg=t['BG'])
        self.simple_label.configure(bg=t['BG'], fg=t['MUTED_FG'])
        self.current_label.configure(bg=t['BG'], fg=t['MUTED_FG'])
        self.font_label.configure(bg=t['BG'], fg=t['MUTED_FG'])
        self.status.configure(bg=t['BG'], fg=t['MUTED_FG'])
        self._theme_label.configure(bg=t['BG'], fg=t['MUTED_FG'], text=f"● {theme_name}")

        # 工具列按鈕
        for frame in [self.simple_bar, self.top]:
            for w in frame.winfo_children():
                if isinstance(w, tk.Button):
                    w.configure(bg=t['BTN_BG'], fg=t['BTN_FG'])

        # 編輯器
        self.text.configure(
            bg=t['TEXT_BG'], fg=t['TEXT_FG'],
            insertbackground=t['CURSOR'],
            selectbackground=t['SELECT_BG'],
        )

        # 縮放 grip
        for grip in [self._grip_br, self._grip_bl]:
            grip.configure(bg=t['BAR_HOVER'])
        for grip in [self._grip_b, self._grip_l]:
            grip.configure(bg=t['BG'])

        # Clip 按鈕重繪
        try:
            self.render_bar(self.sync.list_clips())
        except Exception:
            pass

        # Scrollbar 跟著換色
        self._apply_scrollbar_style()

        # 同步更新設定面板主題
        if hasattr(self, "settings_panel") and self.settings_panel is not None:
            self.settings_panel.apply_theme(theme_name)

        # 儲存主題選擇
        s = settings_manager.load()
        s['theme'] = theme_name
        settings_manager.save(s)
        self.set_status(f"主題：{theme_name}")

    # ----------------------------------------------------------
    # 視窗焦點 / 移動
    # ----------------------------------------------------------

    def on_focus_in(self, event=None):
        self.root.attributes("-alpha", ALPHA_FOCUSED)

    def on_focus_out(self, event=None):
        self.root.attributes("-alpha", ALPHA_UNFOCUSED)

    def on_escape_pressed(self, event=None):
        if hasattr(self, "in_settings_mode") and self.in_settings_mode:
            self.close_settings()
        else:
            self.enter_simple_mode()

    def start_move(self, event):
        self._move_x = event.x
        self._move_y = event.y

    def do_move(self, event):
        if self._is_resizing or self._is_maximized:
            return
        x = self.root.winfo_x() + event.x - self._move_x
        y = self.root.winfo_y() + event.y - self._move_y
        self.root.geometry(f"+{x}+{y}")

    # ----------------------------------------------------------
    # 視窗調整大小（四向）
    # ----------------------------------------------------------

    def start_resize(self, event, direction: str = 'br'):
        if self._is_maximized:
            return
        self._is_resizing    = True
        self._resize_dir     = direction
        self._resize_x       = self.root.winfo_x()
        self._resize_y       = self.root.winfo_y()
        self._resize_w       = self.root.winfo_width()
        self._resize_h       = self.root.winfo_height()
        self._resize_mouse_x = event.x_root
        self._resize_mouse_y = event.y_root

    def do_resize(self, event):
        if not self._is_resizing:
            return
        dx = event.x_root - self._resize_mouse_x
        dy = event.y_root - self._resize_mouse_y
        d  = self._resize_dir
        x, y = self._resize_x, self._resize_y
        w, h = self._resize_w, self._resize_h

        if 'r' in d:
            w = max(WINDOW_MIN_W, self._resize_w + dx)
        if 'b' in d:
            h = max(WINDOW_MIN_H, self._resize_h + dy)
        if 'l' in d:
            new_w = max(WINDOW_MIN_W, self._resize_w - dx)
            x = self._resize_x + (self._resize_w - new_w)
            w = new_w

        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def stop_resize(self, event):
        self._is_resizing = False

    # ----------------------------------------------------------
    # 全螢幕切換
    # ----------------------------------------------------------

    def toggle_maximize(self, event=None):
        if self._is_maximized:
            self.root.geometry(self._prev_geometry)
            self._is_maximized = False
            self.btn_max.config(text="□")
            self.set_status("還原視窗")
        else:
            self._prev_geometry = self.root.geometry()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self.root.geometry(f"{sw}x{sh}+0+0")
            self._is_maximized = True
            self.btn_max.config(text="❐")
            self.set_status("全螢幕")

    # ----------------------------------------------------------
    # 最小化
    # ----------------------------------------------------------

    def minimize_window(self):
        self.root.overrideredirect(False)
        self.root.state('iconic')

    def on_window_map(self, event=None):
        if self.root.state() == 'normal':
            self.root.after(10, self._restore_overrideredirect)

    def _restore_overrideredirect(self):
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", self._topmost)
        self.root.lift()

    # ----------------------------------------------------------
    # Ctrl + 滾輪縮放（VS Code 風格）
    # ----------------------------------------------------------

    def on_ctrl_scroll(self, event):
        if event.delta > 0:
            self.increase_font()
        else:
            self.decrease_font()
        return "break"  # 防止預設滾動行為

    # ----------------------------------------------------------
    # 設定對話框
    # ----------------------------------------------------------

    def open_settings(self):
        self.flush_pending_write()
        from ui_settings import SettingsPanel

        if not hasattr(self, "settings_panel") or self.settings_panel is None:
            self.settings_frame = tk.Frame(self.main, bg=self._c('BG'))
            self.settings_panel = SettingsPanel(self.settings_frame, self)
            self.settings_panel.pack(fill="both", expand=True)

        if not hasattr(self, "in_settings_mode") or not self.in_settings_mode:
            self.pre_settings_simple_mode = self.simple_mode
            self.in_settings_mode = True

            # 隱藏主視窗其他元件
            self.sidebar.pack_forget()
            self.content.pack_forget()

            # 展開設定面板
            self.settings_frame.pack(side="left", fill="both", expand=True)

            # 同步載入最新設定至輸入框
            self.settings_panel._s = settings_manager.load()
            self.settings_panel.var_base_dir.set(self.settings_panel._s.get("base_dir", ""))
            self.settings_panel.var_build_root.set(self.settings_panel._s.get("build_root", ""))
            self.settings_panel.var_theme.set(self.settings_panel._s.get("theme", self._theme_name))
            self.settings_panel.var_alpha_unfocused.set(str(self.settings_panel._s.get("alpha_unfocused", 0.6)))
            self.settings_panel.var_start_simple.set(bool(self.settings_panel._s.get("start_simple_mode", True)))
            self.settings_panel.var_font_size.set(str(self.settings_panel._s.get("font_size", 11)))
            self.settings_panel.var_font_code.set(self.settings_panel._s.get("font_code_name", "Consolas"))
            self.settings_panel.var_check.set(str(self.settings_panel._s.get("check_interval_ms", 700)))
            self.settings_panel.var_write.set(str(self.settings_panel._s.get("write_debounce_ms", 500)))
            self.settings_panel.var_hl.set(str(self.settings_panel._s.get("highlight_delay_ms", 300)))
            self.settings_panel.var_hl_max.set(str(self.settings_panel._s.get("highlight_max_len", 200000)))
            self.settings_panel.var_remote.set(self.settings_panel._s.get("remote_hosts", ""))

            # 即時套用當前主題顏色
            self.settings_panel.apply_theme(self._theme_name)
            self.set_status("設定模式")

    def close_settings(self):
        if hasattr(self, "in_settings_mode") and self.in_settings_mode:
            self.in_settings_mode = False
            self.settings_frame.pack_forget()

            # 還原顯示模式
            if self.pre_settings_simple_mode:
                self.enter_simple_mode()
            else:
                self.show_full_mode()

    # ----------------------------------------------------------
    # Clip 清單管理
    # ----------------------------------------------------------

    def reload_clip_list(self):
        try:
            files = self.sync.list_clips()
            if self.current_file is None or not self.current_file.exists():
                self.current_file    = files[0]
                self.last_text_hash  = ""
                self.last_file_mtime = 0
                self.load_from_file(force=True)
            self.render_bar(files)
            self.update_current_label()
            self.set_status(f"已載入 {len(files)} 個 clip  {time.strftime('%H:%M:%S')}")
        except Exception as e:
            self.set_status(f"重整失敗：{e}")

    def select_latest_clip(self):
        try:
            latest_file = self.sync.latest_clip()
            if not latest_file:
                return
            self.current_file    = latest_file
            self.last_text_hash  = ""
            self.last_file_mtime = 0
            self.load_from_file(force=True)
            self.render_bar(self.sync.list_clips())
            self.update_current_label()
        except Exception as e:
            self.set_status(f"選取最新 .md 失敗：{e}")

    def render_bar(self, files):
        t = self._t
        for widget in self.clip_buttons_frame.winfo_children():
            widget.destroy()
        for file_path in files:
            is_active = self.current_file and file_path.name == self.current_file.name
            bg = t['BAR_ACTIVE'] if is_active else t['BAR_BG']
            btn = tk.Button(
                self.clip_buttons_frame,
                text=file_path.stem,
                command=lambda p=file_path: self.switch_clip(p),
                bg=bg, fg=t['FG'],
                activebackground=t['BAR_HOVER'], activeforeground="#ffffff",
                relief="flat", anchor="w", padx=12, pady=7, font=FONT_BAR,
            )
            btn.pack(fill="x", padx=6, pady=1)

    def switch_clip(self, file_path):
        if self.current_file == file_path:
            return
        self.flush_pending_write()
        self.current_file    = file_path
        self.last_text_hash  = ""
        self.last_file_mtime = 0
        self.load_from_file(force=True)
        self.reload_clip_list()
        self.update_simple_label()

    # ----------------------------------------------------------
    # 顯示模式切換
    # ----------------------------------------------------------

    def enter_simple_mode(self):
        self.flush_pending_write()
        self.simple_mode = True
        self.sidebar.pack_forget()
        if not self.content.winfo_ismapped():
            self.content.pack(side="left", fill="both", expand=True)
        self.top.pack_forget()
        self.bottom.pack_forget()
        if not self.simple_bar.winfo_ismapped():
            self.simple_bar.pack(fill="x", padx=8, pady=(8, 4), before=self.editor_frame)
        self.update_simple_label()
        self.set_status("簡潔模式")

    def show_full_mode(self):
        self.simple_mode = False
        self.simple_bar.pack_forget()
        if not self.content.winfo_ismapped():
            self.content.pack(side="left", fill="both", expand=True)
        if not self.sidebar.winfo_ismapped():
            self.sidebar.pack(side="left", fill="y", before=self.content)
        if not self.top.winfo_ismapped():
            self.top.pack(fill="x", padx=8, pady=(8, 4), before=self.editor_frame)
        if not self.bottom.winfo_ismapped():
            self.bottom.pack(fill="x", padx=8, pady=(0, 8))
        self.reload_clip_list()
        self.update_current_label()
        self.set_status("完整模式")

    def update_simple_label(self):
        self.simple_label.config(
            text=self.current_file.stem if self.current_file else "無 .md 檔案"
        )

    # ----------------------------------------------------------
    # 新增 / 刪除 Clip
    # ----------------------------------------------------------

    def ask_clip_name(self) -> str | None:
        t = self._t
        dialog = tk.Toplevel(self.root)
        dialog.title("新增 Clip")
        dialog.configure(bg=t['BG'])
        dialog.geometry("360x160+220+220")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.attributes("-topmost", True)
        dialog.attributes("-alpha", ALPHA_FOCUSED)
        dialog.lift()
        dialog.focus_force()

        result = {"value": None}

        tk.Label(
            dialog,
            text="輸入 .md 檔名（例如：sql_temp）",
            bg=t['BG'], fg=t['FG'], font=FONT_UI, anchor="w",
        ).pack(fill="x", padx=12, pady=(16, 6))

        entry = tk.Entry(
            dialog,
            bg=t['TEXT_BG'], fg=t['TEXT_FG'],
            insertbackground=t['CURSOR'],
            relief="flat", font=(FONT_CODE_NAME, 11),
        )
        entry.pack(fill="x", padx=12)
        entry.focus_set()

        btn_frame = tk.Frame(dialog, bg=t['BG'])
        btn_frame.pack(fill="x", padx=12, pady=16)

        def ok():
            result["value"] = entry.get().strip()
            dialog.destroy()
            self.root.attributes("-alpha", ALPHA_FOCUSED)

        def cancel():
            result["value"] = None
            dialog.destroy()
            self.root.attributes("-alpha", ALPHA_FOCUSED)

        self.make_button(btn_frame, "確定", ok).pack(side="right", padx=(4, 0))
        self.make_button(btn_frame, "取消", cancel).pack(side="right")
        dialog.bind("<Return>", lambda e: ok())
        dialog.bind("<Escape>", lambda e: cancel())
        self.root.wait_window(dialog)
        return result["value"]

    def add_clip(self):
        name = self.ask_clip_name()
        if not name:
            return
        name = name.strip().replace(".md", "")
        if not re.match(r"^[A-Za-z0-9_-]+$", name):
            messagebox.showwarning("名稱無效", "僅允許英文、數字、底線、連字號", parent=self.root)
            return
        try:
            self.current_file    = self.sync.create_clip(name)
            self.last_text_hash  = ""
            self.last_file_mtime = 0
            self.reload_clip_list()
            self.load_from_file(force=True)
            self.update_simple_label()
        except Exception as e:
            messagebox.showwarning("新增失敗", str(e), parent=self.root)

    def delete_clip(self):
        if not self.current_file:
            return
        if not messagebox.askyesno("確認刪除", f"確定刪除 {self.current_file.name}？", parent=self.root):
            return
        try:
            old = self.current_file
            self.sync.delete_clip(old)
            self.current_file = None
            self.reload_clip_list()
            self.set_status(f"已刪除 {old.name}")
            self.update_simple_label()
        except Exception as e:
            messagebox.showwarning("刪除失敗", str(e), parent=self.root)

    def update_current_label(self):
        self.current_label.config(
            text=self.current_file.stem if self.current_file else "無 .md 檔案"
        )
        self.update_simple_label()

    # ----------------------------------------------------------
    # Syntax Highlight
    # ----------------------------------------------------------

    def setup_code_tags(self):
        self.text.tag_configure("keyword",    foreground="#569cd6")
        self.text.tag_configure("string",     foreground="#ce9178")
        self.text.tag_configure("comment",    foreground="#6a9955")
        self.text.tag_configure("number",     foreground="#b5cea8")
        self.text.tag_configure("function",   foreground="#dcdcaa")
        self.text.tag_configure("md_heading", foreground="#4fc1ff")
        self.text.tag_configure("md_code",    foreground="#ce9178")
        self.text.tag_configure("md_bold",    foreground="#dcdcaa")

    def highlight_code(self):
        content = self.get_text()
        if len(content) > HIGHLIGHT_MAX_LEN:
            return
        tags = ("keyword", "string", "comment", "number", "function",
                "md_heading", "md_code", "md_bold")
        for tag in tags:
            self.text.tag_remove(tag, "1.0", "end")
        patterns = [
            ("md_heading", r"^#{1,6}\s.*$",               re.MULTILINE),
            ("md_code",    r"`[^`]+`",                     0),
            ("md_bold",    r"\*\*[^*]+\*\*",               0),
            ("comment",    r"#.*",                         0),
            ("string",     r"(['\"])(?:(?=(\\?))\2.)*?\1", 0),
            ("number",     r"\b\d+(\.\d+)?\b",             0),
            ("keyword",
             r"\b(def|class|import|from|as|if|elif|else|for|while|try|except|"
             r"finally|with|return|in|is|not|and|or|None|True|False|lambda|"
             r"pass|break|continue|raise|select|where|join|left|right|inner|"
             r"outer|group|order|by|having|insert|update|delete|merge|into|"
             r"values|case|when|then|end)\b",
             re.IGNORECASE),
            ("function",   r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=\()", 0),
        ]
        for tag, pattern, flags in patterns:
            for match in re.finditer(pattern, content, flags):
                self.text.tag_add(tag, f"1.0+{match.start()}c", f"1.0+{match.end()}c")

    def schedule_highlight(self):
        if self.highlight_job:
            self.root.after_cancel(self.highlight_job)
        self.highlight_job = self.root.after(HIGHLIGHT_DELAY_MS, self.highlight_code)

    # ----------------------------------------------------------
    # 文字操作
    # ----------------------------------------------------------

    def get_text(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set_text(self, value: str):
        self.updating_from_file = True
        self.text.delete("1.0", "end")
        self.text.insert("1.0", value)
        self.text.edit_modified(False)
        self.highlight_code()
        self.updating_from_file = False

    def on_text_modified(self, event=None):
        if self.updating_from_file:
            self.text.edit_modified(False)
            return
        if not self.text.edit_modified():
            return
        self.text.edit_modified(False)
        self.schedule_highlight()
        if self.pending_write_job:
            self.root.after_cancel(self.pending_write_job)
        self.pending_write_job = self.root.after(WRITE_DEBOUNCE_MS, self.write_to_file)

    def flush_pending_write(self):
        if self.pending_write_job:
            self.root.after_cancel(self.pending_write_job)
            self.pending_write_job = None
            self.write_to_file()

    def write_to_file(self):
        self.pending_write_job = None
        if not self.current_file:
            return
        value      = self.get_text()
        value_hash = self.sync.hash_text(value)
        if value_hash == self.last_text_hash:
            return
        try:
            self.last_file_mtime = self.sync.write_clip(self.current_file, value)
            self.last_text_hash  = value_hash
            self.set_status(f"已儲存 {self.current_file.name}  {time.strftime('%H:%M:%S')}")
            self.update_simple_label()
        except Exception as e:
            self.set_status(f"寫入失敗：{e}")

    def load_from_file(self, force: bool = False):
        if not self.current_file:
            return
        try:
            mtime = self.sync.mtime(self.current_file)
            if not force and mtime <= self.last_file_mtime:
                return
            value      = self.sync.read_clip(self.current_file)
            value_hash = self.sync.hash_text(value)
            if value_hash != self.last_text_hash:
                self.set_text(value)
                self.last_text_hash = value_hash
            self.last_file_mtime = self.sync.mtime(self.current_file)
            self.update_current_label()
            self.set_status(f"已讀取 {self.current_file.name}  {time.strftime('%H:%M:%S')}")
        except Exception as e:
            self.set_status(f"讀取失敗：{e}")

    def poll_file(self):
        self.load_from_file()
        self.root.after(CHECK_INTERVAL_MS, self.poll_file)

    # ----------------------------------------------------------
    # 工具列操作
    # ----------------------------------------------------------

    def copy_text(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.get_text())
        self.set_status("已複製到剪貼板")

    def clear_text(self):
        if messagebox.askyesno("確認清空", "確定清空目前的 .md 內容？", parent=self.root):
            self.set_text("")
            self.write_to_file()

    def toggle_topmost(self):
        self._topmost = not self._topmost
        self.root.attributes("-topmost", self._topmost)
        self.set_status("已置頂" if self._topmost else "已取消置頂")

    def apply_font_size(self):
        self.text.config(font=(FONT_CODE_NAME, self.font_size))
        self.font_label.config(text=f"{self.font_size}px")
        self.set_status(f"字體大小：{self.font_size}px")

    def apply_wrap_mode(self):
        self.text.config(wrap="word" if self.auto_wrap else "none")
        if hasattr(self, "wrap_button"):
            self.wrap_button.config(text=f"換行：{'開' if self.auto_wrap else '關'}")

    def toggle_wrap(self):
        self.auto_wrap = not self.auto_wrap
        self.apply_wrap_mode()

    def increase_font(self):
        if self.font_size < MAX_FONT_SIZE:
            self.font_size += 1
            self.apply_font_size()

    def decrease_font(self):
        if self.font_size > MIN_FONT_SIZE:
            self.font_size -= 1
            self.apply_font_size()

    # ----------------------------------------------------------
    # 工具方法
    # ----------------------------------------------------------

    def safe_call(self, fn):
        try:
            return fn()
        except Exception as e:
            self.set_status(str(e))
            return None

    def set_status(self, msg: str):
        if hasattr(self, "status"):
            self.status.config(text=msg)
