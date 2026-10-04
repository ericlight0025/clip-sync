"""
sync_service.py — Clip 檔案讀寫同步服務
Distributed under the MIT License. (See LICENSE file for details)
"""
import hashlib
import os
import re
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

from config import BASE_DIR, DEFAULT_CLIPS

# 合法 clip 名稱：僅允許英文、數字、底線、連字號，防止路徑遍歷
_VALID_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


class ClipConflictError(RuntimeError):
    """檔案內容已被其他使用者更新，拒絕覆寫。"""


class SyncService:
    def __init__(self, base_dir: Path = BASE_DIR):
        self.base_dir = Path(base_dir)

    @contextmanager
    def _write_lock(self, file_path: Path):
        """以共享目錄上的排他鎖序列化寫入；不等待或強制移除他人的鎖。"""
        lock_path = file_path.with_name(file_path.name + '.lock')
        try:
            descriptor = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise OSError(f'{file_path.name} 正在由另一個程式寫入，請稍後重試') from exc
        os.close(descriptor)
        try:
            yield
        finally:
            lock_path.unlink()

    def ensure_base_dir(self):
        """確保 clips 目錄存在，若為空則建立預設檔案。"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        existing = list(self.base_dir.glob("*.md"))
        if not existing:
            for name, content in DEFAULT_CLIPS.items():
                try:
                    with (self.base_dir / name).open('x', encoding='utf-8') as stream:
                        stream.write(content)
                except FileExistsError:
                    pass  # 另一個程式已完成初始化，保留其內容。

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
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with self._write_lock(file_path):
            with file_path.open('x', encoding='utf-8'):
                pass
        return file_path

    def delete_clip(self, file_path: Path):
        """刪除 clip，若只剩一個則拒絕刪除。"""
        files = self.list_clips()
        if len(files) <= 1:
            raise RuntimeError("至少保留一個 .md 檔案")
        with self._write_lock(file_path):
            file_path.unlink()

    def read_clip(self, file_path: Path) -> str:
        """讀取內容；檔案遭外部刪除時不擅自建立或覆寫。"""
        return file_path.read_text(encoding="utf-8")

    def write_clip(self, file_path: Path, value: str, expected_hash: str | None = None) -> float:
        """排他鎖內核對版本，以同目錄唯一暫存檔原子替換，回傳 mtime。"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        with self._write_lock(file_path):
            if expected_hash is not None:
                try:
                    actual_hash = self.hash_text(self.read_clip(file_path))
                except FileNotFoundError:
                    actual_hash = None
                if actual_hash != expected_hash:
                    raise ClipConflictError(f'{file_path.name} 已在外部修改或刪除')
            tmp_file = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                        dir=file_path.parent, prefix='.' + file_path.name + '.',
                        suffix='.tmp', delete=False) as stream:
                    tmp_file = Path(stream.name)
                    stream.write(value)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(tmp_file, file_path)
                return file_path.stat().st_mtime
            finally:
                if tmp_file is not None:
                    tmp_file.unlink(missing_ok=True)

    def save_conflict_copy(self, file_path: Path, value: str) -> Path:
        """另存本機編輯為可見的衝突副本，保留遠端原檔。"""
        name = f'{file_path.stem}_conflict_{uuid.uuid4().hex}'
        target = self.create_clip(name)
        self.write_clip(target, value, expected_hash=self.hash_text(''))
        return target

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
