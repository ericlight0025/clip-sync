"""資料保存與共享寫入回歸測試；僅操作 TemporaryDirectory。"""
import ast
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

import settings_manager
import sync_service
from sync_service import ClipConflictError, SyncService
from ui_dashboard import SharedPasteDashboard

SOURCE = Path(__file__).resolve().parents[1]


class RegressionTests(unittest.TestCase):
    """保留真實流程，使用替身隔離 Tk 桌面與網路。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.service = SyncService(self.base)

    def tearDown(self):
        self.tmp.cleanup()

    def dashboard(self, dirty=True):
        d = SharedPasteDashboard.__new__(SharedPasteDashboard)
        d.sync = self.service
        d.root = MagicMock()
        d.root.after.return_value = 'retry-job'
        d.current_file = self.base / 'old.md'
        d.current_file.write_text('original', encoding='utf-8')
        d.last_file_mtime = d.sync.mtime(d.current_file)
        d.last_text_hash = d.sync.hash_text('original')
        d.pending_write_job = 'save-job' if dirty else None
        d.highlight_job = None
        d.buffer = 'local-edit' if dirty else 'original'
        d.get_text = lambda: d.buffer
        d.set_text = lambda value: setattr(d, 'buffer', value)
        for name in ('set_status', 'render_bar', 'update_current_label', 'update_simple_label'):
            setattr(d, name, MagicMock())
        return d

    def test_poll_keeps_local_edit_and_save_preserves_remote(self):
        d = self.dashboard()
        original = d.current_file
        original.write_text('remote-edit', encoding='utf-8')
        d.load_from_file()
        self.assertEqual(d.buffer, 'local-edit')
        self.assertTrue(d.flush_pending_write())
        self.assertEqual(original.read_text(), 'remote-edit')
        self.assertIn('_conflict_', d.current_file.name)
        self.assertEqual(d.current_file.read_text(), 'local-edit')

    def test_clean_poll_detects_changes_even_with_unchanged_mtime(self):
        d = self.dashboard(dirty=False)
        old_time = d.last_file_mtime
        d.current_file.write_text('remote-edit', encoding='utf-8')
        os.utime(d.current_file, (old_time, old_time))
        d.load_from_file()
        self.assertEqual(d.buffer, 'remote-edit')

    def test_add_flushes_old_clip(self):
        d = self.dashboard()
        original = d.current_file
        d.ask_clip_name = lambda: 'new'
        d.add_clip()
        self.assertEqual(original.read_text(), 'local-edit')
        self.assertEqual(d.current_file.name, 'new.md')
        self.assertEqual(d.buffer, '')

    def test_add_is_blocked_on_failed_save(self):
        d = self.dashboard()
        d.ask_clip_name = lambda: 'new'
        with patch.object(self.service, 'write_clip', side_effect=PermissionError('offline')):
            d.add_clip()
        self.assertEqual(d.current_file.name, 'old.md')
        self.assertFalse((self.base / 'new.md').exists())
        self.assertEqual(d.buffer, 'local-edit')

    def test_close_flushes_before_destroy(self):
        d = self.dashboard()
        d.root.destroy.side_effect = lambda: self.assertEqual(d.current_file.read_text(), 'local-edit')
        d.on_close()
        d.root.destroy.assert_called_once()

    def test_startup_offline_edit_recovers_after_connection_returns(self):
        d = self.dashboard()
        d.current_file = None
        d.last_text_hash = ''
        with patch.object(self.service, 'save_conflict_copy', side_effect=OSError('offline')), \
             patch('ui_dashboard.messagebox.showwarning'):
            d.on_close()
        d.root.destroy.assert_not_called()
        self.assertEqual(d.buffer, 'local-edit')
        d.reload_clip_list()
        self.assertIn('recovered_conflict_', d.current_file.name)
        self.assertEqual(d.current_file.read_text(), 'local-edit')

    def test_close_failure_retains_window_and_retry(self):
        d = self.dashboard()
        with patch.object(self.service, 'write_clip', side_effect=PermissionError('offline')), \
             patch('ui_dashboard.messagebox.showwarning'):
            d.on_close()
        d.root.destroy.assert_not_called()
        self.assertEqual(d.buffer, 'local-edit')
        self.assertEqual(d.pending_write_job, 'retry-job')
        self.assertTrue(d.flush_pending_write())
        self.assertEqual(d.current_file.read_text(), 'local-edit')

    def test_switch_failure_keeps_original_and_eventually_saves(self):
        d = self.dashboard()
        original = d.current_file
        other = self.base / 'other.md'
        other.write_text('other')
        with patch.object(self.service, 'write_clip', side_effect=OSError('offline')):
            d.switch_clip(other)
        self.assertEqual(d.current_file, original)
        self.assertEqual(d.buffer, 'local-edit')
        self.assertTrue(d.flush_pending_write())
        self.assertEqual(original.read_text(), 'local-edit')

    def test_unreadable_target_does_not_change_active_clip(self):
        d = self.dashboard(dirty=False)
        original = d.current_file
        d.switch_clip(self.base / 'missing.md')
        self.assertEqual(d.current_file, original)
        self.assertEqual(d.buffer, 'original')

    def test_deleted_remote_preserves_local_in_conflict_copy(self):
        d = self.dashboard()
        original = d.current_file
        original.unlink()
        d.reload_clip_list()
        self.assertEqual(d.buffer, 'local-edit')
        self.assertTrue(d.flush_pending_write())
        self.assertFalse(original.exists())
        self.assertEqual(d.current_file.read_text(), 'local-edit')

    def test_invalid_utf8_target_does_not_change_active_clip(self):
        d = self.dashboard(dirty=False)
        target = self.base / 'invalid.md'
        target.write_bytes(b'\xff')
        d.switch_clip(target)
        self.assertEqual(d.current_file.name, 'old.md')
        self.assertEqual(d.buffer, 'original')

    def test_service_rejects_stale_version(self):
        target = self.base / 'clip.md'
        target.write_text('original')
        version = self.service.hash_text('original')
        self.service.write_clip(target, 'first', expected_hash=version)
        with self.assertRaises(ClipConflictError):
            self.service.write_clip(target, 'second', expected_hash=version)
        self.assertEqual(target.read_text(), 'first')

    def test_concurrent_writer_is_rejected_without_touching_first_temp(self):
        target = self.base / 'clip.md'
        target.write_text('original')
        reached_replace = threading.Event()
        release = threading.Event()
        errors = []
        replace = os.replace

        def delayed_replace(src, dst):
            reached_replace.set()
            if not release.wait(5):
                raise TimeoutError('測試等待超時')
            return replace(src, dst)

        def writer():
            try:
                self.service.write_clip(target, 'first')
            except Exception as exc:
                errors.append(exc)

        with patch.object(sync_service.os, 'replace', side_effect=delayed_replace):
            thread = threading.Thread(target=writer)
            thread.start()
            try:
                self.assertTrue(reached_replace.wait(5))
                with self.assertRaises(OSError):
                    SyncService(self.base).write_clip(target, 'second')
            finally:
                release.set()
                thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(target.read_text(), 'first')
        self.assertEqual(list(self.base.glob('*.lock')), [])
        self.assertEqual(list(self.base.glob('.*.tmp')), [])

    def test_failed_replace_keeps_original_and_cleans_temp(self):
        target = self.base / 'clip.md'
        target.write_text('original')
        with patch.object(sync_service.os, 'replace', side_effect=PermissionError('offline')):
            with self.assertRaises(PermissionError):
                self.service.write_clip(target, 'new')
        self.assertEqual(target.read_text(), 'original')
        self.assertEqual(list(self.base.glob('.*.tmp')), [])
        self.assertEqual(list(self.base.glob('*.lock')), [])

    def test_create_never_truncates_existing_clip(self):
        target = self.base / 'clip.md'
        target.write_text('important')
        with self.assertRaises(FileExistsError):
            self.service.create_clip('clip')
        self.assertEqual(target.read_text(), 'important')

    def test_read_does_not_recreate_deleted_clip(self):
        target = self.base / 'missing.md'
        with self.assertRaises(FileNotFoundError):
            self.service.read_clip(target)
        self.assertFalse(target.exists())

    def test_build_staging_imports_all_modules(self):
        script = (SOURCE / 'scripts/build_exe.bat').read_text()
        names = re.findall(r'copy "%SRC_DIR%([^"\n]+\.py)"', script)
        stage = self.base / 'stage'
        stage.mkdir()
        for name in names:
            shutil.copyfile(SOURCE / name, stage / name)
        proc = subprocess.run([sys.executable, '-E', '-c',
            'import main, ui_settings, settings_manager'], cwd=stage,
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_build_does_not_force_kill_or_delete_final_directory(self):
        script = (SOURCE / 'scripts/build_exe.bat').read_text().lower()
        self.assertNotIn('taskkill /f', script)
        self.assertNotIn('rmdir /s /q "%final_dir%"', script)

    def test_settings_atomic_failure_preserves_previous_file(self):
        target = self.base / 'settings.json'
        target.write_text('{"theme": "Light"}')
        with patch.object(settings_manager, '_SETTINGS_FILE', target), \
             patch.object(settings_manager.os, 'replace', side_effect=OSError('failed')):
            with self.assertRaises(OSError):
                settings_manager.save({'theme': 'VS Code Dark'})
        self.assertEqual(target.read_text(), '{"theme": "Light"}')
        self.assertEqual(list(self.base.glob('.settings.*.tmp')), [])

    def test_settings_save_round_trip(self):
        target = self.base / 'settings.json'
        with patch.object(settings_manager, '_SETTINGS_FILE', target):
            settings_manager.save({'theme': 'Light', 'base_dir': 'shared'})
            saved = settings_manager.load()
        self.assertEqual(saved['theme'], 'Light')
        self.assertEqual(saved['base_dir'], 'shared')
        self.assertEqual(list(self.base.glob('.settings.*.tmp')), [])

    def test_legacy_packaged_settings_remain_readable(self):
        target = self.base / 'settings.json'
        legacy = self.base / 'legacy.json'
        legacy.write_text('{"base_dir": "old-share"}')
        with patch.object(sys, 'frozen', True, create=True), \
             patch.object(settings_manager, '_SETTINGS_FILE', target), \
             patch.object(settings_manager, '_LEGACY_SETTINGS_FILE', legacy):
            settings = settings_manager.load()
            self.assertEqual(settings['base_dir'], 'old-share')
            settings_manager.save(settings)
            self.assertTrue(target.exists())
            self.assertEqual(settings_manager.load()['base_dir'], 'old-share')

    def test_close_button_uses_save_handler(self):
        tree = ast.parse((SOURCE / 'ui_dashboard.py').read_text())
        buttons = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                   and any(k.arg == 'text' and isinstance(k.value, ast.Constant)
                           and k.value.value == '✕' for k in node.keywords)]
        self.assertEqual(len(buttons), 1)
        command = next(k.value for k in buttons[0].keywords if k.arg == 'command')
        self.assertEqual(ast.unparse(command), 'self.on_close')


if __name__ == '__main__':
    unittest.main()
