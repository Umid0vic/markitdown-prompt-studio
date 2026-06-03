"""
Prompt templates for MarkItDown Prompt Studio.
Each template generates a structured prompt with clear sections.
"""

PROMPT_TYPES = [
    "General AI agent prompt",
    "Coding agent prompt",
    "Research prompt",
    "Summarization prompt",
    "Extraction prompt",
    "Requirements analysis prompt",
    "Test-case generation prompt",
    "System prompt",
    "RAG chunk prompt",
    "Custom prompt",
]

AGENT_ROLES = [
    "Expert assistant",
    "Senior software engineer",
    "Research analyst",
    "Product manager",
    "Technical writer",
    "Data analyst",
    "QA engineer",
    "Legal/document reviewer",
    "Custom role",
]

OUTPUT_FORMATS = [
    "Markdown",
    "JSON",
    "Table",
    "Bullet points",
    "Step-by-step plan",
    "Code",
    "Checklist",
    "Custom format",
]

DEFAULT_CONSTRAINTS = """- Be accurate and do not invent missing information.
- Use only the provided source context unless explicitly asked otherwise.
- If information is missing, say what is missing.
- Return a structured and useful answer."""

DEFAULT_SUCCESS_CRITERIA = """- The answer directly addresses the task.
- The answer is grounded in the source content.
- The answer follows the selected output format.
- The answer is clear, complete, and actionable."""


def _build_prompt(role: str, task: str, metadata: str, context: str,
                  constraints: str, output_format: str, success_criteria: str,
                  task_instructions: str = "") -> str:
    """Assemble a final prompt from sections."""
    sections = []
    sections.append(f"## Role\n\n{role}")
    sections.append(f"## Task\n\n{task}")
    if task_instructions:
        sections.append(f"## Instructions\n\n{task_instructions}")
    sections.append(f"## Source Metadata\n\n{metadata}")
    sections.append(f"## Source Context\n\n{context}")
    sections.append(f"## Constraints\n\n{constraints}")
    sections.append(f"## Output Format\n\n{output_format}")
    sections.append(f"## Success Criteria\n\n{success_criteria}")
    return '\n\n---\n\n'.join(sections)


def general_prompt(role, task, metadata, context, constraints, output_format, success_criteria):
    """General AI agent prompt."""
    instructions = (
        "You are a helpful AI assistant. Analyze the provided source context "
        "and complete the task as described. Be thorough, accurate, and structured."
    )
    return _build_prompt(role, task, metadata, context, constraints, output_format,
                         success_criteria, instructions)


def coding_prompt(role, task, metadata, context, constraints, output_format, success_criteria):
    """Coding agent prompt."""
    instructions = """- Inspect the provided context carefully.
- Infer implementation requirements from the source material.
- Produce code or implementation steps as appropriate.
- Identify missing files, dependencies, or assumptions.
- Do not hallucinate APIs, project structure, or library behavior.
- If you need to make assumptions, state them explicitly."""
    return _build_prompt(role, task, metadata, context, constraints, output_format,
                         success_criteria, instructions)


def research_prompt(role, task, metadata, context, constraints, output_format, success_criteria):
    """Research prompt."""
    instructions = """- Extract facts from the provided source context.
- Distinguish evidence from assumptions or opinions.
- Produce a structured research brief.
- Cite specific sections from the source when possible.
- Identify gaps or areas needing further research."""
    return _build_prompt(role, task, metadata, context, constraints, output_format,
                         success_criteria, instructions)


def summarization_prompt(role, task, metadata, context, constraints, output_format, success_criteria):
    """Summarization prompt."""
    instructions = """- Summarize the provided content concisely but thoroughly.
- Preserve key details including decisions, risks, dates, names, and action items.
- Maintain the logical structure of the source material.
- Highlight the most important points."""
    return _build_prompt(role, task, metadata, context, constraints, output_format,
                         success_criteria, instructions)


