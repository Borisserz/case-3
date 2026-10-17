import pytest

from case3.kandinsky import assert_safe_image_url


def test_block_localhost():
    with pytest.raises(RuntimeError, match="blocked"):
        assert_safe_image_url("http://127.0.0.1/x.png")


def test_block_file_scheme():
    with pytest.raises(RuntimeError, match="scheme"):
        assert_safe_image_url("file:///etc/passwd")


def test_block_metadata_name():
    with pytest.raises(RuntimeError, match="blocked"):
        assert_safe_image_url("http://localhost/secret")
