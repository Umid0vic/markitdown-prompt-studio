# Security Policy

## Supported Versions

Security fixes are handled on the latest released version.

## Reporting a Vulnerability

Please open a private security advisory on GitHub if available, or contact the
maintainers privately before publishing details.

Include:

- affected version or commit
- steps to reproduce
- expected and actual behavior
- any relevant sample file, if it can be shared safely

## Privacy Model

MarkItDown Prompt Studio is designed as a local-first app. It does not call AI
APIs. Uploaded documents are processed by the local Streamlit app and the local
MarkItDown installation.

The supported file types are intentionally limited to PDF, DOCX, PPTX, XLSX,
and XLS to keep the dependency surface smaller and the privacy model clearer.
