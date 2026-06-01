"""
Prompt Library — persistence layer for MarkItDown Prompt Studio.
Stores prompts, folders, tags, history, and favorites in a local JSON-backed store.
"""

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


LIBRARY_DIR = Path(__file__).parent / ".prompt_library"
PROMPTS_DIR = LIBRARY_DIR / "prompts"
HISTORY_DIR = LIBRARY_DIR / "history"
TEMPLATES_DIR = LIBRARY_DIR / "templates"
INDEX_FILE = LIBRARY_DIR / "index.json"


def _ensure_dirs():
    """Create library directories if they don't exist."""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def _load_index() -> dict:
    """Load the library index."""
    _ensure_dirs()
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"folders": [], "prompts": [], "tags": [], "settings": {"theme": "dark"}}


def _save_index(index: dict):
    """Save the library index."""
    _ensure_dirs()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


# ─── Folder Management ──────────────────────────────────────────────────────

def get_folders() -> list:
    """Get all folders."""
    index = _load_index()
    return index.get("folders", [])


def create_folder(name: str, parent_id: Optional[str] = None) -> dict:
    """Create a new folder."""
    index = _load_index()
    folder = {
        "id": str(uuid.uuid4()),
        "name": name,
        "parent_id": parent_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    index.setdefault("folders", []).append(folder)
    _save_index(index)
    return folder


def rename_folder(folder_id: str, new_name: str) -> bool:
    """Rename a folder."""
    index = _load_index()
    for folder in index.get("folders", []):
        if folder["id"] == folder_id:
            folder["name"] = new_name
            _save_index(index)
            return True
    return False


def delete_folder(folder_id: str) -> bool:
    """Delete a folder and move its prompts to root."""
    index = _load_index()
    index["folders"] = [f for f in index.get("folders", []) if f["id"] != folder_id]
    # Move prompts in this folder to root
    for prompt in index.get("prompts", []):
        if prompt.get("folder_id") == folder_id:
            prompt["folder_id"] = None
    # Move subfolders to root
    for folder in index.get("folders", []):
        if folder.get("parent_id") == folder_id:
            folder["parent_id"] = None
    _save_index(index)
    return True


# ─── Prompt Management ──────────────────────────────────────────────────────

def get_prompts(folder_id: Optional[str] = None, tag: Optional[str] = None,
                search: Optional[str] = None, favorites_only: bool = False) -> list:
    """Get prompts with optional filtering."""
    index = _load_index()
    prompts = index.get("prompts", [])

    if folder_id is not None:
        prompts = [p for p in prompts if p.get("folder_id") == folder_id]

    if tag:
        prompts = [p for p in prompts if tag in p.get("tags", [])]

    if favorites_only:
        prompts = [p for p in prompts if p.get("favorite", False)]

    if search:
        search_lower = search.lower()
        prompts = [p for p in prompts if (
            search_lower in p.get("name", "").lower() or
            search_lower in p.get("task", "").lower() or
            any(search_lower in t.lower() for t in p.get("tags", []))
        )]

    # Sort by updated_at descending
    prompts.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return prompts


def save_prompt(name: str, content: str, task: str = "", folder_id: Optional[str] = None,
                tags: Optional[list] = None, metadata: Optional[dict] = None,
                prompt_id: Optional[str] = None) -> dict:
    """Save a prompt to the library. If prompt_id is given, updates existing."""
    index = _load_index()
    now = datetime.now(timezone.utc).isoformat()

    if prompt_id:
        # Update existing
        for prompt in index.get("prompts", []):
            if prompt["id"] == prompt_id:
                prompt["name"] = name
                prompt["task"] = task
                prompt["folder_id"] = folder_id
                prompt["tags"] = tags or []
                prompt["metadata"] = metadata or {}
                prompt["updated_at"] = now
                # Save content to file
                _write_prompt_file(prompt_id, content)
                # Auto-save history
                _save_history_entry(prompt_id, content, name)
                _save_index(index)
                return prompt
        # If not found, fall through to create new
        prompt_id = None

    # Create new prompt
    pid = prompt_id or str(uuid.uuid4())
    prompt = {
        "id": pid,
        "name": name,
        "task": task,
        "folder_id": folder_id,
        "tags": tags or [],
        "favorite": False,
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }
    index.setdefault("prompts", []).append(prompt)
    _write_prompt_file(pid, content)
    _save_history_entry(pid, content, name)
    _save_index(index)
    return prompt


def load_prompt_content(prompt_id: str) -> str:
    """Load the content of a saved prompt."""
    filepath = PROMPTS_DIR / f"{prompt_id}.md"
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


def delete_prompt(prompt_id: str) -> bool:
    """Delete a prompt from the library."""
    index = _load_index()
    index["prompts"] = [p for p in index.get("prompts", []) if p["id"] != prompt_id]
    _save_index(index)
    # Remove file
    filepath = PROMPTS_DIR / f"{prompt_id}.md"
    if filepath.exists():
        filepath.unlink()
    return True


def toggle_favorite(prompt_id: str) -> bool:
    """Toggle favorite status."""
    index = _load_index()
    for prompt in index.get("prompts", []):
        if prompt["id"] == prompt_id:
            prompt["favorite"] = not prompt.get("favorite", False)
            _save_index(index)
            return prompt["favorite"]
    return False


def move_prompt(prompt_id: str, folder_id: Optional[str]) -> bool:
    """Move a prompt to a different folder."""
    index = _load_index()
    for prompt in index.get("prompts", []):
        if prompt["id"] == prompt_id:
            prompt["folder_id"] = folder_id
            prompt["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_index(index)
            return True
    return False


def _write_prompt_file(prompt_id: str, content: str):
    """Write prompt content to disk."""
    _ensure_dirs()
    filepath = PROMPTS_DIR / f"{prompt_id}.md"
    filepath.write_text(content, encoding="utf-8")


# ─── Tags ───────────────────────────────────────────────────────────────────

def get_all_tags() -> list:
    """Get all unique tags."""
    index = _load_index()
    tags = set()
    for prompt in index.get("prompts", []):
        tags.update(prompt.get("tags", []))
    return sorted(tags)


def add_tag_to_prompt(prompt_id: str, tag: str) -> bool:
    """Add a tag to a prompt."""
    index = _load_index()
    for prompt in index.get("prompts", []):
        if prompt["id"] == prompt_id:
            tags = prompt.setdefault("tags", [])
            if tag not in tags:
                tags.append(tag)
                _save_index(index)
            return True
    return False


def remove_tag_from_prompt(prompt_id: str, tag: str) -> bool:
    """Remove a tag from a prompt."""
    index = _load_index()
    for prompt in index.get("prompts", []):
        if prompt["id"] == prompt_id:
            tags = prompt.get("tags", [])
            if tag in tags:
                tags.remove(tag)
                _save_index(index)
            return True
    return False


# ─── History ────────────────────────────────────────────────────────────────

def _save_history_entry(prompt_id: str, content: str, name: str):
    """Save a history snapshot for a prompt."""
    _ensure_dirs()
    history_file = HISTORY_DIR / f"{prompt_id}.json"
    history = []
    if history_file.exists():
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)

    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "content": content,
        "char_count": len(content),
    }
    history.append(entry)

    # Keep last 50 versions
    if len(history) > 50:
        history = history[-50:]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def get_prompt_history(prompt_id: str) -> list:
    """Get version history for a prompt."""
    history_file = HISTORY_DIR / f"{prompt_id}.json"
    if history_file.exists():
        with open(history_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def restore_history_version(prompt_id: str, version_id: str) -> Optional[str]:
    """Restore a specific version from history."""
    history = get_prompt_history(prompt_id)
    for entry in history:
        if entry["id"] == version_id:
            _write_prompt_file(prompt_id, entry["content"])
            return entry["content"]
    return None


# ─── Template Library ───────────────────────────────────────────────────────

def get_builtin_templates() -> list:
    """Return built-in prompt templates with variables."""
    return [
        {
            "id": "code_review",
            "name": "Code Review",
            "description": "Review code for quality, bugs, and best practices",
            "tags": ["coding", "review"],
            "variables": ["language", "focus_areas"],
            "template": (
                "## Role\n\nSenior {{language}} engineer and code reviewer.\n\n"
                "## Task\n\nReview the following code for:\n{{focus_areas}}\n\n"
                "## Context\n\n{{context}}\n\n"
                "## Output Format\n\nMarkdown with sections: Summary, Issues Found, Suggestions, Rating (1-10)\n\n"
                "## Constraints\n\n- Be specific with line references\n- Prioritize critical issues first\n- Suggest concrete fixes"
            ),
        },
        {
            "id": "api_docs",
            "name": "API Documentation",
            "description": "Generate API documentation from source code",
            "tags": ["docs", "coding"],
            "variables": ["doc_style", "audience"],
            "template": (
                "## Role\n\nTechnical writer specializing in API documentation.\n\n"
                "## Task\n\nGenerate {{doc_style}} documentation for the following API/code.\n"
                "Target audience: {{audience}}\n\n"
                "## Context\n\n{{context}}\n\n"
                "## Output Format\n\nMarkdown with endpoints/functions, parameters, return values, and examples\n\n"
                "## Constraints\n\n- Include usage examples\n- Document error cases\n- Be precise about types"
            ),
        },
        {
            "id": "meeting_summary",
            "name": "Meeting Summary",
            "description": "Summarize meeting notes into action items",
            "tags": ["productivity", "summary"],
            "variables": ["meeting_type", "attendees"],
            "template": (
                "## Role\n\nExecutive assistant skilled at extracting actionable insights.\n\n"
                "## Task\n\nSummarize this {{meeting_type}} meeting into key decisions and action items.\n"
                "Attendees: {{attendees}}\n\n"
                "## Context\n\n{{context}}\n\n"
                "## Output Format\n\nMarkdown with: Key Decisions, Action Items (with owners), Follow-ups, Timeline\n\n"
                "## Constraints\n\n- Each action item must have an owner\n- Include deadlines where mentioned\n- Flag unresolved items"
            ),
        },
        {
            "id": "data_analysis",
            "name": "Data Analysis",
            "description": "Analyze data and extract insights",
            "tags": ["data", "analysis"],
            "variables": ["analysis_goal", "output_type"],
            "template": (
                "## Role\n\nSenior data analyst with expertise in statistical analysis.\n\n"
                "## Task\n\nAnalyze the following data to: {{analysis_goal}}\n\n"
                "## Context\n\n{{context}}\n\n"
                "## Output Format\n\n{{output_type}}\n\n"
                "## Constraints\n\n- Distinguish correlation from causation\n- Note data quality issues\n- Include confidence levels where appropriate"
            ),
        },
        {
            "id": "bug_report_analysis",
            "name": "Bug Report Analysis",
            "description": "Analyze bug reports and suggest root causes",
            "tags": ["coding", "debugging"],
            "variables": ["system_name", "severity"],
            "template": (
                "## Role\n\nSenior software engineer debugging {{system_name}}.\n\n"
                "## Task\n\nAnalyze this bug report (severity: {{severity}}) and identify:\n"
                "1. Most likely root cause\n2. Reproduction steps\n3. Suggested fix\n4. Test cases to prevent regression\n\n"
                "## Context\n\n{{context}}\n\n"
                "## Output Format\n\nStructured Markdown report\n\n"
                "## Constraints\n\n- Consider edge cases\n- Propose the minimal fix\n- Include test scenarios"
            ),
        },
        {
            "id": "requirements_extraction",
            "name": "Requirements Extraction",
            "description": "Extract structured requirements from documents",
            "tags": ["product", "requirements"],
            "variables": ["project_name", "requirement_type"],
            "template": (
                "## Role\n\nBusiness analyst extracting {{requirement_type}} requirements.\n\n"
                "## Task\n\nExtract all requirements from this document for project: {{project_name}}\n\n"
                "## Context\n\n{{context}}\n\n"
                "## Output Format\n\nTable with columns: ID, Requirement, Priority (Must/Should/Could), Source Section\n\n"
                "## Constraints\n\n- Number each requirement (REQ-001, REQ-002, etc.)\n"
                "- Flag ambiguous requirements\n- Note dependencies between requirements"
            ),
        },
    ]


def get_custom_templates() -> list:
    """Get user-saved templates."""
    index = _load_index()
    return index.get("custom_templates", [])


def save_custom_template(name: str, description: str, template: str,
                         variables: list, tags: Optional[list] = None) -> dict:
    """Save a custom template."""
    index = _load_index()
    tpl = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "template": template,
        "variables": variables,
        "tags": tags or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    index.setdefault("custom_templates", []).append(tpl)
    _save_index(index)
    return tpl


def delete_custom_template(template_id: str) -> bool:
    """Delete a custom template."""
    index = _load_index()
    index["custom_templates"] = [
        t for t in index.get("custom_templates", []) if t["id"] != template_id
    ]
    _save_index(index)
    return True


# ─── Settings ───────────────────────────────────────────────────────────────

def get_settings() -> dict:
    """Get app settings."""
    index = _load_index()
    return index.get("settings", {"theme": "dark"})


def save_settings(settings: dict):
    """Save app settings."""
    index = _load_index()
    index["settings"] = settings
    _save_index(index)


# ─── Import/Export ──────────────────────────────────────────────────────────

def export_library() -> bytes:
    """Export the entire library as a ZIP file."""
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Include index
        if INDEX_FILE.exists():
            zf.write(INDEX_FILE, "index.json")

        # Include all prompts
        if PROMPTS_DIR.exists():
            for f in PROMPTS_DIR.iterdir():
                zf.write(f, f"prompts/{f.name}")

        # Include history
        if HISTORY_DIR.exists():
            for f in HISTORY_DIR.iterdir():
                zf.write(f, f"history/{f.name}")

    return buffer.getvalue()


def import_prompt_from_text(name: str, content: str, folder_id: Optional[str] = None,
                            tags: Optional[list] = None) -> dict:
    """Import a prompt from raw text."""
    return save_prompt(name=name, content=content, task="", folder_id=folder_id, tags=tags)


def get_library_stats() -> dict:
    """Get library statistics."""
    index = _load_index()
    prompts = index.get("prompts", [])
    return {
        "total_prompts": len(prompts),
        "total_folders": len(index.get("folders", [])),
        "total_tags": len(get_all_tags()),
        "favorites": sum(1 for p in prompts if p.get("favorite")),
    }
