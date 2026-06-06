"""
config.py — Shared Paste Dashboard 全域設定
所有路徑、UI 參數、計時器設定均從 settings.json 載入。
首次執行時自動使用預設值並建立 settings.json。
Distributed under the MIT License. (See LICENSE file for details)
"""
from pathlib import Path
import socket
import settings_manager as _sm

# =============================================================
# 載入使用者設定
# =============================================================
_s = _sm.load()

# ==============================================================================
# §1. 路徑設定 (Path Settings)
# ==============================================================================
# 1.1 base_dir: Clips 儲存目錄
BASE_DIR:   Path = Path(_s["base_dir"])
# 1.2 build_root: 建置輸出根目錄
BUILD_ROOT: Path = Path(_s["build_root"])

# 打包子目錄（相對 BUILD_ROOT，不開放 UI 修改，自動推算）
PKG_SRC_DIR = BUILD_ROOT / "_pkg_src"
OUT_DIR     = BUILD_ROOT / "dist"
BUILD_DIR   = BUILD_ROOT / "build"
SPEC_DIR    = BUILD_ROOT / "spec"
FINAL_DIR   = BUILD_ROOT / "SharedPasteDashboard"

# ==============================================================================
# §2. 介面主題 (Theme Settings) - 定義於下方 THEMES 區塊後載入
# ==============================================================================
# 2.1 theme: 目前啟用的主題名稱 (在後面載入並設為 CURRENT_THEME)

# Clip 預設檔案與內容 (作為展示案例)
DEFAULT_CLIPS = {
    "01_welcome.md": "# 歡迎使用 Shared Paste Dashboard\n\n這是一個極簡、跨平台的剪貼簿同步工具。\n\n## 功能特色\n\n- 🚀 **即時同步**：在多台電腦間無縫共享文字與程式碼。\n- 🎨 **多重主題**：內建 VS Code Dark、Monokai 等多款經典主題。\n- 📝 **語法高亮**：自動識別常見程式語言並上色。\n- 🪟 **簡潔模式**：提供極小化視窗，不干擾主工作區。\n- ⚙️ **高度客製**：可自訂字型、透明度、輪詢間隔等參數。\n\n請點擊左側清單切換不同案例！",
    "02_python_script.md": "# Python 爬蟲範例\n\nimport requests\nfrom bs4 import BeautifulSoup\n\ndef fetch_titles(url):\n    \"\"\"抓取網頁標題\"\"\"\n    res = requests.get(url)\n    soup = BeautifulSoup(res.text, 'html.parser')\n    return [h2.text for h2 in soup.find_all('h2')]\n\nif __name__ == '__main__':\n    titles = fetch_titles('https://news.ycombinator.com')\n    for t in titles:\n        print(f'- {t}')\n",
    "03_sql_query.md": "-- MySQL 查詢範例：取得近30日活躍用戶\n\nSELECT \n    u.user_id, \n    u.username, \n    COUNT(l.login_id) as login_count,\n    MAX(l.login_time) as last_login\nFROM \n    users u\nLEFT JOIN \n    login_logs l ON u.user_id = l.user_id\nWHERE \n    u.status = 'active'\n    AND l.login_time >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)\nGROUP BY \n    u.user_id, \n    u.username\nHAVING \n    login_count > 5\nORDER BY \n    last_login DESC;\n",
    "04_daily_memo.md": "# 📝 每日備忘錄\n\n## 待辦事項 (TODO)\n\n- [ ] 10:00 與 PM 討論新功能需求\n- [ ] 13:30 Code Review\n- [ ] 16:00 修正 Issue #1024 效能問題\n\n## 隨手記\n\n- 整理本週測試報告\n- 記得回覆客戶的 E-mail\n- 下班前提交週報\n",
}

