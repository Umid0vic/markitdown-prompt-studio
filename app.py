"""
MarkItDown Prompt Studio
A professional prompt engineering workspace.
Convert files into Markdown and build, organize, and manage prompts for AI agents.
Powered by Microsoft MarkItDown.
"""

import streamlit as st
import pandas as pd
import time
import re
from pathlib import Path

from utils import (
    estimate_tokens, sanitize_filename, deduplicate_filename,
    convert_file, preprocess_context, chunk_text, create_metadata,
    quality_checklist, token_warning, create_zip, TIKTOKEN_AVAILABLE,
    SUPPORTED_FILE_TYPES, SUPPORTED_FORMAT_LABEL,
)
from templates import (
    PROMPT_TYPES, AGENT_ROLES, OUTPUT_FORMATS,
    DEFAULT_CONSTRAINTS, DEFAULT_SUCCESS_CRITERIA,
    generate_prompt, TemplateError,
)
from library import (
    get_folders, create_folder, rename_folder, delete_folder,
    get_prompts, save_prompt, load_prompt_content, delete_prompt,
    toggle_favorite, move_prompt, get_all_tags,
    add_tag_to_prompt, remove_tag_from_prompt,
    get_prompt_history, restore_history_version,
    get_builtin_templates, get_custom_templates, save_custom_template,
    delete_custom_template, get_settings, save_settings,
    export_library, import_prompt_from_text, get_library_stats,
)

# ─── Page Config ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="MarkItDown Prompt Studio",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Theme ──────────────────────────────────────────────────────────────────

settings = get_settings()
theme = settings.get("theme", "dark")

if theme == "dark":
    BG = "#0a0a0f"
    CARD_BG = "#12121a"
    BORDER = "rgba(255, 255, 255, 0.06)"
    TEXT = "#e8e8ed"
    TEXT_MUTED = "#8888a0"
    ACCENT = "#6366f1"
    ACCENT_HOVER = "#818cf8"
    SIDEBAR_BG = "#0f0f14"
else:
    BG = "#f8f9fc"
    CARD_BG = "#ffffff"
    BORDER = "rgba(0, 0, 0, 0.08)"
    TEXT = "#1a1a2e"
    TEXT_MUTED = "#6b7280"
    ACCENT = "#4f46e5"
    ACCENT_HOVER = "#6366f1"
    SIDEBAR_BG = "#ffffff"

st.markdown(f"""
<style>
    .stApp {{
        background-color: {BG};
        color: {TEXT};
    }}
    section[data-testid="stSidebar"] {{
        background-color: {SIDEBAR_BG};
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] .stMarkdown p {{
        color: {TEXT_MUTED};
        font-size: 0.88rem;
    }}
    .stMarkdown h1 {{
        color: {TEXT};
        font-weight: 700;
        letter-spacing: -0.02em;
        font-size: 1.75rem !important;
        margin-bottom: 0.2rem !important;
    }}
    .stMarkdown h2 {{
        color: {TEXT};
        font-weight: 600;
        font-size: 1.25rem !important;
        letter-spacing: -0.01em;
        margin-top: 1.5rem !important;
    }}
    .stMarkdown h3 {{
        color: {TEXT_MUTED};
        font-weight: 600;
        font-size: 1rem !important;
    }}
    .stTextArea textarea, .stTextInput input {{
        background-color: {CARD_BG} !important;
        color: {TEXT} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
        padding: 12px !important;
        font-size: 0.9rem !important;
    }}
    .stTextArea textarea:focus, .stTextInput input:focus {{
        border-color: rgba(99, 102, 241, 0.5) !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.1) !important;
    }}
    .stSelectbox > div > div {{
        background-color: {CARD_BG} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 10px !important;
    }}
    div[data-testid="stExpander"] {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}
    div[data-testid="stMetric"] {{
        background-color: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 12px;
        padding: 14px 18px;
    }}
    div[data-testid="stMetric"] label {{
        color: {TEXT_MUTED} !important;
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {TEXT} !important;
        font-weight: 600 !important;
    }}
    .stDataFrame {{
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid {BORDER};
    }}
    .stDownloadButton button {{
        background: linear-gradient(135deg, {ACCENT} 0%, #4f46e5 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.2rem !important;
        font-size: 0.84rem !important;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2) !important;
        transition: all 0.2s ease !important;
    }}
    .stDownloadButton button:hover {{
        background: linear-gradient(135deg, {ACCENT_HOVER} 0%, {ACCENT} 100%) !important;
        box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3) !important;
        transform: translateY(-1px) !important;
    }}
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {ACCENT} 0%, #4f46e5 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2) !important;
    }}
    .stButton button {{
        border-radius: 10px !important;
        border: 1px solid {BORDER} !important;
        background-color: {CARD_BG} !important;
        color: {TEXT} !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }}
    .stButton button:hover {{
        border-color: rgba(99, 102, 241, 0.4) !important;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        background-color: {CARD_BG};
        border-radius: 10px;
        padding: 4px;
        border: 1px solid {BORDER};
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        color: {TEXT_MUTED};
        font-weight: 500;
        font-size: 0.84rem;
        padding: 8px 16px;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: rgba(99, 102, 241, 0.15) !important;
        color: #a5b4fc !important;
    }}
    hr {{
        border-color: {BORDER} !important;
        margin: 1.5rem 0 !important;
    }}
    .stAlert {{
        border-radius: 10px !important;
    }}
    footer {{ visibility: hidden; }}
    .app-footer {{
        text-align: center;
        color: {TEXT_MUTED};
        padding: 2rem 0 1rem 0;
        font-size: 0.78rem;
        border-top: 1px solid {BORDER};
        margin-top: 3rem;
    }}
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: rgba(128,128,128,0.2); border-radius: 3px; }}
    .tag-badge {{
        display: inline-block;
        background: rgba(99, 102, 241, 0.15);
        color: #a5b4fc;
        border-radius: 6px;
        padding: 2px 8px;
        font-size: 0.72rem;
        font-weight: 500;
        margin-right: 4px;
    }}
</style>
""", unsafe_allow_html=True)