def extraction_prompt(role, task, metadata, context, constraints, output_format, success_criteria):
    """Extraction prompt."""
    instructions = """- Extract the requested entities, fields, requirements, tables, or data points from the source context.
- Use the specified output format strictly.
- If a requested item is not found, indicate it is missing.
- Be precise and do not add information not present in the source."""
    return _build_prompt(role, task, metadata, context, constraints, output_format,
                         success_criteria, instructions)


def requirements_prompt(role, task, metadata, context, constraints, output_format, success_criteria):
    """Requirements analysis prompt."""
    instructions = """- Identify functional requirements from the source context.
- Identify non-functional requirements.
- List assumptions made.
- List open questions that need clarification.
- Identify risks.
- Propose acceptance criteria where possible."""
    return _build_prompt(role, task, metadata, context, constraints, output_format,
                         success_criteria, instructions)


def test_generation_prompt(role, task, metadata, context, constraints, output_format, success_criteria):
    """Test-case generation prompt."""
    instructions = """- Generate test cases based on the source context.
- Include edge cases and boundary conditions.
- Include expected results for each test case.
- Map tests to source requirements where possible.
- Organize tests logically by feature or component."""
    return _build_prompt(role, task, metadata, context, constraints, output_format,
                         success_criteria, instructions)


def system_prompt_template(role, task, metadata, context, constraints, output_format, success_criteria):
    """System prompt generation."""
    instructions = """- Generate a reusable system prompt derived from the source context.
- The system prompt should define the AI agent's behavior, knowledge boundaries, and response style.
- Make it suitable for use as a persistent system message in a chat application."""
    return _build_prompt(role, task, metadata, context, constraints, output_format,
                         success_criteria, instructions)


def rag_chunk_prompt(role, task, metadata, context, constraints, output_format, success_criteria):
    """RAG chunk prompt."""
    instructions = """- Process this single document chunk as part of a larger retrieval-augmented generation workflow.
- Answer based only on the information in this chunk.
- If the chunk does not contain enough information to fully answer, state what is missing.
- Be precise and cite specific parts of the chunk."""
    return _build_prompt(role, task, metadata, context, constraints, output_format,
                         success_criteria, instructions)


def custom_prompt_from_template(template: str, role: str, task: str, context: str,
                                constraints: str, output_format: str,
                                success_criteria: str, metadata: str) -> str:
    """Fill a custom template with placeholders."""
    return template.format(
        role=role,
        task=task,
        context=context,
        constraints=constraints,
        output_format=output_format,
        success_criteria=success_criteria,
        metadata=metadata,
    )


# Map prompt type names to generator functions
TEMPLATE_MAP = {
    "General AI agent prompt": general_prompt,
    "Coding agent prompt": coding_prompt,
    "Research prompt": research_prompt,
    "Summarization prompt": summarization_prompt,
    "Extraction prompt": extraction_prompt,
    "Requirements analysis prompt": requirements_prompt,
    "Test-case generation prompt": test_generation_prompt,
    "System prompt": system_prompt_template,
    "RAG chunk prompt": rag_chunk_prompt,
}


class TemplateError(Exception):
    """Raised when a custom template has invalid placeholders."""
    pass


def generate_prompt(prompt_type: str, role: str, task: str, metadata: str,
                    context: str, constraints: str, output_format: str,
                    success_criteria: str, custom_template: str = "") -> str:
    """Generate a prompt using the appropriate template. Raises TemplateError for invalid custom templates."""
    if prompt_type == "Custom prompt" and custom_template:
        try:
            return custom_prompt_from_template(
                custom_template, role, task, context,
                constraints, output_format, success_criteria, metadata
            )
        except (KeyError, IndexError, ValueError) as e:
            raise TemplateError(
                f"Custom template has invalid placeholders: {e}"
            ) from e

    generator = TEMPLATE_MAP.get(prompt_type, general_prompt)
    return generator(role, task, metadata, context, constraints, output_format, success_criteria)