# ==============================================================================
# §3. 視窗外觀與行為 (Window Settings)
# ==============================================================================
WINDOW_TITLE       = "Shared Paste Dashboard"
# 3.1 window_geometry: 預設視窗位置與大小
WINDOW_GEOMETRY    = _s["window_geometry"]
# 3.2 window_min_w: 視窗最小寬度
WINDOW_MIN_W       = int(_s["window_min_w"])
# 3.3 window_min_h: 視窗最小高度
WINDOW_MIN_H       = int(_s["window_min_h"])
# 3.4 sidebar_width: 側邊欄寬度
SIDEBAR_WIDTH      = int(_s["sidebar_width"])
# 3.5 alpha_focused: 聚焦時透明度
ALPHA_FOCUSED      = float(_s["alpha_focused"])
# 3.6 alpha_unfocused: 失焦時透明度
ALPHA_UNFOCUSED    = float(_s["alpha_unfocused"])
# 3.7 start_simple_mode: 啟動時是否預設進入簡潔模式
START_SIMPLE_MODE  = bool(_s["start_simple_mode"])

DIALOG_GEOMETRY    = "360x160+220+220"
RESIZE_HANDLE_SIZE = 6

# ==============================================================================
# §4. 字型設定 (Font Settings)
# ==============================================================================
# 4.1 font_size: 編輯器預設字型大小
DEFAULT_FONT_SIZE = int(_s["font_size"])
MIN_FONT_SIZE     = 8
MAX_FONT_SIZE     = 28
# 4.2 font_code_name: 編輯器程式碼字型名稱
FONT_CODE_NAME = _s["font_code_name"]
# 4.3 font_ui: UI 介面字型設定
FONT_UI        = tuple(_s["font_ui"])
# 4.4 font_bar: 側邊欄按鈕字型設定
FONT_BAR       = tuple(_s["font_bar"])

# ==============================================================================
# §5. 效能與計時器 (Performance & Timers)
# ==============================================================================
# 5.1 check_interval_ms: 輪詢外部檔案變更的間隔 (毫秒)
CHECK_INTERVAL_MS  = int(_s["check_interval_ms"])
# 5.2 write_debounce_ms: 編輯防抖延遲寫入時間 (毫秒)
WRITE_DEBOUNCE_MS  = int(_s["write_debounce_ms"])
# 5.3 highlight_delay_ms: 語法高亮延遲觸發時間 (毫秒)
HIGHLIGHT_DELAY_MS = int(_s["highlight_delay_ms"])
# 5.4 highlight_max_len: 語法高亮字元數上限 (超過不處理)
HIGHLIGHT_MAX_LEN  = int(_s["highlight_max_len"])

# ==============================================================================
# §6. 多機同步設定 (Sync Settings)
# ==============================================================================
# 6.1 remote_hosts: 遠端主機名稱清單 (以逗號分隔，用於判定環境)
_remote_raw  = _s.get("remote_hosts", "")
REMOTE_HOSTS: set[str] = {
    h.strip().upper() for h in _remote_raw.split(",") if h.strip()
}
HOSTNAME       = socket.gethostname().upper()
HOSTNAME_LABEL = f" [{HOSTNAME}]"
ENV_NAME  = "REMOTE" if HOSTNAME in REMOTE_HOSTS else "LOCAL"


def clip_display_name(name: str) -> str:
    """回傳附加 hostname 的顯示名稱。"""
    return f"{name}{HOSTNAME_LABEL}"


