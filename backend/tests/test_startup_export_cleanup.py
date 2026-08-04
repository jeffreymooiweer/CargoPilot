"""Regression tests for privacy cleanup after interrupted downloads."""
from pathlib import Path

from app.core.startup import purge_export_files


def test_all_temporary_export_formats_are_removed(tmp_path: Path):
    exports = tmp_path / "exports"
    exports.mkdir()
    for name in ("document.pdf", "cards.zip", "legacy.xlsx", "partial.tmp"):
        (exports / name).write_bytes(b"sensitive")

    removed = purge_export_files(exports)

    assert removed == 4
    assert list(exports.iterdir()) == []


def test_suffix_matching_is_case_insensitive(tmp_path: Path):
    exports = tmp_path / "exports"
    exports.mkdir()
    (exports / "DOCUMENT.PDF").write_bytes(b"sensitive")

    assert purge_export_files(exports) == 1
    assert not (exports / "DOCUMENT.PDF").exists()


def test_unknown_files_and_directories_are_left_untouched(tmp_path: Path):
    exports = tmp_path / "exports"
    nested = exports / "keep"
    nested.mkdir(parents=True)
    note = exports / "README.txt"
    note.write_text("operator note", encoding="utf-8")
    nested_pdf = nested / "nested.pdf"
    nested_pdf.write_bytes(b"not a direct export")

    removed = purge_export_files(exports)

    assert removed == 0
    assert note.exists()
    assert nested_pdf.exists()


def test_missing_export_directory_is_a_noop(tmp_path: Path):
    assert purge_export_files(tmp_path / "missing") == 0


def test_cleanup_continues_when_one_file_cannot_be_deleted(tmp_path: Path, monkeypatch):
    exports = tmp_path / "exports"
    exports.mkdir()
    blocked = exports / "blocked.pdf"
    removable = exports / "removable.zip"
    blocked.write_bytes(b"blocked")
    removable.write_bytes(b"remove")

    original_unlink = Path.unlink

    def selective_unlink(path: Path, *args, **kwargs):
        if path == blocked:
            raise PermissionError("blocked for test")
        return original_unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", selective_unlink)

    removed = purge_export_files(exports)

    assert removed == 1
    assert blocked.exists()
    assert not removable.exists()
