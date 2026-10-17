"""P0: file:// path normalize for Playwright allowlist (esp. Windows)."""

from pathlib import Path

from case3.charts import file_url_to_path, paths_equal


def test_file_url_posix(tmp_path: Path):
    target = (tmp_path / "index.html").resolve()
    target.write_text("x", encoding="utf-8")
    uri = target.as_uri()
    assert file_url_to_path(uri) == target


def test_file_url_windows_style_path():
    # Chromium-style path after urlparse on Windows: /C:/Users/...
    p = file_url_to_path("file:///C:/Users/me/work/index.html")
    assert str(p) == str(Path(r"C:\Users\me\work\index.html")) or str(p).replace("\\", "/") == "C:/Users/me/work/index.html"


def test_paths_equal_windows_slash_variants(tmp_path: Path):
    f = (tmp_path / "chart.umd.min.js").resolve()
    f.write_text("js", encoding="utf-8")
    assert paths_equal(f, f)
    # Same path via as_uri roundtrip
    assert paths_equal(file_url_to_path(f.as_uri()), f)
