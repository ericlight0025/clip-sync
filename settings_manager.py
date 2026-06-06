"""
settings_manager.py — 設定檔讀寫管理
將所有使用者可調整的參數（路徑、主題、計時器等）持久化至 settings.json。
Distributed under the MIT License. (See LICENSE file for details)
"""
import json
from pathlib import Path

# settings.json 儲存於程式所在目錄
_SETTINGS_FILE = Path(__file__).parent / "settings.json"

# =============================================================
# 預設值（程式第一次執行時使用）
# =============================================================
DEFAULTS: dict = {
    # ==============================================================================
    # §1. 路徑設定 (Path Settings)
    # ==============================================================================
    # 1.1 base_dir: Clips 儲存目錄
    "base_dir":   r"U:\paste\clips",
    # 編譯輸出路徑
    "build_root": r"C:\BuildOutput",

    # ==============================================================================
    # §2. 介面主題 (Theme Settings)
    # ==============================================================================
    # 2.1 theme: 目前啟用的主題名稱
    "theme": "VS Code Dark",

    # ==============================================================================
    # §3. 視窗外觀與行為 (Window Settings)
    # ==============================================================================
    # 3.1 window_geometry: 預設視窗位置與大小
    "window_geometry":    "860x520+100+100",
    # 3.2 window_min_w: 視窗最小寬度
    "window_min_w":       560,
    # 3.3 window_min_h: 視窗最小高度
    "window_min_h":       360,
    # 3.4 sidebar_width: 側邊欄寬度
    "sidebar_width":      150,
    # 3.5 alpha_focused: 聚焦時透明度
    "alpha_focused":      1.0,
    # 3.6 alpha_unfocused: 失焦時透明度
    "alpha_unfocused":    0.6,
    # 3.7 start_simple_mode: 啟動時是否預設進入簡潔模式
    "start_simple_mode":  True,

    # ==============================================================================
    # §4. 字型設定 (Font Settings)
    # ==============================================================================
    # 4.1 font_size: 編輯器預設字型大小
    "font_size":      11,
    # 4.2 font_code_name: 編輯器程式碼字型名稱
    "font_code_name": "Consolas",
    # 4.3 font_ui: UI 介面字型設定
    "font_ui":        ["Microsoft JhengHei UI", 9],
    # 4.4 font_bar: 側邊欄按鈕字型設定
    "font_bar":       ["Microsoft JhengHei UI", 10],

    # ==============================================================================
    # §5. 效能與計時器 (Performance & Timers)
    # ==============================================================================
    # 5.1 check_interval_ms: 輪詢外部檔案變更的間隔 (毫秒)
    "check_interval_ms":  700,
    # 5.2 write_debounce_ms: 編輯防抖延遲寫入時間 (毫秒)
    "write_debounce_ms":  500,
    # 5.3 highlight_delay_ms: 語法高亮延遲觸發時間 (毫秒)
    "highlight_delay_ms": 300,
    # 5.4 highlight_max_len: 語法高亮字元數上限 (超過不處理)
    "highlight_max_len":  200000,

    # ==============================================================================
    # §6. 多機同步設定 (Sync Settings)
    # ==============================================================================
    # 6.1 remote_hosts: 遠端主機名稱清單 (以逗號分隔，用於判定環境)
    "remote_hosts": "",
}


def load() -> dict:
    """載入 settings.json，若不存在或損毀則回傳預設值。"""
    if _SETTINGS_FILE.exists():
        try:
            data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            # 補齊缺失的 key（升級相容）
            for k, v in DEFAULTS.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return dict(DEFAULTS)


def save(data: dict) -> None:
    """將設定寫入 settings.json。"""
    _SETTINGS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get(key: str, fallback=None):
    """快速取得單一設定值。"""
    return load().get(key, fallback if fallback is not None else DEFAULTS.get(key))