# ─── Session State ──────────────────────────────────────────────────────────

if "conversion_results" not in st.session_state:
    st.session_state.conversion_results = []
if "generated_prompts" not in st.session_state:
    st.session_state.generated_prompts = {}
if "edited_markdown" not in st.session_state:
    st.session_state.edited_markdown = {}
if "active_prompt_key" not in st.session_state:
    st.session_state.active_prompt_key = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Convert"
if "active_folder" not in st.session_state:
    st.session_state.active_folder = None
if "token_budget" not in st.session_state:
    st.session_state.token_budget = 0


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remaining = divmod(seconds, 60)
    return f"{int(minutes)}m {remaining:.0f}s"


def upload_size(uploaded_file) -> str:
    size = getattr(uploaded_file, "size", 0) or 0
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"


# ─── Sidebar Navigation ────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("# Prompt Studio")

    # Navigation
    pages = ["Convert", "Library", "Templates", "Settings"]
    page_icons = {"Convert": "⚡", "Library": "📂", "Templates": "📋", "Settings": "⚙️"}

    for page in pages:
        icon = page_icons[page]
        is_active = st.session_state.current_page == page
        if st.button(
            f"{icon} {page}",
            key=f"nav_{page}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.current_page = page
            st.rerun()

    st.markdown("---")

    # Library quick stats
    stats = get_library_stats()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Prompts", stats["total_prompts"])
    with col2:
        st.metric("Folders", stats["total_folders"])

    st.markdown("---")

    # Theme toggle
    col_t1, col_t2 = st.columns([2, 1])
    with col_t1:
        st.caption("Theme")
    with col_t2:
        new_theme = "light" if theme == "dark" else "dark"
        if st.button("☀" if theme == "dark" else "🌙", key="theme_toggle"):
            settings["theme"] = new_theme
            save_settings(settings)
            st.rerun()

    # Token budget
    st.markdown("---")
    st.caption("Token Budget")
    budget = st.number_input(
        "Max tokens", min_value=0, value=st.session_state.token_budget,
        step=1000, key="budget_input", label_visibility="collapsed",
        help="Set to 0 for unlimited"
    )
    st.session_state.token_budget = budget

    st.markdown("---")
    st.caption(f"Formats: {SUPPORTED_FORMAT_LABEL}")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: CONVERT
# ═══════════════════════════════════════════════════════════════════════════════

if st.session_state.current_page == "Convert":

    st.markdown("# Convert & Build")
    st.caption("Upload files, convert to Markdown, and generate prompts.")

    # ─── Settings Row ───────────────────────────────────────────────────────
    with st.expander("Conversion Settings", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            mode = st.radio("Mode", ["Single file", "Batch files"], key="mode_radio", horizontal=True)
        with col2:
            context_modes = [
                "Use full document",
                "Remove excessive blank lines",
                "Use first N characters",
                "Extract headings only",
                "Extract code blocks only",
                "Extract tables only if possible",
            ]
            context_mode = st.selectbox("Context mode", context_modes, key="context_mode_select")
        with col3:
            max_chars = 20000
            if context_mode == "Use first N characters":
                max_chars = st.number_input("Max characters", min_value=100, value=20000, step=1000, key="max_chars_input")
            enable_chunking = st.toggle("Enable chunking", value=False, key="chunking_toggle")

        if enable_chunking:
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                chunk_size = st.number_input("Chunk size (tokens)", min_value=100, value=4000, step=500, key="chunk_size_input")
            with col_c2:
                chunk_overlap = st.number_input("Overlap (tokens)", min_value=0, value=200, step=50, key="chunk_overlap_input")
        else:
            chunk_size = 4000
            chunk_overlap = 200

    # ─── Upload ─────────────────────────────────────────────────────────────

    accept_multiple = mode == "Batch files"
    uploaded_files = st.file_uploader(
        "Drop files here",
        accept_multiple_files=accept_multiple,
        key="file_uploader",
        type=SUPPORTED_FILE_TYPES,
        label_visibility="collapsed",
    )

    if uploaded_files is None:
        uploaded_files = []
    elif not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]

    # ─── Convert Button ─────────────────────────────────────────────────────

    if uploaded_files:
        if st.button("Convert", type="primary", key="convert_btn", use_container_width=True):
            results = []
            used_names = set()
            total = len(uploaded_files)
            started_at = time.perf_counter()

            progress = st.progress(0, text="Converting...")
            for i, f in enumerate(uploaded_files):
                progress.progress((i + 1) / total, text=f"Converting {f.name}...")
                result = convert_file(f)
                safe = sanitize_filename(f.name)
                result["output_filename"] = deduplicate_filename(safe, used_names) + ".md"
                results.append(result)

            elapsed = time.perf_counter() - started_at
            success_count = sum(1 for r in results if r["status"] != "error")
            progress.progress(1.0, text=f"Done — {success_count}/{total} in {format_duration(elapsed)}")

            st.session_state.conversion_results = results
            for r in results:
                if r["status"] != "error":
                    st.session_state.edited_markdown[r["output_filename"]] = r["markdown"]

    # ─── Results ────────────────────────────────────────────────────────────

    results = st.session_state.conversion_results
    if results:
        successful = [r for r in results if r["status"] != "error"]

        if not successful:
            st.warning("No files converted successfully.")
        else:
            st.markdown("## Output")

            # Action bar
            if len(successful) == 1:
                r = successful[0]
                key = r["output_filename"]
                md_content = st.session_state.edited_markdown.get(key, r["markdown"])
                chars = len(md_content)
                tokens = estimate_tokens(md_content)

                col_m1, col_m2, col_dl, col_copy = st.columns([1, 1, 1.5, 1])
                with col_m1:
                    st.metric("Tokens", f"{tokens:,}")
                with col_m2:
                    st.metric("Characters", f"{chars:,}")
                with col_dl:
                    st.download_button("⬇ Download .md", data=md_content,
                                       file_name=r["output_filename"], mime="text/markdown",
                                       key="dl_single_md", use_container_width=True)
                with col_copy:
                    if st.button("📋 Copy", key="copy_md", use_container_width=True):
                        st.toast("Markdown content ready — use the editor below to select and copy.")

                # Budget indicator
                if st.session_state.token_budget > 0:
                    used_pct = min(tokens / st.session_state.token_budget, 1.0)
                    st.progress(used_pct, text=f"Budget: {tokens:,} / {st.session_state.token_budget:,} tokens ({used_pct*100:.0f}%)")

                tab_preview, tab_edit = st.tabs(["Preview", "Edit"])
                with tab_preview:
                    st.markdown(md_content)
                with tab_edit:
                    edited = st.text_area("ed", value=md_content, height=400,
                                          key=f"editor_{key}", label_visibility="collapsed")
                    st.session_state.edited_markdown[key] = edited
            else:
                # Batch
                zip_files = {r["output_filename"]: st.session_state.edited_markdown.get(r["output_filename"], r["markdown"]) for r in successful}
                col_info, col_dl = st.columns([2, 1])
                with col_info:
                    st.metric("Files", f"{len(successful)}")
                with col_dl:
                    st.download_button("⬇ Download ZIP", data=create_zip(zip_files),
                                       file_name="converted.zip", mime="application/zip",
                                       key="dl_batch_zip", use_container_width=True)

                file_tabs = st.tabs([r["output_filename"] for r in successful])
                for tab, r in zip(file_tabs, successful):
                    key = r["output_filename"]
                    with tab:
                        tab_p, tab_e = st.tabs(["Preview", "Edit"])
                        with tab_p:
                            st.markdown(st.session_state.edited_markdown.get(key, r["markdown"]))
                        with tab_e:
                            edited = st.text_area("ed", value=st.session_state.edited_markdown.get(key, r["markdown"]),
                                                  height=300, key=f"editor_{key}", label_visibility="collapsed")
                            st.session_state.edited_markdown[key] = edited

            # ─── Prompt Builder ─────────────────────────────────────────────

            st.markdown("---")
            st.markdown("## Build Prompt")

            col_left, col_right = st.columns([2, 1])

            with col_left:
                task_input = st.text_area(
                    "Task", placeholder="What should the AI do with this content?",
                    height=100, key="task_input",
                )

            with col_right:
                prompt_type = st.selectbox("Type", PROMPT_TYPES, key="prompt_type_select")
                agent_role = st.selectbox("Role", AGENT_ROLES, key="agent_role_select")
                output_format = st.selectbox("Format", OUTPUT_FORMATS, key="output_format_select")

            custom_role = ""
            if agent_role == "Custom role":
                custom_role = st.text_input("Custom role", key="custom_role_input")
            custom_format = ""
            if output_format == "Custom format":
                custom_format = st.text_input("Custom format", key="custom_format_input")

            with st.expander("Constraints & Criteria"):
                constraints_input = st.text_area("Constraints", value=DEFAULT_CONSTRAINTS, height=100, key="constraints_input")
                success_criteria_input = st.text_area("Success Criteria", value=DEFAULT_SUCCESS_CRITERIA, height=100, key="success_criteria_input")

            custom_template = ""
            if prompt_type == "Custom prompt":
                st.caption("Placeholders: {role}, {task}, {context}, {constraints}, {output_format}, {success_criteria}, {metadata}")
                custom_template = st.text_area("Template", height=200, key="custom_template_input")

            # Batch prompt mode
            batch_prompt_mode = "separate"
            if len(successful) > 1:
                batch_prompt_mode = st.radio("Batch mode", ["Separate per file", "Combined"], key="batch_prompt_mode", horizontal=True)
                batch_prompt_mode = "combined" if "Combined" in batch_prompt_mode else "separate"

            # Generate
            if st.button("Generate Prompt", type="primary", key="generate_prompt_btn", use_container_width=True):
                if not task_input.strip():
                    st.error("Enter a task description.")
                else:
                    role_text = custom_role if agent_role == "Custom role" else agent_role
                    format_text = custom_format if output_format == "Custom format" else output_format

                    if not role_text.strip():
                        st.error("Specify a role.")
                    elif not format_text.strip():
                        st.error("Specify an output format.")
                    else:
                        generated_prompts = {}
                        prompt_names_used = set()

                        try:
                            if batch_prompt_mode == "combined" and len(successful) > 1:
                                combined_parts = []
                                combined_chars = 0
                                for idx, r in enumerate(successful, 1):
                                    key = r["output_filename"]
                                    md = st.session_state.edited_markdown.get(key, r["markdown"])
                                    processed = preprocess_context(md, context_mode, max_chars)
                                    combined_parts.append(f"# Source {idx}: {r['filename']}\n\n{processed}")
                                    combined_chars += len(processed)

                                combined_context = "\n\n---\n\n".join(combined_parts)
                                combined_tokens = estimate_tokens(combined_context)
                                metadata_text = create_metadata(
                                    filename=f"{len(successful)} files", extension="multiple",
                                    char_count=combined_chars, token_count=combined_tokens,
                                    context_mode=context_mode)
                                prompt = generate_prompt(prompt_type, role_text, task_input, metadata_text,
                                                        combined_context, constraints_input, format_text,
                                                        success_criteria_input, custom_template)
                                generated_prompts["combined.prompt.md"] = prompt
                            else:
                                for idx, r in enumerate(successful, 1):
                                    key = r["output_filename"]
                                    md = st.session_state.edited_markdown.get(key, r["markdown"])
                                    processed = preprocess_context(md, context_mode, max_chars)
                                    ext = Path(r["filename"]).suffix
                                    chars = len(processed)
                                    tokens = estimate_tokens(processed)
                                    metadata_text = create_metadata(
                                        filename=r["filename"], extension=ext,
                                        char_count=chars, token_count=tokens,
                                        context_mode=context_mode,
                                        batch_index=idx if len(successful) > 1 else None)
                                    prompt = generate_prompt(prompt_type, role_text, task_input, metadata_text,
                                                            processed, constraints_input, format_text,
                                                            success_criteria_input, custom_template)
                                    safe = sanitize_filename(r["filename"])
                                    prompt_fname = deduplicate_filename(f"{safe}.prompt", prompt_names_used) + ".md"
                                    generated_prompts[prompt_fname] = prompt

                            st.session_state.generated_prompts = generated_prompts
                            st.session_state.active_prompt_key = list(generated_prompts.keys())[0]
                            st.success("Prompt generated!")
                        except TemplateError as e:
                            st.error(f"Template error: {e}")

            # ─── Generated Prompt Output ────────────────────────────────────

            if st.session_state.generated_prompts:
                st.markdown("---")
                st.markdown("## Generated Prompt")

                gen_prompts = st.session_state.generated_prompts
                prompt_keys = list(gen_prompts.keys())

                if len(prompt_keys) > 1:
                    selected_key = st.selectbox("Prompt", prompt_keys, key="prompt_selector")
                else:
                    selected_key = prompt_keys[0]

                st.session_state.active_prompt_key = selected_key
                prompt_text = gen_prompts[selected_key]
                prompt_tokens = estimate_tokens(prompt_text)

                # Export bar at top
                col_m1, col_m2, col_dl1, col_dl2, col_save = st.columns([1, 1, 1, 1, 1])
                with col_m1:
                    st.metric("Tokens", f"{prompt_tokens:,}")
                with col_m2:
                    st.metric("Chars", f"{len(prompt_text):,}")
                with col_dl1:
                    st.download_button("⬇ .md", data=prompt_text, file_name=selected_key,
                                       mime="text/markdown", key="dl_prompt_md", use_container_width=True)
                with col_dl2:
                    txt_name = selected_key.rsplit(".", 1)[0] + ".txt"
                    st.download_button("⬇ .txt", data=prompt_text, file_name=txt_name,
                                       mime="text/plain", key="dl_prompt_txt", use_container_width=True)
                with col_save:
                    if st.button("💾 Save to Library", key="save_to_lib", use_container_width=True):
                        save_prompt(
                            name=selected_key.replace(".prompt.md", ""),
                            content=prompt_text,
                            task=task_input,
                            metadata={"type": prompt_type, "role": agent_role, "format": output_format},
                        )
                        st.success("Saved to library!")

                # Budget indicator
                if st.session_state.token_budget > 0:
                    used_pct = min(prompt_tokens / st.session_state.token_budget, 1.0)
                    st.progress(used_pct, text=f"Budget: {prompt_tokens:,} / {st.session_state.token_budget:,} tokens")
                    if used_pct >= 1.0:
                        st.error("Over token budget! Consider chunking or trimming context.")

                warning = token_warning(prompt_tokens)
                if warning:
                    st.warning(warning)

                # Quality checklist
                with st.expander("Quality Checklist"):
                    role_text = custom_role if agent_role == "Custom role" else agent_role
                    format_text = custom_format if output_format == "Custom format" else output_format
                    checks = quality_checklist(
                        role=role_text, task=task_input, context=prompt_text,
                        output_format=format_text, constraints=constraints_input,
                        success_criteria=success_criteria_input,
                        filename=successful[0]["filename"] if successful else "",
                        token_count=prompt_tokens)
                    for label, status in checks:
                        st.markdown(f"{'✓' if status == 'pass' else '⚠'} {label}")

                # Content
                tab_preview, tab_edit = st.tabs(["Preview", "Edit"])
                with tab_preview:
                    st.markdown(prompt_text)
                with tab_edit:
                    edited_prompt = st.text_area("ep", value=prompt_text, height=400,
                                                 key=f"prompt_editor_{selected_key}", label_visibility="collapsed")
                    st.session_state.generated_prompts[selected_key] = edited_prompt


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: LIBRARY
# ═══════════════════════════════════════════════════════════════════════════════

elif st.session_state.current_page == "Library":

    st.markdown("# Prompt Library")
    st.caption("Organize, search, and manage your saved prompts.")

    # ─── Library Toolbar ────────────────────────────────────────────────────

    col_search, col_filter, col_new = st.columns([3, 1.5, 1.5])
    with col_search:
        search_query = st.text_input("Search prompts...", key="lib_search", label_visibility="collapsed",
                                     placeholder="Search prompts...")
    with col_filter:
        all_tags = get_all_tags()
        filter_tag = st.selectbox("Filter by tag", ["All"] + all_tags, key="lib_filter_tag")
    with col_new:
        show_favs = st.toggle("★ Favorites", key="lib_favs")

    # ─── Folder Sidebar + Prompts ───────────────────────────────────────────

    col_folders, col_prompts = st.columns([1, 3])

    with col_folders:
        st.markdown("### Folders")

        folders = get_folders()

        # Root (all)
        if st.button("📂 All Prompts", key="folder_all", use_container_width=True):
            st.session_state.active_folder = None
            st.rerun()

        for folder in folders:
            col_f, col_del = st.columns([4, 1])
            with col_f:
                if st.button(f"📁 {folder['name']}", key=f"folder_{folder['id']}", use_container_width=True):
                    st.session_state.active_folder = folder["id"]
                    st.rerun()
            with col_del:
                if st.button("×", key=f"del_folder_{folder['id']}"):
                    delete_folder(folder["id"])
                    st.rerun()

        st.markdown("---")

        # Create folder
        with st.expander("New Folder"):
            new_folder_name = st.text_input("Name", key="new_folder_name")
            if st.button("Create", key="create_folder_btn") and new_folder_name:
                create_folder(new_folder_name)
                st.rerun()

        st.markdown("---")

        # Import
        with st.expander("Import"):
            import_file = st.file_uploader("Import .md/.txt", type=["md", "txt"], key="import_file")
            if import_file:
                content = import_file.read().decode("utf-8")
                name = Path(import_file.name).stem
                import_prompt_from_text(name, content, folder_id=st.session_state.active_folder)
                st.success(f"Imported: {name}")
                st.rerun()

        # Export
        st.download_button("⬇ Export Library", data=export_library(),
                           file_name="prompt_library.zip", mime="application/zip",
                           key="export_lib", use_container_width=True)

    with col_prompts:
        # Get prompts with filters
        prompts = get_prompts(
            folder_id=st.session_state.active_folder,
            tag=filter_tag if filter_tag != "All" else None,
            search=search_query if search_query else None,
            favorites_only=show_favs,
        )

        if not prompts:
            st.info("No prompts found. Generate and save prompts from the Convert page!")
        else:
            for prompt in prompts:
                with st.container():
                    col_star, col_name, col_tags, col_actions = st.columns([0.5, 3, 2, 2])

                    with col_star:
                        star = "★" if prompt.get("favorite") else "☆"
                        if st.button(star, key=f"fav_{prompt['id']}"):
                            toggle_favorite(prompt["id"])
                            st.rerun()

                    with col_name:
                        st.markdown(f"**{prompt['name']}**")
                        if prompt.get("task"):
                            st.caption(prompt["task"][:80])

                    with col_tags:
                        tags_html = " ".join(f'<span class="tag-badge">{t}</span>' for t in prompt.get("tags", []))
                        if tags_html:
                            st.markdown(tags_html, unsafe_allow_html=True)

                    with col_actions:
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.button("Open", key=f"open_{prompt['id']}"):
                                content = load_prompt_content(prompt["id"])
                                st.session_state[f"viewing_prompt_{prompt['id']}"] = content
                        with c2:
                            if st.button("📋", key=f"copy_{prompt['id']}"):
                                st.toast("Use the expanded view below to copy content.")
                        with c3:
                            if st.button("🗑", key=f"del_{prompt['id']}"):
                                delete_prompt(prompt["id"])
                                st.rerun()

                    # Expanded view
                    if st.session_state.get(f"viewing_prompt_{prompt['id']}"):
                        content = st.session_state[f"viewing_prompt_{prompt['id']}"]
                        with st.expander(f"📄 {prompt['name']}", expanded=True):
                            # Tag management
                            col_t1, col_t2 = st.columns([3, 1])
                            with col_t1:
                                new_tag = st.text_input("Add tag", key=f"tag_input_{prompt['id']}")
                            with col_t2:
                                if st.button("Add", key=f"add_tag_{prompt['id']}") and new_tag:
                                    add_tag_to_prompt(prompt["id"], new_tag.strip())
                                    st.rerun()

                            # Move to folder
                            folder_options = ["Root"] + [f["name"] for f in folders]
                            folder_ids = [None] + [f["id"] for f in folders]
                            move_to = st.selectbox("Move to folder", folder_options, key=f"move_{prompt['id']}")
                            if st.button("Move", key=f"move_btn_{prompt['id']}"):
                                idx = folder_options.index(move_to)
                                move_prompt(prompt["id"], folder_ids[idx])
                                st.rerun()

                            # History
                            history = get_prompt_history(prompt["id"])
                            if history:
                                with st.expander(f"History ({len(history)} versions)"):
                                    for entry in reversed(history[-10:]):
                                        col_h1, col_h2 = st.columns([3, 1])
                                        with col_h1:
                                            st.caption(f"{entry['timestamp'][:19]} — {entry['char_count']} chars")
                                        with col_h2:
                                            if st.button("Restore", key=f"restore_{entry['id']}"):
                                                restored = restore_history_version(prompt["id"], entry["id"])
                                                if restored:
                                                    st.session_state[f"viewing_prompt_{prompt['id']}"] = restored
                                                    st.rerun()

                            # Content
                            st.markdown(content)

                            # Download
                            st.download_button(
                                "⬇ Download", data=content,
                                file_name=f"{prompt['name']}.md", mime="text/markdown",
                                key=f"dl_{prompt['id']}", use_container_width=True)

                    st.markdown("---")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

elif st.session_state.current_page == "Templates":

    st.markdown("# Template Library")
    st.caption("Use and customize prompt templates with variables.")

    tab_builtin, tab_custom, tab_create = st.tabs(["Built-in Templates", "My Templates", "Create Template"])

    with tab_builtin:
        templates = get_builtin_templates()

        for tpl in templates:
            with st.expander(f"**{tpl['name']}** — {tpl['description']}"):
                # Show tags
                tags_html = " ".join(f'<span class="tag-badge">{t}</span>' for t in tpl.get("tags", []))
                st.markdown(tags_html, unsafe_allow_html=True)

                st.markdown("**Variables:**")
                st.caption(", ".join(f"`{{{{{v}}}}}`" for v in tpl["variables"]))

                # Variable inputs
                var_values = {}
                for var in tpl["variables"]:
                    var_values[var] = st.text_input(f"{var}", key=f"tpl_var_{tpl['id']}_{var}",
                                                   placeholder=f"Enter {var}...")

                # Context
                context_input = st.text_area("Context (paste or leave empty)",
                                             height=150, key=f"tpl_ctx_{tpl['id']}")

                if st.button("Generate from Template", key=f"gen_tpl_{tpl['id']}", type="primary"):
                    # Fill variables
                    filled = tpl["template"]
                    for var, val in var_values.items():
                        filled = filled.replace("{{" + var + "}}", val or f"[{var}]")
                    filled = filled.replace("{{context}}", context_input or "[paste context here]")

                    st.markdown("### Result")
                    st.markdown(filled)

                    # Actions
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.download_button("⬇ Download", data=filled,
                                           file_name=f"{tpl['name'].lower().replace(' ', '_')}.md",
                                           mime="text/markdown", key=f"dl_tpl_{tpl['id']}")
                    with col2:
                        if st.button("Save to Library", key=f"save_tpl_{tpl['id']}"):
                            save_prompt(name=tpl["name"], content=filled, task=tpl["description"])
                            st.success("Saved!")
                    with col3:
                        prompt_tokens = estimate_tokens(filled)
                        st.metric("Tokens", f"{prompt_tokens:,}")

    with tab_custom:
        custom_templates = get_custom_templates()

        if not custom_templates:
            st.info("No custom templates yet. Create one in the 'Create Template' tab!")
        else:
            for tpl in custom_templates:
                with st.expander(f"**{tpl['name']}** — {tpl.get('description', '')}"):
                    st.caption(f"Variables: {', '.join(tpl.get('variables', []))}")

                    var_values = {}
                    for var in tpl.get("variables", []):
                        var_values[var] = st.text_input(f"{var}", key=f"ctpl_var_{tpl['id']}_{var}")

                    context_input = st.text_area("Context", height=150, key=f"ctpl_ctx_{tpl['id']}")

                    if st.button("Generate", key=f"gen_ctpl_{tpl['id']}", type="primary"):
                        filled = tpl["template"]
                        for var, val in var_values.items():
                            filled = filled.replace("{{" + var + "}}", val or f"[{var}]")
                        filled = filled.replace("{{context}}", context_input or "[context]")
                        st.markdown(filled)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button("⬇ Download", data=filled,
                                               file_name=f"{tpl['name']}.md", mime="text/markdown",
                                               key=f"dl_ctpl_{tpl['id']}")
                        with col2:
                            if st.button("Save to Library", key=f"save_ctpl_{tpl['id']}"):
                                save_prompt(name=tpl["name"], content=filled)
                                st.success("Saved!")

                    if st.button("Delete Template", key=f"del_ctpl_{tpl['id']}"):
                        delete_custom_template(tpl["id"])
                        st.rerun()

    with tab_create:
        st.markdown("### Create Custom Template")
        st.caption("Use `{{variable_name}}` for dynamic placeholders. `{{context}}` is reserved for document content.")

        tpl_name = st.text_input("Template name", key="new_tpl_name")
        tpl_desc = st.text_input("Description", key="new_tpl_desc")
        tpl_vars = st.text_input("Variables (comma-separated)", key="new_tpl_vars",
                                 placeholder="e.g. language, framework, audience")
        tpl_tags = st.text_input("Tags (comma-separated)", key="new_tpl_tags",
                                 placeholder="e.g. coding, review")
        tpl_body = st.text_area("Template body", height=300, key="new_tpl_body",
                                placeholder="## Role\n\n{{role}}\n\n## Task\n\n{{task}}\n\n## Context\n\n{{context}}")

        if st.button("Save Template", type="primary", key="save_new_tpl"):
            if not tpl_name or not tpl_body:
                st.error("Name and body are required.")
            else:
                variables = [v.strip() for v in tpl_vars.split(",") if v.strip()]
                tags = [t.strip() for t in tpl_tags.split(",") if t.strip()]
                save_custom_template(name=tpl_name, description=tpl_desc,
                                     template=tpl_body, variables=variables, tags=tags)
                st.success(f"Template '{tpl_name}' saved!")
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SETTINGS
# ═══════════════════════════════════════════════════════════════════════════════

elif st.session_state.current_page == "Settings":

    st.markdown("# Settings")

    st.markdown("## Appearance")
    theme_choice = st.radio("Theme", ["dark", "light"], index=0 if theme == "dark" else 1,
                            key="settings_theme", horizontal=True)
    if theme_choice != theme:
        settings["theme"] = theme_choice
        save_settings(settings)
        st.rerun()

    st.markdown("---")

    st.markdown("## Token Budget")
    st.caption("Set a token limit to track prompt size against your model's context window.")
    budget_presets = {"No limit": 0, "GPT-4 (8K)": 8000, "GPT-4 (32K)": 32000,
                     "GPT-4 (128K)": 128000, "Claude (200K)": 200000, "Custom": -1}
    preset = st.selectbox("Preset", list(budget_presets.keys()), key="budget_preset")
    if budget_presets[preset] == -1:
        custom_budget = st.number_input("Custom token limit", min_value=0, value=8000, step=1000, key="custom_budget")
        st.session_state.token_budget = custom_budget
    else:
        st.session_state.token_budget = budget_presets[preset]

    st.markdown("---")

    st.markdown("## Library")
    stats = get_library_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Prompts", stats["total_prompts"])
    with col2:
        st.metric("Folders", stats["total_folders"])
    with col3:
        st.metric("Tags", stats["total_tags"])
    with col4:
        st.metric("Favorites", stats["favorites"])

    st.download_button("⬇ Export Full Library", data=export_library(),
                       file_name="prompt_studio_library.zip", mime="application/zip",
                       key="settings_export")

    st.markdown("---")
    st.markdown("## About")
    st.caption("MarkItDown Prompt Studio v2.0")
    st.caption(f"Token estimation: {'tiktoken (cl100k_base)' if TIKTOKEN_AVAILABLE else 'character estimate (~4 chars/token)'}")
    st.caption(f"Supported formats: {SUPPORTED_FORMAT_LABEL}")


# ─── Footer ────────────────────────────────────────────────────────────────

st.markdown('<div class="app-footer">Powered by Microsoft MarkItDown · Prompt Studio v2.0</div>', unsafe_allow_html=True)