# =============================================================
# 主題定義（所有可用主題）
# =============================================================
THEMES: dict[str, dict] = {
    "VS Code Dark": {
        "BG":         "#1e1e1e",
        "TITLE_BG":   "#111111",
        "BAR_BG":     "#202020",
        "BAR_ACTIVE": "#37373d",
        "BAR_HOVER":  "#2a2d2e",
        "FG":         "#d4d4d4",
        "MUTED_FG":   "#9cdcfe",
        "BTN_BG":     "#333333",
        "BTN_FG":     "#ffffff",
        "TEXT_BG":    "#1e1e1e",
        "TEXT_FG":    "#d4d4d4",
        "CURSOR":     "#ffffff",
        "SELECT_BG":  "#264f78",
    },
    "PowerShell": {
        "BG":         "#012456",
        "TITLE_BG":   "#001b40",
        "BAR_BG":     "#001f4d",
        "BAR_ACTIVE": "#063b78",
        "BAR_HOVER":  "#0b3a70",
        "FG":         "#ffffff",
        "MUTED_FG":   "#c7e6ff",
        "BTN_BG":     "#063b78",
        "BTN_FG":     "#ffffff",
        "TEXT_BG":    "#012456",
        "TEXT_FG":    "#ffffff",
        "CURSOR":     "#ffffff",
        "SELECT_BG":  "#1f5f99",
    },
    "Monokai": {
        "BG":         "#272822",
        "TITLE_BG":   "#1a1a15",
        "BAR_BG":     "#2d2e27",
        "BAR_ACTIVE": "#3e3d32",
        "BAR_HOVER":  "#3a3a2e",
        "FG":         "#f8f8f2",
        "MUTED_FG":   "#a6e22e",
        "BTN_BG":     "#3e3d32",
        "BTN_FG":     "#f8f8f2",
        "TEXT_BG":    "#272822",
        "TEXT_FG":    "#f8f8f2",
        "CURSOR":     "#f8f8f2",
        "SELECT_BG":  "#49483e",
    },
    "One Dark": {
        "BG":         "#282c34",
        "TITLE_BG":   "#1e2127",
        "BAR_BG":     "#21252b",
        "BAR_ACTIVE": "#2c313a",
        "BAR_HOVER":  "#2c313c",
        "FG":         "#abb2bf",
        "MUTED_FG":   "#61afef",
        "BTN_BG":     "#2c313a",
        "BTN_FG":     "#abb2bf",
        "TEXT_BG":    "#282c34",
        "TEXT_FG":    "#abb2bf",
        "CURSOR":     "#528bff",
        "SELECT_BG":  "#3e4451",
    },
    "Solarized Dark": {
        "BG":         "#002b36",
        "TITLE_BG":   "#00212b",
        "BAR_BG":     "#073642",
        "BAR_ACTIVE": "#0d4a5a",
        "BAR_HOVER":  "#0a4050",
        "FG":         "#839496",
        "MUTED_FG":   "#2aa198",
        "BTN_BG":     "#073642",
        "BTN_FG":     "#93a1a1",
        "TEXT_BG":    "#002b36",
        "TEXT_FG":    "#839496",
        "CURSOR":     "#268bd2",
        "SELECT_BG":  "#0d4a5a",
    },
    "Light": {
        "BG":         "#f5f5f5",
        "TITLE_BG":   "#e8e8e8",
        "BAR_BG":     "#ececec",
        "BAR_ACTIVE": "#dcdcdc",
        "BAR_HOVER":  "#e2e2e2",
        "FG":         "#333333",
        "MUTED_FG":   "#0066cc",
        "BTN_BG":     "#dcdcdc",
        "BTN_FG":     "#333333",
        "TEXT_BG":    "#ffffff",
        "TEXT_FG":    "#1a1a1a",
        "CURSOR":     "#000000",
        "SELECT_BG":  "#bad7ff",
    },
}

# 目前啟用主題名稱
_theme_name = _s.get("theme", "VS Code Dark")
if _theme_name not in THEMES:
    _theme_name = "VS Code Dark"
CURRENT_THEME = _theme_name

# 展開主題顏色為模組層級常數（供舊版引用相容）
_t     = THEMES[CURRENT_THEME]
BG         = _t["BG"]
TITLE_BG   = _t["TITLE_BG"]
BAR_BG     = _t["BAR_BG"]
BAR_ACTIVE = _t["BAR_ACTIVE"]
BAR_HOVER  = _t["BAR_HOVER"]
FG         = _t["FG"]
MUTED_FG   = _t["MUTED_FG"]
BTN_BG     = _t["BTN_BG"]
BTN_FG     = _t["BTN_FG"]
TEXT_BG    = _t["TEXT_BG"]
TEXT_FG    = _t["TEXT_FG"]
CURSOR     = _t["CURSOR"]
SELECT_BG  = _t["SELECT_BG"]
