"""
FastAPI backend for MarkItDown Prompt Studio.
Handles file conversion, prompt generation, and library management.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

from .utils import (
    estimate_tokens, sanitize_filename, deduplicate_filename,
    convert_file, preprocess_context, chunk_text, create_metadata,
    quality_checklist, token_warning, create_zip, TIKTOKEN_AVAILABLE,
    SUPPORTED_FILE_TYPES, SUPPORTED_FORMAT_LABEL,
)
from .templates import (
    PROMPT_TYPES, AGENT_ROLES, OUTPUT_FORMATS,
    DEFAULT_CONSTRAINTS, DEFAULT_SUCCESS_CRITERIA,
    generate_prompt, TemplateError,
)
from .library import (
    get_folders, create_folder, rename_folder, delete_folder,
    get_prompts, save_prompt, load_prompt_content, delete_prompt,
    toggle_favorite, move_prompt, get_all_tags,
    add_tag_to_prompt, remove_tag_from_prompt,
    get_prompt_history, restore_history_version,
    get_builtin_templates, get_custom_templates, save_custom_template,
    delete_custom_template, get_settings, save_settings,
    export_library, import_prompt_from_text, get_library_stats,
)

app = FastAPI(title="MarkItDown Prompt Studio", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


# ─── Models ─────────────────────────────────────────────────────────────────

class PromptRequest(BaseModel):
    prompt_type: str = "General AI agent prompt"
    role: str = "Expert assistant"
    task: str = ""
    constraints: str = DEFAULT_CONSTRAINTS
    success_criteria: str = DEFAULT_SUCCESS_CRITERIA
    output_format: str = "Markdown"
    context_mode: str = "Use full document"
    max_chars: int = 20000
    custom_template: str = ""
    markdown_content: str = ""
    filename: str = "document"


class SavePromptRequest(BaseModel):
    name: str
    content: str
    task: str = ""
    folder_id: Optional[str] = None
    tags: list = []
    metadata: dict = {}
    prompt_id: Optional[str] = None


class FolderRequest(BaseModel):
    name: str
    parent_id: Optional[str] = None


class TagRequest(BaseModel):
    tag: str


class MoveRequest(BaseModel):
    folder_id: Optional[str] = None


class TemplateRequest(BaseModel):
    name: str
    description: str = ""
    template: str
    variables: list = []
    tags: list = []


class SettingsRequest(BaseModel):
    theme: str = "dark"
    token_budget: int = 0


# ─── Conversion Endpoints ───────────────────────────────────────────────────

@app.post("/api/convert")
async def convert_files(files: list[UploadFile] = File(...)):
    """Convert uploaded files to Markdown."""
    results = []
    used_names = set()

    for f in files:
        result = convert_file(f)
        safe = sanitize_filename(f.filename or "unnamed")
        result["output_filename"] = deduplicate_filename(safe, used_names) + ".md"
        results.append(result)

    return {"results": results}


@app.post("/api/generate-prompt")
async def generate_prompt_endpoint(req: PromptRequest):
    """Generate a structured prompt from content."""
    try:
        processed = preprocess_context(req.markdown_content, req.context_mode, req.max_chars)
        ext = os.path.splitext(req.filename)[1] if req.filename else ".md"
        chars = len(processed)
        tokens = estimate_tokens(processed)

        metadata_text = create_metadata(
            filename=req.filename,
            extension=ext,
            char_count=chars,
            token_count=tokens,
            context_mode=req.context_mode,
        )

        prompt = generate_prompt(
            req.prompt_type, req.role, req.task, metadata_text,
            processed, req.constraints, req.output_format,
            req.success_criteria, req.custom_template,
        )

        prompt_tokens = estimate_tokens(prompt)
        warning = token_warning(prompt_tokens)

        role_text = req.role
        checks = quality_checklist(
            role=role_text, task=req.task, context=prompt,
            output_format=req.output_format, constraints=req.constraints,
            success_criteria=req.success_criteria, filename=req.filename,
            token_count=prompt_tokens,
        )

        return {
            "prompt": prompt,
            "tokens": prompt_tokens,
            "chars": len(prompt),
            "warning": warning,
            "checklist": [{"label": label, "status": status} for label, status in checks],
        }
    except TemplateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/estimate-tokens")
async def estimate_tokens_endpoint(text: str = ""):
    """Estimate tokens for text."""
    return {"tokens": estimate_tokens(text), "chars": len(text)}


# ─── Library Endpoints ──────────────────────────────────────────────────────

@app.get("/api/library/stats")
async def library_stats():
    return get_library_stats()


@app.get("/api/library/prompts")
async def list_prompts(
    folder_id: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False,
):
    return get_prompts(folder_id=folder_id, tag=tag, search=search, favorites_only=favorites_only)


@app.post("/api/library/prompts")
async def create_prompt(req: SavePromptRequest):
    return save_prompt(
        name=req.name, content=req.content, task=req.task,
        folder_id=req.folder_id, tags=req.tags, metadata=req.metadata,
        prompt_id=req.prompt_id,
    )


@app.get("/api/library/prompts/{prompt_id}")
async def get_prompt(prompt_id: str):
    content = load_prompt_content(prompt_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"id": prompt_id, "content": content}


@app.delete("/api/library/prompts/{prompt_id}")
async def remove_prompt(prompt_id: str):
    delete_prompt(prompt_id)
    return {"ok": True}


@app.post("/api/library/prompts/{prompt_id}/favorite")
async def toggle_prompt_favorite(prompt_id: str):
    result = toggle_favorite(prompt_id)
    return {"favorite": result}


@app.post("/api/library/prompts/{prompt_id}/move")
async def move_prompt_endpoint(prompt_id: str, req: MoveRequest):
    move_prompt(prompt_id, req.folder_id)
    return {"ok": True}


@app.post("/api/library/prompts/{prompt_id}/tags")
async def add_tag(prompt_id: str, req: TagRequest):
    add_tag_to_prompt(prompt_id, req.tag)
    return {"ok": True}


@app.delete("/api/library/prompts/{prompt_id}/tags/{tag}")
async def remove_tag(prompt_id: str, tag: str):
    remove_tag_from_prompt(prompt_id, tag)
    return {"ok": True}


@app.get("/api/library/prompts/{prompt_id}/history")
async def prompt_history(prompt_id: str):
    return get_prompt_history(prompt_id)


@app.post("/api/library/prompts/{prompt_id}/history/{version_id}/restore")
async def restore_version(prompt_id: str, version_id: str):
    content = restore_history_version(prompt_id, version_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return {"content": content}


@app.get("/api/library/tags")
async def list_tags():
    return get_all_tags()


# ─── Folder Endpoints ───────────────────────────────────────────────────────

@app.get("/api/library/folders")
async def list_folders():
    return get_folders()


@app.post("/api/library/folders")
async def create_folder_endpoint(req: FolderRequest):
    return create_folder(req.name, req.parent_id)


@app.put("/api/library/folders/{folder_id}")
async def rename_folder_endpoint(folder_id: str, req: FolderRequest):
    rename_folder(folder_id, req.name)
    return {"ok": True}


@app.delete("/api/library/folders/{folder_id}")
async def delete_folder_endpoint(folder_id: str):
    delete_folder(folder_id)
    return {"ok": True}


# ─── Template Endpoints ─────────────────────────────────────────────────────

@app.get("/api/templates/builtin")
async def builtin_templates():
    return get_builtin_templates()


@app.get("/api/templates/custom")
async def custom_templates():
    return get_custom_templates()


@app.post("/api/templates/custom")
async def create_template(req: TemplateRequest):
    return save_custom_template(
        name=req.name, description=req.description,
        template=req.template, variables=req.variables, tags=req.tags,
    )


@app.delete("/api/templates/custom/{template_id}")
async def delete_template(template_id: str):
    delete_custom_template(template_id)
    return {"ok": True}


# ─── Settings Endpoints ─────────────────────────────────────────────────────

@app.get("/api/settings")
async def get_app_settings():
    return get_settings()


@app.put("/api/settings")
async def update_settings(req: SettingsRequest):
    save_settings(req.model_dump())
    return {"ok": True}


# ─── Export/Import ──────────────────────────────────────────────────────────

@app.get("/api/library/export")
async def export_library_endpoint():
    data = export_library()
    return StreamingResponse(
        iter([data]),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=prompt_library.zip"},
    )


@app.post("/api/library/import")
async def import_prompt(file: UploadFile = File(...), folder_id: Optional[str] = None):
    content = (await file.read()).decode("utf-8")
    name = os.path.splitext(file.filename or "imported")[0]
    result = import_prompt_from_text(name, content, folder_id=folder_id)
    return result


# ─── Config Info ────────────────────────────────────────────────────────────

@app.get("/api/config")
async def get_config():
    return {
        "supported_formats": SUPPORTED_FORMAT_LABEL,
        "supported_types": SUPPORTED_FILE_TYPES,
        "tiktoken_available": TIKTOKEN_AVAILABLE,
        "prompt_types": PROMPT_TYPES,
        "agent_roles": AGENT_ROLES,
        "output_formats": OUTPUT_FORMATS,
        "default_constraints": DEFAULT_CONSTRAINTS,
        "default_success_criteria": DEFAULT_SUCCESS_CRITERIA,
    }


# ─── Serve Frontend ────────────────────────────────────────────────────────

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
