"""
MarkItDown Prompt Studio
Convert files into Markdown and build clean prompts for AI agents.
Powered by Microsoft MarkItDown.
"""

import streamlit as st
import pandas as pd
import time
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

# ─── Page Config ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="MarkItDown Prompt Studio",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────

st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp {
        background-color: #0d0d0d;
        color: #f0f0f0;
    }
    section[data-testid="stSidebar"] {
        background-color: #111111;
        border-right: 1px solid #2a2a2a;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #ffffff;
    }
    .stTextArea textarea, .stTextInput input, .stSelectbox select {
        background-color: #1a1a1a !important;
        color: #f0f0f0 !important;
        border: 1px solid #333333 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stExpander"] {
        background-color: #141414;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
    }
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
    }
    div[data-testid="stMetric"] {
        background-color: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 10px;
        padding: 12px;
    }
    .stDownloadButton button {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stDownloadButton button:hover {
        background-color: #e0e0e0 !important;
    }
    .stButton button {
        border-radius: 8px !important;
        border: 1px solid #444 !important;
    }
    footer {
        visibility: hidden;
    }
    .app-footer {
        text-align: center;
        color: #666;
        padding: 2rem 0 1rem 0;
        font-size: 0.85rem;
        border-top: 1px solid #2a2a2a;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# ─── Session State Initialization ───────────────────────────────────────────

if "conversion_results" not in st.session_state:
    st.session_state.conversion_results = []
if "generated_prompts" not in st.session_state:
    st.session_state.generated_prompts = {}
if "edited_markdown" not in st.session_state:
    st.session_state.edited_markdown = {}
if "active_prompt_key" not in st.session_state:
    st.session_state.active_prompt_key = None


def format_duration(seconds: float) -> str:
    """Format a short duration for the UI."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, remaining = divmod(seconds, 60)
    return f"{int(minutes)}m {remaining:.0f}s"


def upload_size(uploaded_file) -> str:
    """Return a compact file size label."""
    size = getattr(uploaded_file, "size", 0) or 0
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size} B"

# ─── Sidebar ────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("# 📝 MarkItDown Prompt Studio")
    st.markdown("*Convert files into Markdown and build clean prompts for AI agents.*")
    st.markdown("---")

    st.markdown("**Workflow Settings**")

    mode = st.radio("Mode", ["Single file", "Batch files"], key="mode_radio")
    if st.button("Clear session", key="clear_session_btn"):
        st.session_state.conversion_results = []
        st.session_state.generated_prompts = {}
        st.session_state.edited_markdown = {}
        st.session_state.active_prompt_key = None
        st.rerun()

    st.markdown("---")
    st.markdown("**Prompt Settings**")

    prompt_type = st.selectbox("Prompt type", PROMPT_TYPES, key="prompt_type_select")

    agent_role = st.selectbox("Agent role", AGENT_ROLES, key="agent_role_select")
    custom_role = ""
    if agent_role == "Custom role":
        custom_role = st.text_input("Custom role", key="custom_role_input")

    output_format = st.selectbox("Output format", OUTPUT_FORMATS, key="output_format_select")
    custom_format = ""
    if output_format == "Custom format":
        custom_format = st.text_input("Custom format", key="custom_format_input")

    st.markdown("---")
    st.markdown("**Context Preprocessing**")

    context_modes = [
        "Use full document",
        "Remove excessive blank lines",
        "Use first N characters",
        "Extract headings only",
        "Extract code blocks only",
        "Extract tables only if possible",
    ]
    context_mode = st.selectbox("Context mode", context_modes, key="context_mode_select")

    max_chars = 20000
    if context_mode == "Use first N characters":
        max_chars = st.number_input("Max characters", min_value=100, value=20000, step=1000, key="max_chars_input")

    st.markdown("---")
    st.markdown("**Chunking**")

    enable_chunking = st.toggle("Enable chunking", value=False, key="chunking_toggle")
    chunk_size = 4000
    chunk_overlap = 200
    if enable_chunking:
        chunk_size = st.number_input("Chunk size (tokens)", min_value=100, value=4000, step=500, key="chunk_size_input")
        chunk_overlap = st.number_input("Chunk overlap (tokens)", min_value=0, value=200, step=50, key="chunk_overlap_input")
        if chunk_overlap >= chunk_size:
            st.warning("Overlap must be less than chunk size. It will be clamped automatically.")

    st.markdown("---")

    with st.expander("📚 Resources"):
        st.markdown("""
- [MarkItDown GitHub](https://github.com/microsoft/markitdown)
- [MarkItDown PyPI](https://pypi.org/project/markitdown/)
- [Streamlit Docs](https://docs.streamlit.io/)
- [tiktoken](https://github.com/openai/tiktoken)
        """)

    st.markdown("---")
    st.caption(f"Supported formats: {SUPPORTED_FORMAT_LABEL}.")
    token_method = "tiktoken (cl100k_base)" if TIKTOKEN_AVAILABLE else "character estimate (1 token ≈ 4 chars)"
    st.caption(f"Token estimation: {token_method}")

# ─── Main Area ──────────────────────────────────────────────────────────────

st.markdown("# MarkItDown Prompt Studio")
st.markdown("Convert files into Markdown and build clean prompts for AI agents.")
st.caption(f"Supported formats: {SUPPORTED_FORMAT_LABEL}.")

# ─── Upload Section ─────────────────────────────────────────────────────────

st.markdown("## 📁 Upload Files")

accept_multiple = mode == "Batch files"
uploaded_files = st.file_uploader(
    "Drag and drop files here",
    accept_multiple_files=accept_multiple,
    key="file_uploader",
    type=SUPPORTED_FILE_TYPES,
    help=f"Supported formats: {SUPPORTED_FORMAT_LABEL}.",
)

# Normalize to list
if uploaded_files is None:
    uploaded_files = []
elif not isinstance(uploaded_files, list):
    uploaded_files = [uploaded_files]

# ─── Conversion ─────────────────────────────────────────────────────────────

if uploaded_files:
    if st.button("🔄 Convert", type="primary", key="convert_btn"):
        results = []
        used_names = set()
        total = len(uploaded_files)
        started_at = time.perf_counter()
        live_rows = []

        with st.status(f"Converting {total} file{'s' if total > 1 else ''}...", expanded=True) as status:
            progress = st.progress(0, text="Preparing conversion queue...")
            metric_cols = st.columns(4)
            current_box = st.empty()
            table_box = st.empty()

            for f in uploaded_files:
                live_rows.append({
                    "File": f.name,
                    "Size": upload_size(f),
                    "Status": "Queued",
                    "Characters": "",
                    "Tokens": "",
                    "Duration": "",
                    "Message": "",
                })

            table_box.dataframe(pd.DataFrame(live_rows), use_container_width=True, hide_index=True)

            for i, f in enumerate(uploaded_files):
                elapsed = time.perf_counter() - started_at
                percent = i / total
                progress.progress(percent, text=f"[{i + 1}/{total}] Converting {f.name}")
                current_box.info(f"Working on {f.name}. Elapsed: {format_duration(elapsed)}")
                live_rows[i]["Status"] = "Converting"
                live_rows[i]["Message"] = "Reading file and running MarkItDown"
                table_box.dataframe(pd.DataFrame(live_rows), use_container_width=True, hide_index=True)

                with metric_cols[0]:
                    st.metric("Files done", f"{i}/{total}")
                with metric_cols[1]:
                    st.metric("Current file", f.name)
                with metric_cols[2]:
                    st.metric("Elapsed", format_duration(elapsed))
                with metric_cols[3]:
                    st.metric("Progress", f"{percent * 100:.0f}%")

                result = convert_file(f)
                # Deduplicate output filenames
                safe = sanitize_filename(f.name)
                result["output_filename"] = deduplicate_filename(safe, used_names) + ".md"
                results.append(result)

                live_rows[i]["Status"] = "Done" if result["status"] == "success" else ("Warning" if result["status"] == "warning" else "Error")
                live_rows[i]["Characters"] = f"{result['char_count']:,}"
                live_rows[i]["Tokens"] = f"{result['token_count']:,}"
                live_rows[i]["Duration"] = format_duration(result.get("duration_seconds", 0))
                live_rows[i]["Message"] = result["error"] or "Converted successfully"
                table_box.dataframe(pd.DataFrame(live_rows), use_container_width=True, hide_index=True)

            elapsed = time.perf_counter() - started_at
            progress.progress(1.0, text=f"Done in {format_duration(elapsed)}")
            success_count = sum(1 for r in results if r["status"] != "error")
            current_box.success(f"Finished {success_count}/{total} files in {format_duration(elapsed)}.")
            status.update(label=f"Converted {success_count}/{total} files", state="complete", expanded=False)

        st.session_state.conversion_results = results
        # Initialize edited markdown using deduplicated output_filename as key
        for r in results:
            if r["status"] != "error":
                st.session_state.edited_markdown[r["output_filename"]] = r["markdown"]

# ─── Conversion Results ─────────────────────────────────────────────────────

results = st.session_state.conversion_results

if results:
    st.markdown("## 📊 Conversion Results")

    if len(results) > 1:
        df = pd.DataFrame([{
            "Filename": r["filename"],
            "Status": "✓" if r["status"] == "success" else ("⚠" if r["status"] == "warning" else "✗"),
            "Output": r["output_filename"],
            "Error": r["error"],
            "Characters": r["char_count"],
            "Est. Tokens": r["token_count"],
        } for r in results])
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ─── Markdown Preview/Editor ────────────────────────────────────────────

    st.markdown("## 📄 Markdown Preview & Editor")

    successful = [r for r in results if r["status"] != "error"]

    if not successful:
        st.warning("No files were converted successfully.")
    else:
        if len(successful) == 1:
            r = successful[0]
            key = r["output_filename"]
            tab_preview, tab_raw = st.tabs(["Preview", "Raw Editor"])
            with tab_preview:
                st.markdown(st.session_state.edited_markdown.get(key, r["markdown"]))
            with tab_raw:
                edited = st.text_area(
                    "Edit Markdown",
                    value=st.session_state.edited_markdown.get(key, r["markdown"]),
                    height=400,
                    key=f"editor_{key}",
                )
                st.session_state.edited_markdown[key] = edited

            col1, col2 = st.columns(2)
            with col1:
                md_content = st.session_state.edited_markdown.get(key, r["markdown"])
                st.download_button(
                    "⬇ Download .md",
                    data=md_content,
                    file_name=r["output_filename"],
                    mime="text/markdown",
                    key="dl_single_md",
                )
            with col2:
                chars = len(md_content)
                tokens = estimate_tokens(md_content)
                st.metric("Characters", f"{chars:,}")
                st.metric("Estimated Tokens", f"{tokens:,}")
        else:
            # Batch mode tabs per file — use output_filename for unique tabs/keys
            file_tabs = st.tabs([r["output_filename"] for r in successful])
            for tab, r in zip(file_tabs, successful):
                key = r["output_filename"]
                with tab:
                    tab_preview, tab_raw = st.tabs(["Preview", "Raw Editor"])
                    with tab_preview:
                        st.markdown(st.session_state.edited_markdown.get(key, r["markdown"]))
                    with tab_raw:
                        edited = st.text_area(
                            "Edit Markdown",
                            value=st.session_state.edited_markdown.get(key, r["markdown"]),
                            height=300,
                            key=f"editor_{key}",
                        )
                        st.session_state.edited_markdown[key] = edited

            # Batch download
            zip_files = {}
            for r in successful:
                key = r["output_filename"]
                content = st.session_state.edited_markdown.get(key, r["markdown"])
                zip_files[r["output_filename"]] = content

            st.download_button(
                "⬇ Download all as ZIP",
                data=create_zip(zip_files),
                file_name="markitdown_converted.zip",
                mime="application/zip",
                key="dl_batch_zip",
            )

    # ─── Prompt Builder ─────────────────────────────────────────────────────

    st.markdown("---")
    st.markdown("## 🛠️ Prompt Builder")

    task_input = st.text_area(
        "Task",
        placeholder="Example: Analyze this document and create a detailed implementation plan.",
        height=120,
        key="task_input",
    )

    constraints_input = st.text_area(
        "Constraints",
        value=DEFAULT_CONSTRAINTS,
        height=150,
        key="constraints_input",
    )

    success_criteria_input = st.text_area(
        "Success Criteria",
        value=DEFAULT_SUCCESS_CRITERIA,
        height=150,
        key="success_criteria_input",
    )

    custom_template = ""
    if prompt_type == "Custom prompt":
        st.markdown("**Custom Template**")
        st.caption("Placeholders: {role}, {task}, {context}, {constraints}, {output_format}, {success_criteria}, {metadata}")
        custom_template = st.text_area(
            "Template",
            value="## Role\n{role}\n\n## Task\n{task}\n\n## Context\n{context}\n\n## Constraints\n{constraints}\n\n## Output Format\n{output_format}\n\n## Success Criteria\n{success_criteria}\n\n## Metadata\n{metadata}",
            height=250,
            key="custom_template_input",
        )

    # Batch prompt mode
    batch_prompt_mode = "separate"
    if len(successful) > 1:
        batch_prompt_mode = st.radio(
            "Batch prompt mode",
            ["Separate prompt per file", "Combined prompt from all files"],
            key="batch_prompt_mode",
        )
        batch_prompt_mode = "combined" if "Combined" in batch_prompt_mode else "separate"

    # ─── Generate Prompt ────────────────────────────────────────────────────

    if st.button("✨ Generate Prompt", type="primary", key="generate_prompt_btn"):
        if not successful:
            st.error("No converted files available. Please upload and convert files first.")
        elif not task_input.strip():
            st.error("Please enter a task description.")
        else:
            role_text = custom_role if agent_role == "Custom role" else agent_role
            format_text = custom_format if output_format == "Custom format" else output_format

            if not role_text.strip():
                st.error("Please specify a role.")
            elif not format_text.strip():
                st.error("Please specify an output format.")
            else:
                generated_prompts = {}
                prompt_names_used = set()
                generation_error = False

                try:
                    if batch_prompt_mode == "combined" and len(successful) > 1:
                        # Combine all contexts
                        combined_context_parts = []
                        combined_chars = 0
                        for idx, r in enumerate(successful, 1):
                            key = r["output_filename"]
                            md = st.session_state.edited_markdown.get(key, r["markdown"])
                            processed = preprocess_context(md, context_mode, max_chars)
                            combined_context_parts.append(f"# Source {idx}: {r['filename']}\n\n{processed}")
                            combined_chars += len(processed)

                        combined_context = "\n\n---\n\n".join(combined_context_parts)
                        combined_tokens = estimate_tokens(combined_context)

                        metadata_text = create_metadata(
                            filename=f"{len(successful)} files combined",
                            extension="multiple",
                            char_count=combined_chars,
                            token_count=combined_tokens,
                            context_mode=context_mode,
                        )

                        prompt = generate_prompt(
                            prompt_type, role_text, task_input, metadata_text,
                            combined_context, constraints_input, format_text,
                            success_criteria_input, custom_template,
                        )
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
                                filename=r["filename"],
                                extension=ext,
                                char_count=chars,
                                token_count=tokens,
                                context_mode=context_mode,
                                batch_index=idx if len(successful) > 1 else None,
                            )

                            prompt = generate_prompt(
                                prompt_type, role_text, task_input, metadata_text,
                                processed, constraints_input, format_text,
                                success_criteria_input, custom_template,
                            )
                            safe = sanitize_filename(r["filename"])
                            prompt_fname = deduplicate_filename(f"{safe}.prompt", prompt_names_used) + ".md"
                            generated_prompts[prompt_fname] = prompt

                except TemplateError as e:
                    st.error(f"Template error: {e}")
                    generation_error = True

                if not generation_error:
                    st.session_state.generated_prompts = generated_prompts
                    st.session_state.active_prompt_key = list(generated_prompts.keys())[0]
                    st.success("Prompt generated!")

    # ─── Chunking ──────────────────────────────────────────────────────────

    if enable_chunking and successful:
        st.markdown("---")
        st.markdown("## 🧩 Chunking")

        # Use first successful file for single mode, or combined for batch
        if len(successful) == 1:
            key = successful[0]["output_filename"]
            source_md = st.session_state.edited_markdown.get(key, successful[0]["markdown"])
            source_name = successful[0]["filename"]
        else:
            parts = []
            for r in successful:
                key = r["output_filename"]
                md = st.session_state.edited_markdown.get(key, r["markdown"])
                parts.append(f"# {r['filename']}\n\n{md}")
            source_md = "\n\n---\n\n".join(parts)
            source_name = "combined"

        processed_for_chunking = preprocess_context(source_md, context_mode, max_chars)
        chunks = chunk_text(processed_for_chunking, chunk_size, chunk_overlap)

        st.metric("Total Chunks", len(chunks))

        chunk_data = []
        for i, c in enumerate(chunks, 1):
            chunk_data.append({
                "Chunk": i,
                "Characters": len(c),
                "Est. Tokens": estimate_tokens(c),
            })
        st.dataframe(pd.DataFrame(chunk_data), use_container_width=True, hide_index=True)

        # Preview chunks
        with st.expander("Preview Chunks"):
            for i, c in enumerate(chunks, 1):
                st.markdown(f"**Chunk {i}**")
                st.text(c[:500] + ("..." if len(c) > 500 else ""))
                st.markdown("---")

        # Generate chunk prompts
        if st.button("Generate Chunk Prompts", key="gen_chunk_prompts_btn"):
            role_text = custom_role if agent_role == "Custom role" else agent_role
            format_text = custom_format if output_format == "Custom format" else output_format

            if not task_input.strip():
                st.error("Please enter a task description for chunk prompts.")
            elif not role_text.strip():
                st.error("Please specify a role.")
            else:
                chunk_prompts = {}
                for i, c in enumerate(chunks, 1):
                    ext = Path(source_name).suffix if source_name != "combined" else ".md"
                    metadata_text = create_metadata(
                        filename=source_name,
                        extension=ext,
                        char_count=len(c),
                        token_count=estimate_tokens(c),
                        context_mode=context_mode,
                        chunk_number=i,
                        total_chunks=len(chunks),
                    )
                    prompt = generate_prompt(
                        prompt_type, role_text, task_input, metadata_text,
                        c, constraints_input, format_text,
                        success_criteria_input, custom_template,
                    )
                    safe = sanitize_filename(source_name)
                    chunk_prompts[f"{safe}.chunk-{i:03d}.prompt.md"] = prompt

                st.session_state.chunk_prompts = chunk_prompts
                st.success(f"Generated {len(chunk_prompts)} chunk prompts.")

                st.download_button(
                    "⬇ Download chunk prompts as ZIP",
                    data=create_zip(chunk_prompts),
                    file_name="chunk_prompts.zip",
                    mime="application/zip",
                    key="dl_chunk_zip",
                )

    # ─── Final Prompt Output ────────────────────────────────────────────────

    if st.session_state.generated_prompts:
        st.markdown("---")
        st.markdown("## 📋 Final Prompt")

        gen_prompts = st.session_state.generated_prompts
        prompt_keys = list(gen_prompts.keys())

        # Select which prompt to view/edit
        if len(prompt_keys) > 1:
            selected_key = st.selectbox(
                "Select prompt",
                prompt_keys,
                index=prompt_keys.index(st.session_state.active_prompt_key) if st.session_state.active_prompt_key in prompt_keys else 0,
                key="prompt_selector",
            )
        else:
            selected_key = prompt_keys[0]

        st.session_state.active_prompt_key = selected_key
        prompt_text = gen_prompts[selected_key]
        prompt_tokens = estimate_tokens(prompt_text)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Prompt Characters", f"{len(prompt_text):,}")
        with col2:
            st.metric("Prompt Tokens", f"{prompt_tokens:,}")

        warning = token_warning(prompt_tokens)
        if warning:
            st.warning(warning)

        # ─── Quality Checklist (before export) ──────────────────────────────

        st.markdown("### ✅ Prompt Quality Checklist")

        role_text = custom_role if agent_role == "Custom role" else agent_role
        format_text = custom_format if output_format == "Custom format" else output_format

        checks = quality_checklist(
            role=role_text,
            task=task_input,
            context=prompt_text,
            output_format=format_text,
            constraints=constraints_input,
            success_criteria=success_criteria_input,
            filename=successful[0]["filename"] if successful else "",
            token_count=prompt_tokens,
        )

        for label, status in checks:
            if status == "pass":
                st.markdown(f"✓ {label}")
            else:
                st.markdown(f"⚠ {label}")

        st.markdown("---")

        # Preview / Edit
        tab_preview, tab_raw = st.tabs(["Preview", "Raw Editor"])
        with tab_preview:
            st.markdown(prompt_text)
        with tab_raw:
            edited_prompt = st.text_area(
                "Edit Prompt",
                value=prompt_text,
                height=400,
                key=f"prompt_editor_{selected_key}",
            )
            # Write edits back to the generated_prompts dict
            st.session_state.generated_prompts[selected_key] = edited_prompt
            prompt_text = edited_prompt

        # Export buttons
        st.markdown("**Export**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "⬇ Download .md",
                data=prompt_text,
                file_name=selected_key,
                mime="text/markdown",
                key="dl_prompt_md",
            )
        with col2:
            txt_name = selected_key.rsplit(".", 1)[0] + ".txt"
            st.download_button(
                "⬇ Download .txt",
                data=prompt_text,
                file_name=txt_name,
                mime="text/plain",
                key="dl_prompt_txt",
            )
        with col3:
            if len(gen_prompts) > 1:
                st.download_button(
                    "⬇ All prompts as ZIP",
                    data=create_zip(st.session_state.generated_prompts),
                    file_name="prompts.zip",
                    mime="application/zip",
                    key="dl_all_prompts_zip",
                )

# ─── Footer ────────────────────────────────────────────────────────────────

st.markdown('<div class="app-footer">Powered by Microsoft MarkItDown</div>', unsafe_allow_html=True)
