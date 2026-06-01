# Contributing

Thanks for helping improve MarkItDown Prompt Studio.

## Development Setup

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements-dev.txt
streamlit run app.py
```

## Project Scope

The app intentionally supports a focused set of local document formats:

- PDF
- DOCX
- PPTX
- XLSX
- XLS

Please avoid adding network-backed conversion, AI API calls, or broad file-type
support unless the privacy and dependency tradeoffs are clearly documented.

## Pull Requests

Before opening a pull request:

```bash
python -m py_compile app.py utils.py templates.py
python -m pytest
```

If tests do not exist for the behavior you changed, add a focused test where
practical. Keep UI changes simple, accessible, and easy to scan.
