# MarkItDown Prompt Studio

Convert documents to Markdown and turn them into structured prompts for AI agents.

MarkItDown Prompt Studio is a local Streamlit app powered by
[Microsoft MarkItDown](https://github.com/microsoft/markitdown). It focuses on a
small, practical set of document formats so the app stays easier to install,
understand, and trust.

## Supported Formats

- PDF
- DOCX
- PPTX
- XLSX
- XLS

The app intentionally does not support audio, video, images, web URLs, YouTube,
or OCR workflows. This keeps the dependency footprint smaller and avoids hidden
network-backed conversion behavior.

## Features

- Convert supported documents to Markdown
- Upload one file or batch-convert multiple files
- See live conversion progress with status, size, duration, character count, and token count
- Preview and edit converted Markdown
- Build structured prompts with role, task, context, constraints, output format, success criteria, and metadata
- Use 9 built-in prompt templates plus custom templates with placeholders
- Estimate tokens with `tiktoken` when available, otherwise use a character-based fallback
- Show token warnings at 8K, 32K, and 100K token thresholds
- Preprocess context by trimming blank lines, truncating, or extracting headings, code blocks, or tables
- Chunk large documents with configurable size and overlap
- Export Markdown, text prompts, or ZIP bundles
- Run locally without AI API calls

## Quick Start

### Windows

Double-click:

```text
run_app.bat
```

Then open:

```text
http://localhost:8501
```

To stop the app, press `Ctrl+C` in the app terminal or double-click:

```text
stop_app.bat
```

### Manual Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Usage

1. Choose single-file or batch mode.
2. Upload PDF, DOCX, PPTX, XLSX, or XLS files.
3. Click Convert.
4. Review and edit the generated Markdown.
5. Choose a prompt template, role, output format, and context mode.
6. Enter the task, constraints, and success criteria.
7. Generate the prompt.
8. Review the checklist and token warning.
9. Export as `.md`, `.txt`, or `.zip`.

## Privacy

This app does not call AI APIs. Uploaded files are processed by the local
Streamlit app and the local MarkItDown package.

For sensitive documents, run the app locally and avoid hosting it publicly unless
you add authentication and understand where uploaded files are processed.

## Development

```bash
pip install -r requirements-dev.txt
python -m py_compile app.py utils.py templates.py
python -m pytest
```

## Project Files

- `app.py` - Streamlit UI and workflow
- `utils.py` - conversion, token counting, preprocessing, chunking, ZIP export, metadata, and checks
- `templates.py` - prompt templates and prompt generation
- `requirements.txt` - runtime dependencies
- `run_app.bat` - Windows launcher
- `stop_app.bat` - Windows stop script

## License

MIT. See [LICENSE](LICENSE).
