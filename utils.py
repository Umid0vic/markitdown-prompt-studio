"""
Utility functions for MarkItDown Prompt Studio.
Handles token estimation, file sanitization, conversion, preprocessing,
chunking, ZIP generation, metadata, and quality checks.
"""

import re
import os
import io
import zipfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Try importing tiktoken for accurate token estimation
try:
    import tiktoken
    _encoding = tiktoken.get_encoding("cl100k_base")
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".xls"}
SUPPORTED_FILE_TYPES = sorted(ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS)
SUPPORTED_FORMAT_LABEL = "PDF, DOCX, PPTX, XLSX, and XLS"


def estimate_tokens(text: str) -> int:
    """Estimate token count using tiktoken if available, else char/4."""
    if not text:
        return 0
    if TIKTOKEN_AVAILABLE:
        return len(_encoding.encode(text))
    return max(1, len(text) // 4)


def sanitize_filename(name: str) -> str:
    """Sanitize a filename for safe filesystem use."""
    name = Path(name).stem
    name = re.sub(r'[^\w\s\-.]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = name.strip('_.')
    return name or "unnamed"


def deduplicate_filename(name: str, existing: set) -> str:
    """Add numeric suffix if name already exists in the set."""
    if name not in existing:
        existing.add(name)
        return name
    counter = 1
    while True:
        candidate = f"{name}_{counter}"
        if candidate not in existing:
            existing.add(candidate)
            return candidate
        counter += 1


def convert_file(uploaded_file) -> dict:
    """
    Convert an uploaded file using MarkItDown.
    Returns dict with keys: filename, status, markdown, error, char_count, token_count, output_filename.
    """
    filename = uploaded_file.name
    safe_name = sanitize_filename(filename)
    result = {
        "filename": filename,
        "status": "success",
        "markdown": "",
        "error": "",
        "char_count": 0,
        "token_count": 0,
        "output_filename": f"{safe_name}.md",
        "duration_seconds": 0.0,
    }

    if uploaded_file.size == 0:
        result["status"] = "error"
        result["error"] = "File is empty."
        return result

    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        result["status"] = "error"
        result["error"] = f"Unsupported file type. Upload {SUPPORTED_FORMAT_LABEL} files only."
        return result

    tmp_path = None
    started_at = time.perf_counter()
    try:
        from markitdown import MarkItDown
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getbuffer())
            tmp_path = tmp.name

        md = MarkItDown()
        conversion = md.convert(tmp_path)
        text = conversion.text_content or ""

        if not text.strip():
            result["status"] = "warning"
            result["error"] = "Conversion produced empty output."

        result["markdown"] = text
        result["char_count"] = len(text)
        result["token_count"] = estimate_tokens(text)

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    finally:
        result["duration_seconds"] = round(time.perf_counter() - started_at, 2)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return result


def preprocess_context(markdown: str, mode: str, max_chars: int = 20000) -> str:
    """Apply context preprocessing based on selected mode."""
    if not markdown:
        return ""

    if mode == "Use full document":
        return markdown

    elif mode == "Remove excessive blank lines":
        return re.sub(r'\n{3,}', '\n\n', markdown)

    elif mode == "Use first N characters":
        return markdown[:max_chars]

    elif mode == "Extract headings only":
        lines = markdown.split('\n')
        headings = [l for l in lines if l.strip().startswith('#')]
        return '\n'.join(headings)

    elif mode == "Extract code blocks only":
        blocks = re.findall(r'```[\s\S]*?```', markdown)
        return '\n\n'.join(blocks)

    elif mode == "Extract tables only if possible":
        lines = markdown.split('\n')
        table_lines = [l for l in lines if '|' in l]
        return '\n'.join(table_lines)

    return markdown


def _split_large_paragraph(text: str, chunk_size: int) -> list:
    """Split a single large paragraph into smaller pieces by sentence/word boundary."""
    def split_by_chars(value: str) -> list:
        char_limit = max(1, chunk_size * 4)
        return [value[i:i + char_limit] for i in range(0, len(value), char_limit)]

    # Try splitting by sentences first
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) > 1:
        pieces = []
        current = []
        current_tokens = 0
        for s in sentences:
            s_tokens = estimate_tokens(s)
            if current_tokens + s_tokens > chunk_size and current:
                pieces.append(' '.join(current))
                current = []
                current_tokens = 0
            current.append(s)
            current_tokens += s_tokens
        if current:
            pieces.append(' '.join(current))
        return pieces

    # Fallback: split by words
    words = text.split()
    pieces = []
    current = []
    current_tokens = 0
    for w in words:
        w_tokens = estimate_tokens(w)
        if w_tokens > chunk_size:
            if current:
                pieces.append(' '.join(current))
                current = []
                current_tokens = 0
            pieces.extend(split_by_chars(w))
            continue
        if current_tokens + w_tokens > chunk_size and current:
            pieces.append(' '.join(current))
            current = []
            current_tokens = 0
        current.append(w)
        current_tokens += w_tokens
    if current:
        pieces.append(' '.join(current))
    return pieces if pieces else split_by_chars(text)


