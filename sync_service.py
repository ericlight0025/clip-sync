"""
sync_service.py — Clip 檔案讀寫同步服務
Distributed under the MIT License. (See LICENSE file for details)
"""
import hashlib
import os
import re
from pathlib import Path

from config import BASE_DIR, DEFAULT_CLIPS

# 合法 clip 名稱：僅允許英文、數字、底線、連字號，防止路徑遍歷
_VALID_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


class SyncService:
    def __init__(self, base_dir: Path = BASE_DIR):
        self.base_dir = base_dir

    def ensure_base_dir(self):
        """確保 clips 目錄存在，若為空則建立預設檔案。"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        existing = list(self.base_dir.glob("*.md"))
        if not existing:
            for name, content in DEFAULT_CLIPS.items():
                (self.base_dir / name).write_text(content, encoding="utf-8")

    def list_clips(self) -> list[Path]:
        """回傳所有 .md 檔案，依名稱排序。"""
        self.ensure_base_dir()
        files = sorted(self.base_dir.glob("*.md"), key=lambda p: p.name.lower())
        if not files:
            default_file = self.base_dir / "default.md"
            default_file.write_text("", encoding="utf-8")
            files = [default_file]
        return files

    def latest_clip(self) -> Path | None:
        """回傳最近修改的 clip 檔案。"""
        files = self.list_clips()
        return max(files, key=lambda p: p.stat().st_mtime) if files else None

    def create_clip(self, name: str) -> Path:
        """建立新 clip，若已存在則拋出例外。"""
        name = name.strip().replace(".md", "")
        # 驗證名稱，拒絕路徑分隔符與 ".."，避免寫入 base_dir 之外
        if not _VALID_NAME.match(name):
            raise ValueError("名稱僅允許英文、數字、底線、連字號")
        file_path = self.base_dir / f"{name}.md"
        if file_path.exists():
            raise FileExistsError(f"{file_path.name} 已存在")
        file_path.write_text("", encoding="utf-8")
        return file_path

    def delete_clip(self, file_path: Path):
        """刪除 clip，若只剩一個則拒絕刪除。"""
        files = self.list_clips()
        if len(files) <= 1:
            raise RuntimeError("至少保留一個 .md 檔案")
        file_path.unlink()

    def read_clip(self, file_path: Path) -> str:
        """讀取 clip 內容，若不存在則建立空檔。"""
        if not file_path.exists():
            file_path.write_text("", encoding="utf-8")
        return file_path.read_text(encoding="utf-8")

    def write_clip(self, file_path: Path, value: str) -> float:
        """以 tmp 暫存檔安全寫入，回傳寫入後的 mtime。"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = file_path.with_suffix(file_path.suffix + ".tmp")
        tmp_file.write_text(value, encoding="utf-8")
        os.replace(tmp_file, file_path)
        return file_path.stat().st_mtime

    @staticmethod
    def hash_text(value: str) -> str:
        """回傳文字內容的雜湊值（僅用於變更偵測，非安全用途）。"""
        return hashlib.md5(
            value.encode("utf-8", errors="ignore"), usedforsecurity=False
        ).hexdigest()

    @staticmethod
    def mtime(file_path: Path) -> float:
        """回傳檔案的修改時間，不存在則回傳 0。"""
        return file_path.stat().st_mtime if file_path.exists() else 0
