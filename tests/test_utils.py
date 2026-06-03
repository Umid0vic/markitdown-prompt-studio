from backend.utils import (
    SUPPORTED_EXTENSIONS,
    chunk_text,
    convert_file,
    sanitize_filename,
    token_warning,
)


class FakeUpload:
    def __init__(self, name: str, content: bytes):
        self.name = name
        self._content = content
        self.size = len(content)

    def getbuffer(self):
        return memoryview(self._content)


def test_supported_extensions_are_focused():
    assert SUPPORTED_EXTENSIONS == {".pdf", ".docx", ".pptx", ".xlsx", ".xls"}


def test_sanitize_filename_removes_path_and_unsafe_chars():
    assert sanitize_filename("../bad:name?.pdf") == "bad_name"


def test_token_warning_thresholds_are_inclusive():
    assert token_warning(7_999) == ""
    assert token_warning(8_000)
    assert token_warning(32_000)
    assert token_warning(100_000)


def test_chunk_text_splits_large_unbroken_text():
    chunks = chunk_text("a" * 20_000, chunk_size=100, overlap=10)
    assert len(chunks) > 1


def test_convert_file_rejects_unsupported_extension_before_conversion():
    result = convert_file(FakeUpload("notes.txt", b"hello"))
    assert result["status"] == "error"
    assert "Unsupported file type" in result["error"]
