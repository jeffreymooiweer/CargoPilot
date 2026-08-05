from app.core.startup import purge_export_files


def test_all_generated_export_formats_are_removed(tmp_path):
    generated = [
        tmp_path / "shipment.pdf",
        tmp_path / "cards.zip",
        tmp_path / "legacy.xlsx",
        tmp_path / "render.tmp",
    ]
    for path in generated:
        path.write_bytes(b"sensitive")

    unrelated = tmp_path / "keep.txt"
    unrelated.write_text("keep", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    nested_pdf = nested / "keep.pdf"
    nested_pdf.write_bytes(b"nested")

    assert purge_export_files(tmp_path) == 4
    assert all(not path.exists() for path in generated)
    assert unrelated.exists()
    assert nested_pdf.exists()


def test_missing_export_directory_is_a_noop(tmp_path):
    missing = tmp_path / "does-not-exist"

    assert purge_export_files(missing) == 0


def test_cleanup_ignores_directories_with_export_suffixes(tmp_path):
    fake_pdf_directory = tmp_path / "not-a-file.pdf"
    fake_pdf_directory.mkdir()

    assert purge_export_files(tmp_path) == 0
    assert fake_pdf_directory.is_dir()