def chunk_text(text: str, chunk_size: int = 4000, overlap: int = 200) -> list:
    """
    Split text into chunks by estimated token count.
    Respects paragraph boundaries where possible.
    Splits oversized paragraphs by sentence/word boundary.
    """
    if not text:
        return []

    # Validate: overlap must be less than chunk_size
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)

    paragraphs = text.split('\n\n')

    # Pre-split oversized paragraphs
    split_paragraphs = []
    for para in paragraphs:
        if estimate_tokens(para) > chunk_size:
            split_paragraphs.extend(_split_large_paragraph(para, chunk_size))
        else:
            split_paragraphs.append(para)

    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in split_paragraphs:
        para_tokens = estimate_tokens(para)

        if current_tokens + para_tokens > chunk_size and current_chunk:
            chunk_text_joined = '\n\n'.join(current_chunk)
            chunks.append(chunk_text_joined)

            # Build overlap from end of current chunk
            overlap_text = ""
            overlap_tokens = 0
            for p in reversed(current_chunk):
                p_tokens = estimate_tokens(p)
                if overlap_tokens + p_tokens > overlap:
                    break
                overlap_text = p + '\n\n' + overlap_text if overlap_text else p
                overlap_tokens += p_tokens

            current_chunk = [overlap_text] if overlap_text else []
            current_tokens = overlap_tokens

        current_chunk.append(para)
        current_tokens += para_tokens

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks


def create_metadata(filename: str, extension: str, char_count: int, token_count: int,
                    context_mode: str, batch_index: int = None, chunk_number: int = None,
                    total_chunks: int = None) -> str:
    """Generate metadata block for prompts."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"- Source: {filename}",
        f"- Format: {extension}",
        f"- Converted: {timestamp}",
        f"- Characters: {char_count}",
        f"- Estimated tokens: {token_count}",
        f"- Context mode: {context_mode}",
    ]
    if batch_index is not None:
        lines.append(f"- Batch index: {batch_index}")
    if chunk_number is not None:
        lines.append(f"- Chunk: {chunk_number}/{total_chunks}")
    return '\n'.join(lines)


def quality_checklist(role: str, task: str, context: str, output_format: str,
                      constraints: str, success_criteria: str, filename: str,
                      token_count: int) -> list:
    """
    Generate prompt quality checklist.
    Returns list of (label, status) where status is 'pass' or 'warning'.
    """
    checks = []
    checks.append(("Has role", "pass" if role.strip() else "warning"))
    checks.append(("Has task", "pass" if task.strip() else "warning"))
    checks.append(("Has source context", "pass" if context.strip() else "warning"))
    checks.append(("Has output format", "pass" if output_format.strip() else "warning"))
    checks.append(("Has constraints", "pass" if constraints.strip() else "warning"))
    checks.append(("Has success criteria", "pass" if success_criteria.strip() else "warning"))
    checks.append(("Has filename/source metadata", "pass" if filename.strip() else "warning"))

    if token_count <= 100000:
        checks.append(("Estimated token count is reasonable", "pass"))
    else:
        checks.append(("Prompt may be too long", "warning"))

    if token_count > 8000:
        checks.append(("Chunking recommended for smaller models", "warning"))

    return checks


def token_warning(token_count: int) -> str:
    """Return warning message based on token count."""
    if token_count >= 100000:
        return "⚠️ This prompt is very large. Chunking is strongly recommended."
    elif token_count >= 32000:
        return "⚠️ This prompt is large. Consider chunking or compression."
    elif token_count >= 8000:
        return "⚠️ This prompt may be too large for smaller context windows."
    return ""


def create_zip(files: dict) -> bytes:
    """
    Create a ZIP file in memory.
    files: dict of {filename: content_string}
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname, content in files.items():
            zf.writestr(fname, content)
    return buffer.getvalue()
