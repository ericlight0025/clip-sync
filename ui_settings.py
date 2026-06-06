"""
ui_settings.py — 設定面板
提供所有可設定參數的 UI 介面：路徑、主題、計時器、視窗、字型、遠端主機。
此面板嵌入於主視窗中，而非以獨立視窗彈出。
Distributed under the MIT License. (See LICENSE file for details)
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import config
import settings_manager


class SettingsPanel(tk.Frame):
    def __init__(self, parent: tk.Widget, dashboard):
        super().__init__(parent, bg=dashboard._c('BG'))
        self.dashboard = dashboard
        self._s        = settings_manager.load()
        self._t        = dashboard._t

        self._build()

    # ----------------------------------------------------------
    # 元件輔助方法
    # ----------------------------------------------------------

    def _label(self, parent, text: str, row: int, col: int = 0):
        lbl = tk.Label(
            parent, text=text,
            bg=self._t['BG'], fg=self._t['FG'],
            font=config.FONT_UI, anchor="w",
        )
        lbl.grid(row=row, column=col, sticky="w", padx=(0, 8), pady=3)
        return lbl

    def _entry(self, parent, var: tk.StringVar, row: int, col: int = 1, width: int = 28):
        e = tk.Entry(
            parent, textvariable=var, width=width,
            bg=self._t['TEXT_BG'], fg=self._t['TEXT_FG'],
            insertbackground=self._t['CURSOR'],
            relief="flat", font=(config.FONT_CODE_NAME, 10),
        )
        e.grid(row=row, column=col, sticky="ew", pady=3)
        return e

    def _browse_btn(self, parent, var: tk.StringVar, row: int):
        def browse():
            path = filedialog.askdirectory(initialdir=var.get() or "C:\\")
            if path:
                var.set(path)
        btn = tk.Button(
            parent, text="📂", command=browse,
            bg=self._t['BTN_BG'], fg=self._t['BTN_FG'],
            activebackground=self._t['BAR_HOVER'], activeforeground="#ffffff",
            relief="flat", padx=6, pady=2, font=config.FONT_UI,
        )
        btn.grid(row=row, column=2, padx=(4, 0), pady=3)
        return btn

    def _section(self, parent, text: str, row: int):
        lbl = tk.Label(
            parent, text=f"  {text}",
            bg=self._t['BAR_ACTIVE'], fg=self._t['MUTED_FG'],
            font=(config.FONT_CODE_NAME, 9, "bold"), anchor="w",
        )
        lbl.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(10, 3), ipady=3)
        lbl.is_header = True
        return lbl

    # ----------------------------------------------------------
    # UI 建構
    # ----------------------------------------------------------

    def _build(self):
        t = self._t
        s = self._s

        # 可捲動的主內容區
        self.canvas = tk.Canvas(self, bg=t['BG'], highlightthickness=0)
        self.scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style="Themed.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.scroll.set)
        self.scroll.pack(side="right", fill="y")
        self.canvas.pack(side="top", fill="both", expand=True)

        self.outer = tk.Frame(self.canvas, bg=t['BG'])
        canvas_win = self.canvas.create_window((0, 0), window=self.outer, anchor="nw")

        def on_configure(e):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self.canvas.itemconfig(canvas_win, width=self.canvas.winfo_width())
        self.outer.bind("<Configure>", on_configure)
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(canvas_win, width=e.width))

        def _on_mousewheel(e):
            try:
                self.canvas.yview_scroll(-1 * (e.delta // 120), "units")
            except Exception:
                pass
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))
        def _on_destroy(e):
            try:
                self.canvas.unbind_all("<MouseWheel>")
            except Exception:
                pass
        self.bind("<Destroy>", _on_destroy)

        self.inner = tk.Frame(self.outer, bg=t['BG'])
        self.inner.pack(fill="both", expand=True, padx=16, pady=8)
        self.inner.columnconfigure(1, weight=1)

        row = 0

        # ── §1. 路徑設定 ──────────────────────────────
        self._section(self.inner, "📁  §1. 路徑設定 (Path Settings)", row); row += 1

        self.var_base_dir   = tk.StringVar(value=s.get("base_dir", ""))
        self.var_build_root = tk.StringVar(value=s.get("build_root", ""))

        self._label(self.inner, "Clips 目錄", row)
        self._entry(self.inner, self.var_base_dir, row)
        self._browse_btn(self.inner, self.var_base_dir, row); row += 1

        self._label(self.inner, "建置輸出目錄", row)
        self._entry(self.inner, self.var_build_root, row)
        self._browse_btn(self.inner, self.var_build_root, row); row += 1

        # ── §2. 主題 ──────────────────────────────────
        self._section(self.inner, "🎨  §2. 介面主題 (Theme Settings)", row); row += 1

        self.var_theme = tk.StringVar(value=s.get("theme", config.CURRENT_THEME))
        theme_frame = tk.Frame(self.inner, bg=t['BG'])
        theme_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=4)
        self._theme_buttons: dict[str, tk.Button] = {}
        for name in config.THEMES:
            btn = tk.Button(
                theme_frame, text=name,
                command=lambda n=name: self._select_theme(n),
                bg=t['BAR_ACTIVE'] if name == self.var_theme.get() else t['BTN_BG'],
                fg=t['BTN_FG'],
                activebackground=t['BAR_HOVER'], activeforeground="#ffffff",
                relief="flat", padx=8, pady=5, font=config.FONT_UI,
            )
            btn.pack(side="left", padx=(0, 4), pady=2)
            btn.theme_name = name
            self._theme_buttons[name] = btn
        row += 1

        # ── §3. 視窗設定 ──────────────────────────────
        self._section(self.inner, "🪟  §3. 視窗設定 (Window Settings)", row); row += 1

        self.var_alpha_unfocused = tk.StringVar(value=str(s.get("alpha_unfocused", 0.6)))
        self.var_start_simple    = tk.BooleanVar(value=bool(s.get("start_simple_mode", True)))

        self._label(self.inner, "失焦透明度 (0–1)", row)
        self._entry(self.inner, self.var_alpha_unfocused, row, width=8); row += 1

        chk = tk.Checkbutton(
            self.inner, text="啟動時進入簡潔模式",
            variable=self.var_start_simple,
            bg=t['BG'], fg=t['FG'],
            selectcolor=t['TEXT_BG'],
            activebackground=t['BG'], activeforeground=t['FG'],
            font=config.FONT_UI,
        )
        chk.grid(row=row, column=0, columnspan=3, sticky="w", pady=3); row += 1

        # ── §4. 字型 ──────────────────────────────────
        self._section(self.inner, "✏  §4. 字型設定 (Font Settings)", row); row += 1

        self.var_font_size = tk.StringVar(value=str(s.get("font_size", 11)))
        self.var_font_code = tk.StringVar(value=s.get("font_code_name", "Consolas"))

        self._label(self.inner, "預設字號",   row); self._entry(self.inner, self.var_font_size, row, width=8);  row += 1
        self._label(self.inner, "程式碼字型", row); self._entry(self.inner, self.var_font_code, row, width=20); row += 1

        # ── §5. 計時器 ────────────────────────────────
        self._section(self.inner, "⏱  §5. 效能與計時器 (Performance & Timers)", row); row += 1

        self.var_check  = tk.StringVar(value=str(s.get("check_interval_ms",  700)))
        self.var_write  = tk.StringVar(value=str(s.get("write_debounce_ms",  500)))
        self.var_hl     = tk.StringVar(value=str(s.get("highlight_delay_ms", 300)))
        self.var_hl_max = tk.StringVar(value=str(s.get("highlight_max_len",  200000)))

        self._label(self.inner, "輪詢間隔 (毫秒)",   row); self._entry(self.inner, self.var_check,  row, width=10); row += 1
        self._label(self.inner, "寫檔延遲 (毫秒)",   row); self._entry(self.inner, self.var_write,  row, width=10); row += 1
        self._label(self.inner, "Highlight 延遲 (毫秒)", row); self._entry(self.inner, self.var_hl,     row, width=10); row += 1
        self._label(self.inner, "Highlight 字元上限", row); self._entry(self.inner, self.var_hl_max, row, width=10); row += 1

        # ── §6. 遠端主機 ──────────────────────────────
        self._section(self.inner, "🖥  §6. 多機同步設定 (Sync Settings)", row); row += 1

        self.var_remote = tk.StringVar(value=s.get("remote_hosts", ""))
        self._label(self.inner, "遠端主機清單 (逗號分隔)", row)
        self._entry(self.inner, self.var_remote, row, width=28); row += 1

        # ── 底部按鈕 ──────────────────────────────
        self.btn_bar = tk.Frame(self, bg=t['BAR_BG'])
        self.btn_bar.pack(fill="x", side="bottom")
        self.btn_bar.is_btn_bar = True

        btn_save = tk.Button(
            self.btn_bar, text="✔  儲存並套用",
            command=self._save,
            bg=t['BAR_ACTIVE'], fg=t['BTN_FG'],
            activebackground=t['BAR_HOVER'], activeforeground="#ffffff",
            relief="flat", padx=14, pady=6, font=config.FONT_UI,
        )
        btn_save.pack(side="right", padx=8, pady=8)
        btn_save.is_save = True

        btn_back = tk.Button(
            self.btn_bar, text="← 返回編輯器",
            command=self.dashboard.close_settings,
            bg=t['BTN_BG'], fg=t['BTN_FG'],
            activebackground=t['BAR_HOVER'], activeforeground="#ffffff",
            relief="flat", padx=14, pady=6, font=config.FONT_UI,
        )
        btn_back.pack(side="right", pady=8)

        # 綁定 ESC 鍵返回
        self.bind("<Escape>", lambda e: self.dashboard.close_settings())

    # ----------------------------------------------------------
    # 主題預覽與套用
    # ----------------------------------------------------------

    def _select_theme(self, name: str):
        self.var_theme.set(name)
        if self.dashboard:
            self.dashboard.apply_theme(name)

    def apply_theme(self, theme_name: str):
        """遞迴更新面板內所有元件的主題顏色。"""
        if theme_name not in config.THEMES:
            return
        self._t = dict(config.THEMES[theme_name])
        t = self._t
        self._apply_theme_to_widget(self, t)

    def _apply_theme_to_widget(self, w, t):
        typename = w.winfo_class()
        if typename == "Label":
            if hasattr(w, "is_header") and w.is_header:
                w.configure(bg=t['BAR_ACTIVE'], fg=t['MUTED_FG'])
            else:
                w.configure(bg=t['BG'], fg=t['FG'])
        elif typename == "Entry":
            w.configure(bg=t['TEXT_BG'], fg=t['TEXT_FG'], insertbackground=t['CURSOR'])
        elif typename == "Button":
            if hasattr(w, "theme_name"):
                w.configure(
                    bg=t['BAR_ACTIVE'] if w.theme_name == self.var_theme.get() else t['BTN_BG'],
                    fg=t['BTN_FG'],
                    activebackground=t['BAR_HOVER']
                )
            elif hasattr(w, "is_save") and w.is_save:
                w.configure(bg=t['BAR_ACTIVE'], fg=t['BTN_FG'], activebackground=t['BAR_HOVER'])
            else:
                w.configure(bg=t['BTN_BG'], fg=t['BTN_FG'], activebackground=t['BAR_HOVER'])
        elif typename == "Frame":
            if hasattr(w, "is_btn_bar") and w.is_btn_bar:
                w.configure(bg=t['BAR_BG'])
            else:
                w.configure(bg=t['BG'])
        elif typename == "Checkbutton":
            w.configure(bg=t['BG'], fg=t['FG'], selectcolor=t['TEXT_BG'], activebackground=t['BG'], activeforeground=t['FG'])
        elif typename == "Canvas":
            w.configure(bg=t['BG'])

        for child in w.winfo_children():
            self._apply_theme_to_widget(child, t)

    # ----------------------------------------------------------
    # 儲存
    # ----------------------------------------------------------

    def _save(self):
        try:
            s = settings_manager.load()
            s["base_dir"]           = self.var_base_dir.get().strip()
            s["build_root"]         = self.var_build_root.get().strip()
            s["theme"]              = self.var_theme.get()
            s["check_interval_ms"]  = int(self.var_check.get())
            s["write_debounce_ms"]  = int(self.var_write.get())
            s["highlight_delay_ms"] = int(self.var_hl.get())
            s["highlight_max_len"]  = int(self.var_hl_max.get())
            s["alpha_unfocused"]    = float(self.var_alpha_unfocused.get())
            s["start_simple_mode"]  = bool(self.var_start_simple.get())
            s["font_size"]          = int(self.var_font_size.get())
            s["font_code_name"]     = self.var_font_code.get().strip()
            s["remote_hosts"]       = self.var_remote.get().strip()
            settings_manager.save(s)

            # 即時套用
            if self.dashboard:
                self.dashboard.apply_theme(s["theme"])
                self.dashboard.font_size = s["font_size"]
                self.dashboard.apply_font_size()

            messagebox.showinfo(
                "儲存成功",
                "✔ 設定已儲存。\n主題與字型立即生效。\n路徑與計時器需重新啟動程式後生效。",
                parent=self.dashboard.root,
            )
            self.dashboard.close_settings()

        except ValueError as e:
            messagebox.showerror("輸入錯誤", f"數字欄位格式不正確：{e}", parent=self.dashboard.root)
        except Exception as e:
            messagebox.showerror("錯誤", str(e), parent=self.dashboard.root)
