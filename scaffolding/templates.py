"""
Starter code templates for different types of assignments.
"""
import json
import os
import re
from html import unescape
from typing import Any, Dict, List, Optional


def html_to_markdown(html: str) -> str:
    """
    Convert HTML assignment content to readable Markdown.

    Handles common Canvas HTML patterns: headings, paragraphs, lists,
    bold/italic, links, code blocks, and tables.
    """
    if not html:
        return ""

    text = html

    # Decode HTML entities
    text = unescape(text)

    # Remove <style> and <link> tags and their content
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<link[^>]*/?>', '', text)

    # Headings
    for i in range(1, 7):
        text = re.sub(
            rf'<h{i}[^>]*>(.*?)</h{i}>',
            lambda m, lvl=i: f"\n{'#' * lvl} {m.group(1).strip()}\n",
            text, flags=re.DOTALL,
        )

    # Bold / italic
    text = re.sub(r'<(strong|b)>(.*?)</\1>', r'**\2**', text, flags=re.DOTALL)
    text = re.sub(r'<(em|i)>(.*?)</\1>', r'*\2*', text, flags=re.DOTALL)

    # Code blocks
    text = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', r'\n```\n\1\n```\n', text, flags=re.DOTALL)
    text = re.sub(r'<code>(.*?)</code>', r'`\1`', text, flags=re.DOTALL)

    # Links
    text = re.sub(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)

    # Images
    text = re.sub(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"[^>]*/?>',  r'![\2](\1)', text)
    text = re.sub(r'<img[^>]+src="([^"]+)"[^>]*/?>',  r'![image](\1)', text)

    # Lists
    text = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', text, flags=re.DOTALL)
    text = re.sub(r'</?[ou]l[^>]*>', '\n', text)

    # Paragraphs and line breaks
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<p[^>]*>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL)
    text = re.sub(r'<hr\s*/?>', '\n---\n', text)

    # Table support (basic)
    text = re.sub(r'<tr[^>]*>(.*?)</tr>', lambda m: '| ' + m.group(1) + '\n', text, flags=re.DOTALL)
    text = re.sub(r'<t[hd][^>]*>(.*?)</t[hd]>', r'\1 | ', text, flags=re.DOTALL)
    text = re.sub(r'</?table[^>]*>', '\n', text)
    text = re.sub(r'</?thead[^>]*>', '', text)
    text = re.sub(r'</?tbody[^>]*>', '', text)

    # Strip remaining tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return text


def build_course_context_markdown(course_context: List[Dict[str, Any]]) -> str:
    """Render retrieved course-context chunks into a companion markdown file."""
    lines = [
        "# Course Context",
        "",
        "This file contains relevant excerpts retrieved from course reference material.",
        "",
    ]

    for index, item in enumerate(course_context, start=1):
        title = item.get("section_title") or item.get("document_name") or f"Match {index}"
        lines.append(f"## Match {index}: {title}")
        document_name = item.get("document_name")
        if document_name:
            lines.append(f"- Source: {document_name}")
        distance = item.get("distance")
        if distance is not None:
            lines.append(f"- Distance: {distance:.4f}")
        lines.append("")
        lines.append(item.get("text", "").strip())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"

def normalize_slug(name: str) -> str:
    """
    Convert a name to a valid slug for repository names.
    
    Args:
        name: The assignment or project name
        
    Returns:
        A normalized slug suitable for repository names
    """
    # Convert to lowercase
    slug = name.lower()
    # Replace any sequence of non-alphanumeric characters with a single hyphen
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    return slug


PYTHON_TEMPLATES = {
    "README.md": """# {assignment_name}

## Overview
This repository contains starter code for this assignment.

## Full Assignment
See `ASSIGNMENT.md` for the complete assignment brief.

## Due Date
{due_date}

## Setup
```bash
pip install -r requirements.txt
```

## Running Tests
```bash
pytest
```

## Submission
Complete the implementation in `main.py` and ensure all tests pass.
""",
    "requirements.txt": """pytest>=7.4.0
""",
    "main.py": """\"\"\"
{assignment_name}

{assignment_description}
\"\"\"


def main():
    \"\"\"Main function - implement your solution here.\"\"\"
    pass


if __name__ == "__main__":
    main()
""",
    "tests/test_main.py": """\"\"\"
Tests for {assignment_name}
\"\"\"
import pytest
from main import main


def test_main():
    \"\"\"Test the main function.\"\"\"
    # TODO: Add your test cases here
    pass
""",
    ".gitignore": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
venv/
env/
.env
"""
}

R_TEMPLATES = {
    "README.md": """# {assignment_name}

## Overview
This repository contains starter code for this assignment.

## Full Assignment
See `ASSIGNMENT.md` for the complete assignment brief.

## Due Date
{due_date}

## Setup
Ensure you have R installed.

## Running
```bash
Rscript main.R
```

## Testing
```bash
Rscript tests/test_main.R
```

## Submission
Complete the implementation in `main.R` and ensure all tests pass.
""",
    "main.R": """# {assignment_name}
#
# {assignment_description}

main <- function() {{
  invisible(NULL)
}}

if (sys.nframe() == 0) {{
  main()
}}
""",
    "tests/test_main.R": """source("main.R")

stopifnot(exists("main"))
stopifnot(is.function(main))
""",
    ".gitignore": """# R
.Rhistory
.RData
.Rproj.user/
.Ruserdata
renv/library/
"""
}

# Map of language/type keywords to templates
TEMPLATE_MAP = {
    "python": PYTHON_TEMPLATES,
    "py": PYTHON_TEMPLATES,
    "r": R_TEMPLATES,
    "rscript": R_TEMPLATES,
}

SOURCE_FILE_BY_LANGUAGE = {
    "python": "main.py",
    "py": "main.py",
    "r": "main.R",
    "rscript": "main.R",
}

PYTHON_NOTEBOOK_LIBRARY_RULES = [
    {
        "patterns": [
            r"\bbayes(?:ian)?(?:\s+theorem)?\b",
            r"\bprior\b",
            r"\bposterior\b",
        ],
        "requirement": "scipy>=1.11.0",
        "imports": ["from scipy.stats import beta"],
    },
]

PYTHON_LIBRARY_RULES = [
    {
        "patterns": [r"\bnumpy\b"],
        "requirement": "numpy>=1.26.0",
        "imports": ["import numpy as np"],
    },
    {
        "patterns": [r"\bpandas\b"],
        "requirement": "pandas>=2.2.0",
        "imports": ["import pandas as pd"],
    },
    {
        "patterns": [r"\bmatplotlib(?:\.pyplot)?\b", r"\bpyplot\b"],
        "requirement": "matplotlib>=3.8.0",
        "imports": ["import matplotlib.pyplot as plt"],
    },
    {
        "patterns": [r"\bseaborn\b"],
        "requirement": "seaborn>=0.13.0",
        "imports": ["import seaborn as sns"],
    },
    {
        "patterns": [r"\bscipy\b"],
        "requirement": "scipy>=1.11.0",
        "imports": ["import scipy"],
    },
    {
        "patterns": [r"\bscikit-learn\b", r"\bsklearn\b"],
        "requirement": "scikit-learn>=1.4.0",
        "imports": ["import sklearn"],
    },
    {
        "patterns": [r"\brequests\b"],
        "requirement": "requests>=2.31.0",
        "imports": ["import requests"],
    },
    {
        "patterns": [r"\bbeautifulsoup4\b", r"\bbs4\b", r"\bbeautiful\s+soup\b"],
        "requirement": "beautifulsoup4>=4.12.0",
        "imports": ["from bs4 import BeautifulSoup"],
    },
]


def get_template_for_language(language: str) -> dict:
    """
    Get the appropriate template based on the language/type.
    
    Args:
        language: Programming language or assignment type
        
    Returns:
        Dictionary of file templates
    """
    language_lower = language.lower()
    
    # First, try exact match
    if language_lower in TEMPLATE_MAP:
        return TEMPLATE_MAP[language_lower]
    
    # Then try partial matches, prioritizing longer keys first.
    sorted_keys = sorted(TEMPLATE_MAP.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in language_lower:
            return TEMPLATE_MAP[key]
    
    # Default to Python if no match
    return PYTHON_TEMPLATES


def build_agent_fact_card(
    agent_id: str,
    agent_name: str,
    summary: str,
    domain: str,
    capabilities: List[str],
    registry_url: str = "",
    source_repository: str = "",
    mcp_locator: str = "#registry:server-name",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a provisional NANDA/NEST Agent Fact Card payload.

    This schema is intentionally minimal until the official registry schema is
    confirmed. It captures assignment-aligned metadata and interoperability hints.
    """
    clean_capabilities = [c for c in capabilities if c]
    return {
        "schema_version": "0.1-draft",
        "agent_id": normalize_slug(agent_id),
        "name": agent_name,
        "summary": summary,
        "domain": domain,
        "capabilities": clean_capabilities,
        "interoperability": {
            "a2a": "@agent-id",
            "mcp": mcp_locator,
        },
        "registry": {
            "url": registry_url,
            "status": "not_registered",
        },
        "source_repository": source_repository,
        "metadata": metadata or {},
    }


def build_service_fact_card() -> Dict[str, Any]:
    """Build the service-level fact card for the current workflow app."""
    return build_agent_fact_card(
        agent_id="canvas-assignment-workflow",
        agent_name="Canvas Assignment Workflow",
        summary=(
            "Fetches Canvas assignments, infers coding vs writing work, creates "
            "GitHub repositories for coding assignments, and creates Notion pages "
            "for writing assignments."
        ),
        domain="education automation",
        capabilities=[
            "list_courses",
            "list_assignments",
            "fetch_assignment",
            "infer_assignment_type",
            "list_course_modules",
            "search_course_modules",
            "ingest_course_document",
            "search_course_context",
            "discover_agents",
            "plan_assignment",
            "resume_task",
            "list_agent_scorecards",
            "list_task_steps",
            "list_task_artifacts",
            "create_github_repository",
            "generate_starter_files",
            "create_notion_page",
        ],
        registry_url="https://index.projectnanda.org",
        source_repository="https://github.com/willdaly/canvas-github-agent",
        mcp_locator="canvas-github-agent-mcp",
        metadata={
            "version": "0.1.0",
            "runtime": "python>=3.10",
            "entrypoint": "app/agent.py",
            "mcp_entrypoint": "app/mcp_server.py",
            "mcp_stdio_command": "canvas-github-agent-mcp",
            "architecture": "deterministic workflow orchestrator",
            "inputs": [
                "course_id",
                "assignment_id (optional)",
                "language",
                "assignment_type (optional)",
                "notion_content_mode (optional)",
            ],
            "outputs": [
                "agent discovery payloads for delegation candidate selection",
                "assignment planning payloads for pre-execution analysis",
                "agent scorecard payloads for delegation ranking feedback",
                "execution step payloads for persisted task tracing",
                "github repository metadata and URL for coding assignments",
                "notion page metadata and URL for writing assignments",
            ],
            "tools_used": [
                "CanvasTools",
                "CourseContextTools",
                "GitHubTools",
                "NotionTools",
            ],
            "constraints": [
                "requires Canvas credentials",
                "requires GitHub credentials for coding assignment flow",
                "requires Notion credentials for writing assignment flow",
            ],
            "supported_languages": ["python", "r"],
            "course_context_backend": "chroma",
            "course_context_parser": "docling",
            "course_context_sources": ["canvas_modules", "chroma_documents"],
            "supported_course_document_formats": ["pdf"],
            "notebook_support": "python notebook scaffolding for assignments that explicitly require Jupyter notebook submission",
        },
    )


def build_service_oasf_record(service_base_url: Optional[str] = None) -> Dict[str, Any]:
    """Build a minimal OASF 1.0.0 record for the current workflow app."""
    source_repository = "https://github.com/willdaly/canvas-github-agent"
    resolved_service_base_url = (
        service_base_url
        or os.getenv("SERVICE_BASE_URL", "http://localhost:8000").strip()
        or "http://localhost:8000"
    ).rstrip("/")
    return {
        "name": "Canvas Assignment Workflow",
        "version": "0.1.0",
        "schema_version": "1.0.0",
        "description": (
            "Fetches Canvas assignments, infers coding vs writing work, creates "
            "GitHub repositories for coding assignments, and creates Notion pages "
            "for writing assignments."
        ),
        "authors": ["Will Daly"],
        "created_at": "2026-03-20T00:00:00Z",
        "skills": [
            {"id": 1001, "name": "agent_orchestration/task_decomposition"},
            {
                "id": 10101,
                "name": (
                    "natural_language_processing/"
                    "natural_language_understanding/contextual_comprehension"
                )
            },
            {
                "id": 10301,
                "name": (
                    "natural_language_processing/"
                    "information_retrieval_synthesis/fact_extraction"
                )
            },
        ],
        "domains": [
            {
                "id": 10204,
                "name": "technology/software_engineering/apis_integration",
            },
        ],
        "locators": [
            {
                "type": "source_code",
                "urls": [source_repository],
            },
            {
                "type": "url",
                "urls": [
                    f"{resolved_service_base_url}/metadata/oasf-record",
                    f"{resolved_service_base_url}/capabilities",
                ],
            },
        ],
        "annotations": {
            "architecture": "deterministic workflow orchestrator",
            "api_base_url": resolved_service_base_url,
            "capabilities_endpoint": f"{resolved_service_base_url}/capabilities",
            "coding_destination": "github",
            "create_endpoint": f"{resolved_service_base_url}/create",
            "course_context_backend": "chroma",
            "course_context_document_listing_endpoint": f"{resolved_service_base_url}/courses/{{course_id}}/documents",
            "course_context_ingest_endpoint": f"{resolved_service_base_url}/courses/{{course_id}}/documents/ingest",
            "course_context_parser": "docling",
            "course_context_search_endpoint": f"{resolved_service_base_url}/courses/{{course_id}}/context/search",
            "course_context_sources": "canvas_modules,chroma_documents",
            "course_module_listing_endpoint": f"{resolved_service_base_url}/courses/{{course_id}}/modules",
            "course_module_search_endpoint": f"{resolved_service_base_url}/courses/{{course_id}}/modules/search",
            "discover_agents_endpoint": f"{resolved_service_base_url}/discover-agents",
            "entrypoint": "app/agent.py",
            "health_endpoint": f"{resolved_service_base_url}/health",
            "invocation_mode": "supports synchronous planning, synchronous request-response, and asynchronous task polling",
            "mcp_entrypoint": "app/mcp_server.py",
            "mcp_server_name": "canvas-assignment-workflow",
            "mcp_stdio_command": "canvas-github-agent-mcp",
            "mcp_capabilities_resource": "canvas-assignment-workflow://capabilities",
            "mcp_oasf_resource": "canvas-assignment-workflow://metadata/oasf-record",
            "notebook_support": (
                "python notebook scaffolding when assignment text explicitly "
                "requires Jupyter notebook submission"
            ),
            "discovery_schema": "agent_candidate_v1",
            "plan_endpoint": f"{resolved_service_base_url}/plan",
            "planning_schema": "assignment_plan_v1",
            "result_schema": "task_result_v1",
            "runtime": "python>=3.10",
            "scorecards_endpoint": f"{resolved_service_base_url}/agents/scorecards",
            "scorecard_schema": "agent_scorecard_v1",
            "supported_languages": "python,r",
            "task_artifacts_endpoint": f"{resolved_service_base_url}/tasks/{{task_id}}/artifacts",
            "task_resume_endpoint": f"{resolved_service_base_url}/tasks/{{task_id}}/resume",
            "task_steps_endpoint": f"{resolved_service_base_url}/tasks/{{task_id}}/steps",
            "task_step_schema": "execution_step_v1",
            "task_status_endpoint": f"{resolved_service_base_url}/tasks/{{task_id}}",
            "task_status_schema": "task_status_v1",
            "task_submission_endpoint": f"{resolved_service_base_url}/tasks",
            "writing_destination": "notion",
        },
    }


def extract_required_filenames(assignment_description: str) -> List[str]:
    """Extract explicit required filenames from assignment text."""
    if not assignment_description:
        return []

    text = assignment_description
    filenames: List[str] = []

    explicit_patterns = [
        r"must be named\s+([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)",
        r"file called\s+`?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`?",
        r"include\s+a\s+file\s+named\s+`?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`?",
    ]
    for pattern in explicit_patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            filenames.append(match.strip())

    for match in re.findall(r"`([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)`", text):
        filenames.append(match.strip())

    common_ext_pattern = (
        r"\b([A-Za-z0-9_./-]+\."
        r"(?:py|ipynb|r|rmd|txt|md|json|ya?ml|csv))\b"
    )
    for match in re.findall(common_ext_pattern, text, flags=re.IGNORECASE):
        filenames.append(match.strip())

    unique: List[str] = []
    seen = set()
    for filename in filenames:
        key = filename.lower()
        if key not in seen:
            seen.add(key)
            unique.append(filename)
    return unique


def extract_required_function_names(assignment_description: str) -> List[str]:
    """Extract required function names from assignment text."""
    if not assignment_description:
        return []

    candidates: List[str] = []

    candidates.extend(
        re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", assignment_description)
    )
    candidates.extend(
        re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", assignment_description)
    )

    phrase_patterns = [
        r"function names?\s*:\s*([^\.\n]+)",
        r"functions?\s+(?:named|called)\s+([^\.\n]+)",
        r"implement\s+(?:the\s+)?functions?\s+([^\.\n]+)",
    ]
    for pattern in phrase_patterns:
        for block in re.findall(pattern, assignment_description, flags=re.IGNORECASE):
            candidates.extend(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", block))

    filtered = []
    seen = set()
    ignored = {
        "and", "called", "function", "functions", "implement", "main",
        "named", "or", "print", "solution", "the",
    }
    for name in candidates:
        lower = name.lower()
        if name.startswith("__"):
            continue
        if lower in ignored:
            continue
        if name not in seen:
            seen.add(name)
            filtered.append(name)
    return filtered


def assignment_mentions_jupyter_notebook(assignment_description: str) -> bool:
    """Return True when the assignment explicitly calls for a Jupyter notebook."""
    if not assignment_description:
        return False

    text = assignment_description.lower()
    patterns = [
        r"jupyter\s+notebook",
        r"\.ipynb\b",
        r"(?:submission|submit|upload)[^\.\n]{0,80}\bnotebook\b",
        r"\bnotebook\b[^\.\n]{0,80}(?:submission|submit|upload)",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def infer_python_notebook_requirements(assignment_description: str) -> List[str]:
    """Infer extra Python requirements for notebook-based assignments."""
    if not assignment_description:
        return []

    text = assignment_description.lower()
    requirements: List[str] = []
    for rule in PYTHON_NOTEBOOK_LIBRARY_RULES:
        if any(re.search(pattern, text) for pattern in rule["patterns"]):
            requirement = rule["requirement"]
            if requirement not in requirements:
                requirements.append(requirement)
    return requirements


def infer_python_notebook_imports(assignment_description: str) -> List[str]:
    """Infer helpful Python notebook imports from assignment content."""
    if not assignment_description:
        return []

    text = assignment_description.lower()
    imports: List[str] = []
    for rule in PYTHON_NOTEBOOK_LIBRARY_RULES:
        if any(re.search(pattern, text) for pattern in rule["patterns"]):
            for import_line in rule["imports"]:
                if import_line not in imports:
                    imports.append(import_line)
    return imports


def infer_python_assignment_requirements(assignment_description: str) -> List[str]:
    """Infer Python package requirements from assignment text."""
    if not assignment_description:
        return []

    text = assignment_description.lower()
    requirements: List[str] = []
    for rule in PYTHON_LIBRARY_RULES + PYTHON_NOTEBOOK_LIBRARY_RULES:
        if any(re.search(pattern, text) for pattern in rule["patterns"]):
            requirement = rule["requirement"]
            if requirement not in requirements:
                requirements.append(requirement)
    return requirements


def infer_python_assignment_imports(assignment_description: str) -> List[str]:
    """Infer Python import lines from assignment text."""
    if not assignment_description:
        return []

    imports: List[str] = []
    seen = set()

    for import_line in re.findall(
        r"(?m)^\s*((?:from\s+[A-Za-z_][A-Za-z0-9_\.]*\s+import\s+[A-Za-z_*][A-Za-z0-9_,\s*]*)|(?:import\s+[A-Za-z_][A-Za-z0-9_\.]*\s*(?:as\s+[A-Za-z_][A-Za-z0-9_]*)?))\s*$",
        assignment_description,
    ):
        cleaned = re.sub(r"\s+", " ", import_line.strip())
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            imports.append(cleaned)

    text = assignment_description.lower()
    for rule in PYTHON_LIBRARY_RULES + PYTHON_NOTEBOOK_LIBRARY_RULES:
        if any(re.search(pattern, text) for pattern in rule["patterns"]):
            for import_line in rule["imports"]:
                if import_line not in seen:
                    seen.add(import_line)
                    imports.append(import_line)
    return imports


def _inject_python_imports(source: str, import_lines: List[str]) -> str:
    """Insert import lines after a module docstring, preserving existing content."""
    if not import_lines:
        return source

    normalized_imports: List[str] = []
    for import_line in import_lines:
        cleaned = import_line.strip()
        if cleaned and cleaned not in normalized_imports:
            normalized_imports.append(cleaned)

    if not normalized_imports:
        return source

    stripped = source.lstrip()
    leading = source[: len(source) - len(stripped)]
    docstring_match = re.match(r'(["\']{3}[\s\S]*?["\']{3}\n+)', stripped)
    import_block = "\n".join(normalized_imports) + "\n\n"

    if docstring_match:
        docstring = docstring_match.group(1)
        remainder = stripped[docstring_match.end():].lstrip("\n")
        return f"{leading}{docstring}\n{import_block}{remainder}"

    return f"{leading}{import_block}{stripped}"


def _build_python_stub_file(
    assignment_name: str,
    assignment_summary: str,
    function_names: List[str],
    import_lines: List[str],
    include_main: bool,
) -> str:
    blocks = [
        f'"""{assignment_name}\n\n{assignment_summary}\n"""',
        "",
    ]

    if import_lines:
        blocks.extend(import_lines)
        blocks.append("")

    for function_name in function_names:
        blocks.append(
            f"def {function_name}():\n"
            f"    \"\"\"TODO: implement {function_name}.\"\"\"\n"
            "    raise NotImplementedError\n"
        )

    if include_main:
        blocks.append(
            "def main():\n"
            "    \"\"\"Main function - implement your solution here.\"\"\"\n"
            "    pass\n"
        )
        blocks.append(
            'if __name__ == "__main__":\n'
            "    main()\n"
        )

    return "\n".join(blocks).strip() + "\n"


def _build_r_stub_file(
    assignment_name: str,
    assignment_summary: str,
    function_names: List[str],
    include_main: bool,
) -> str:
    blocks = [
        f"# {assignment_name}",
        "#",
        f"# {assignment_summary}",
        "",
    ]

    for function_name in function_names:
        blocks.append(
            f"{function_name} <- function() {{\n"
            f"  stop(\"TODO: implement {function_name}\")\n"
            "}\n"
        )

    if include_main:
        blocks.append(
            "main <- function() {\n"
            "  invisible(NULL)\n"
            "}\n"
        )
        blocks.append(
            "if (sys.nframe() == 0) {\n"
            "  main()\n"
            "}\n"
        )

    return "\n".join(blocks).strip() + "\n"


def _build_function_stub_file(
    assignment_name: str,
    assignment_summary: str,
    function_names: List[str],
    language: str,
    import_lines: List[str],
    include_main: bool,
) -> str:
    if language in {"python", "py"}:
        return _build_python_stub_file(
            assignment_name,
            assignment_summary,
            function_names,
            import_lines,
            include_main,
        )
    return _build_r_stub_file(assignment_name, assignment_summary, function_names, include_main)


def _build_python_notebook_file(
    assignment_name: str,
    assignment_summary: str,
    function_names: List[str],
    import_lines: List[str],
) -> str:
    code_lines = [
        f'"""{assignment_name}"""',
        "",
    ]

    for function_name in function_names:
        code_lines.extend([
            f"def {function_name}():",
            f'    """TODO: implement {function_name}."""',
            "    raise NotImplementedError",
            "",
        ])

    code_lines.extend([
        "def main():",
        '    """Main function - implement your solution here."""',
        "    pass",
        "",
        'if __name__ == "__main__":',
        "    main()",
    ])

    cells = [
        {
            "cell_type": "markdown",
            "metadata": {"language": "markdown"},
            "source": [
                f"# {assignment_name}\n",
                "\n",
                f"{assignment_summary}\n",
            ],
        },
    ]

    if import_lines:
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {"language": "python"},
                "outputs": [],
                "source": [f"{line}\n" for line in import_lines],
            }
        )

    notebook = {
        "cells": cells + [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {"language": "python"},
                "outputs": [],
                "source": [f"{line}\n" for line in code_lines],
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return json.dumps(notebook, indent=2) + "\n"


def _select_function_stub_target(language: str, requested_files: List[str]) -> str:
    default_target = SOURCE_FILE_BY_LANGUAGE.get(language, "main.py")
    source_extensions = {"python": ".py", "py": ".py", "r": ".R", "rscript": ".R"}
    source_extension = source_extensions.get(language, ".py")

    source_files = [
        path for path in requested_files
        if path.endswith(source_extension) and not path.lower().startswith("tests/")
    ]
    if len(source_files) == 1:
        return source_files[0]
    return default_target


def _select_notebook_target(requested_files: List[str]) -> str:
    notebook_files = [path for path in requested_files if path.lower().endswith(".ipynb")]
    if len(notebook_files) == 1:
        return notebook_files[0]
    return "main.ipynb"


def _extend_python_requirements(existing_requirements: str, extra_requirements: List[str]) -> str:
    if not extra_requirements:
        return existing_requirements

    lines = [line for line in existing_requirements.splitlines() if line.strip()]
    for requirement in extra_requirements:
        if requirement not in lines:
            lines.append(requirement)
    return "\n".join(lines) + "\n"


def _is_python_ml_project_assignment(requested_files: List[str], assignment_description: str) -> bool:
    requested_lower = {path.lower() for path in requested_files}
    description_lower = assignment_description.lower()
    ml_signals = [
        "machine learning",
        "ml project",
        "group project",
        "dataset",
        "eda",
        "exploratory data analysis",
        "model development",
        "predictive",
        "prescriptive",
        "classification",
        "malware",
        "intrusion",
        "nsl-kdd",
        "kagglehub",
    ]
    return (
        any(signal in description_lower for signal in ml_signals)
        or "presentation.md" in requested_lower
        or "slides.md" in requested_lower
    )


def _is_nsl_kdd_assignment(assignment_description: str) -> bool:
    description_lower = assignment_description.lower()
    return any(
        phrase in description_lower
        for phrase in [
            "nsl-kdd",
            "nsl kdd",
            "network intrusion detection",
            "malware and network intrusion detection",
        ]
    )


def _build_generic_report_template(assignment_name: str) -> str:
    return (
        f"# {assignment_name} Report\n\n"
        "## Executive Summary\n\n"
        "Summarize the purpose of the work, the approach you followed, and the most important findings.\n\n"
        "## Problem Statement\n\n"
        "Explain the problem being addressed and why it matters.\n\n"
        "## Methods\n\n"
        "Document the workflow, tools, and analysis steps used to complete the assignment.\n\n"
        "## Findings\n\n"
        "Summarize the main results, tables, graphs, or outputs that support your conclusions.\n\n"
        "## Recommendations\n\n"
        "Describe the actions or follow-up steps suggested by the results.\n\n"
        "## Appendix\n\n"
        "Include referenced code snippets, tables, figures, or supporting material.\n"
    )


def _build_ml_project_report_template(assignment_name: str, dataset_name: str) -> str:
    return (
        f"# {assignment_name} Report\n\n"
        "## Real-World Problem\n\n"
        "Explain the cybersecurity or business problem your team is solving and why big-data ML techniques are appropriate.\n\n"
        f"## Dataset Selection: {dataset_name}\n\n"
        "Explain why this dataset was selected, what it contains, and how it supports the project objectives.\n\n"
        "## EDA Workflow\n\n"
        "Describe the exploratory data analysis process, dataset size, feature types, missingness, duplicates, outliers, and the most important patterns discovered.\n\n"
        "## Data Preparation\n\n"
        "Summarize the preprocessing, feature engineering, encoding, scaling, and dataset split decisions used before model training.\n\n"
        "## ML Methodology and Algorithms\n\n"
        "Explain which ML algorithms were used, why they were selected, and how the code transforms the data step by step.\n\n"
        "## Results and Metrics\n\n"
        "Compare model performance using the selected metrics and visualizations. Include insights from the EDA and advanced analytics.\n\n"
        "## Interpretation and Recommendations\n\n"
        "Interpret what the results mean for stakeholders, identify the important variables, and recommend next actions.\n\n"
        "## Weekly Code Walkthrough Notes\n\n"
        "Capture concise talking points for the weekly in-class walkthroughs and note which code snippets to demonstrate.\n\n"
        "## Appendix\n\n"
        "Include referenced code snippets, tables, plots, and any generated model artifact summaries.\n"
    )


def _build_ml_project_runner_file(dataset_name: str) -> str:
    return (
        f'"""Pipeline entrypoint for the {dataset_name} ML project scaffold."""\n\n'
        "from pathlib import Path\n\n"
        "from src.data_loader import load_nsl_kdd_frames\n"
        "from src.eda import build_eda_summary, render_eda_artifacts\n"
        "from src.train_models import train_and_evaluate_models, write_model_artifacts\n\n"
        "def main() -> None:\n"
        '    """Download data, run EDA, train baseline models, and persist artifacts."""\n'
        "    output_dir = Path('outputs')\n"
        "    output_dir.mkdir(exist_ok=True)\n"
        "    train_df, test_df, metadata = load_nsl_kdd_frames()\n"
        "    eda_summary = build_eda_summary(train_df, test_df, metadata)\n"
        "    render_eda_artifacts(train_df, eda_summary, output_dir=output_dir)\n"
        "    model_results = train_and_evaluate_models(train_df, test_df)\n"
        "    write_model_artifacts(model_results, output_dir=output_dir)\n"
        "    print('EDA and model artifacts written to outputs/.')\n\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def _build_nsl_kdd_data_loader_file() -> str:
    return '''"""Dataset-loading utilities for the NSL-KDD ML project scaffold."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

import kagglehub
import pandas as pd

DEFAULT_DATASET_HANDLE = os.getenv(
    "KAGGLEHUB_DATASET",
    "<set-your-nsl-kdd-kagglehub-handle>",
)

NSL_KDD_COLUMNS = [
    "duration",
    "protocol_type",
    "service",
    "flag",
    "src_bytes",
    "dst_bytes",
    "land",
    "wrong_fragment",
    "urgent",
    "hot",
    "num_failed_logins",
    "logged_in",
    "num_compromised",
    "root_shell",
    "su_attempted",
    "num_root",
    "num_file_creations",
    "num_shells",
    "num_access_files",
    "num_outbound_cmds",
    "is_host_login",
    "is_guest_login",
    "count",
    "srv_count",
    "serror_rate",
    "srv_serror_rate",
    "rerror_rate",
    "srv_rerror_rate",
    "same_srv_rate",
    "diff_srv_rate",
    "srv_diff_host_rate",
    "dst_host_count",
    "dst_host_srv_count",
    "dst_host_same_srv_rate",
    "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate",
    "dst_host_srv_diff_host_rate",
    "dst_host_serror_rate",
    "dst_host_srv_serror_rate",
    "dst_host_rerror_rate",
    "dst_host_srv_rerror_rate",
    "label",
    "difficulty",
]


def _find_matching_file(root: Path, candidates: Sequence[str]) -> Path:
    lowered = {candidate.lower() for candidate in candidates}
    for path in root.rglob("*"):
        if path.is_file() and path.name.lower() in lowered:
            return path
    raise FileNotFoundError(f"Could not find any of {sorted(lowered)} under {root}")


def download_dataset(dataset_handle: str | None = None) -> Path:
    handle = (dataset_handle or DEFAULT_DATASET_HANDLE).strip()
    if not handle or handle.startswith("<"):
        raise ValueError(
            "Set KAGGLEHUB_DATASET to the KaggleHub handle for your NSL-KDD dataset before running this scaffold."
        )
    return Path(kagglehub.dataset_download(handle))


def load_nsl_kdd_frames(dataset_handle: str | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    dataset_root = download_dataset(dataset_handle)
    train_path = _find_matching_file(dataset_root, ["KDDTrain+.txt", "KDDTrain+.csv"])
    test_path = _find_matching_file(dataset_root, ["KDDTest+.txt", "KDDTest+.csv"])

    train_df = pd.read_csv(train_path, names=NSL_KDD_COLUMNS)
    test_df = pd.read_csv(test_path, names=NSL_KDD_COLUMNS)
    metadata = {
        "dataset_root": str(dataset_root),
        "train_path": str(train_path),
        "test_path": str(test_path),
    }
    return train_df, test_df, metadata
'''


def _build_ml_eda_file(dataset_name: str) -> str:
    return f'''"""EDA helpers for the {dataset_name} ML project scaffold."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def build_eda_summary(train_df: pd.DataFrame, test_df: pd.DataFrame, metadata: dict[str, str]) -> dict:
    combined_df = pd.concat([train_df.assign(split="train"), test_df.assign(split="test")], ignore_index=True)
    numeric_columns = combined_df.select_dtypes(include=["number"]).columns.tolist()
    return {{
        "dataset_root": metadata.get("dataset_root", ""),
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "combined_rows": int(len(combined_df)),
        "feature_count": int(combined_df.shape[1] - 2),
        "missing_values": int(combined_df.isna().sum().sum()),
        "duplicate_rows": int(combined_df.duplicated().sum()),
        "label_distribution": combined_df["label"].value_counts().to_dict(),
        "numeric_columns": numeric_columns,
    }}


def render_eda_artifacts(train_df: pd.DataFrame, summary: dict, output_dir: str | Path = "outputs") -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    (output_path / "eda_summary.json").write_text(json.dumps(summary, indent=2) + "\\n", encoding="utf-8")

    plt.figure(figsize=(10, 5))
    train_df["label"].value_counts().head(10).plot(kind="bar")
    plt.title("Top NSL-KDD Class Labels")
    plt.tight_layout()
    plt.savefig(output_path / "label_distribution.png")
    plt.close()

    numeric_columns = train_df.select_dtypes(include=["number"]).columns.tolist()[:6]
    if numeric_columns:
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=train_df[numeric_columns])
        plt.xticks(rotation=30, ha="right")
        plt.title("Sample Numeric Feature Distribution")
        plt.tight_layout()
        plt.savefig(output_path / "numeric_feature_boxplot.png")
        plt.close()
'''


def _build_ml_training_file() -> str:
    return '''"""Baseline model-training helpers for the NSL-KDD ML project scaffold."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGET_COLUMN = "label"
CATEGORICAL_COLUMNS = ["protocol_type", "service", "flag"]


def _binary_target(series: pd.Series) -> pd.Series:
    return (series.astype(str).str.lower() != "normal").astype(int)


def _split_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    features = frame.drop(columns=[TARGET_COLUMN, "difficulty"], errors="ignore")
    target = _binary_target(frame[TARGET_COLUMN])
    return features, target


def build_preprocessor(features: pd.DataFrame) -> ColumnTransformer:
    categorical_columns = [column for column in CATEGORICAL_COLUMNS if column in features.columns]
    numeric_columns = [column for column in features.columns if column not in categorical_columns]

    return ColumnTransformer(
        transformers=[
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_columns,
            ),
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric_columns,
            ),
        ],
        remainder="drop",
    )


def build_models(preprocessor: ColumnTransformer) -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("model", LogisticRegression(max_iter=1000)),
            ]
        ),
        "random_forest": Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("model", RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)),
            ]
        ),
    }


def _evaluate_model(name: str, model: Pipeline, x_train: pd.DataFrame, y_train: pd.Series, x_test: pd.DataFrame, y_test: pd.Series) -> dict:
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, predictions, average="binary", zero_division=0)
    return {
        "model": name,
        "accuracy": round(float(accuracy_score(y_test, predictions)), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
    }


def train_and_evaluate_models(train_df: pd.DataFrame, test_df: pd.DataFrame) -> list[dict]:
    x_train, y_train = _split_features(train_df)
    x_test, y_test = _split_features(test_df)
    preprocessor = build_preprocessor(x_train)
    models = build_models(preprocessor)
    return [
        _evaluate_model(name, model, x_train, y_train, x_test, y_test)
        for name, model in models.items()
    ]


def write_model_artifacts(results: list[dict], output_dir: str | Path = "outputs") -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    (output_path / "model_metrics.json").write_text(json.dumps(results, indent=2) + "\\n", encoding="utf-8")

    lines = [
        "# Model Metrics",
        "",
        "| Model | Accuracy | Precision | Recall | F1 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            f"| {result['model']} | {result['accuracy']:.4f} | {result['precision']:.4f} | {result['recall']:.4f} | {result['f1']:.4f} |"
        )

    (output_path / "MODEL_METRICS.md").write_text("\\n".join(lines) + "\\n", encoding="utf-8")
'''


def _build_ml_project_tests_file() -> str:
    return '''import pandas as pd

from src.train_models import _binary_target, build_preprocessor


def test_binary_target_marks_attacks_as_one():
    result = _binary_target(pd.Series(["normal", "neptune", "smurf"]))
    assert result.tolist() == [0, 1, 1]


def test_build_preprocessor_handles_known_nsl_kdd_columns():
    frame = pd.DataFrame(
        {
            "protocol_type": ["tcp", "udp"],
            "service": ["http", "domain_u"],
            "flag": ["SF", "S0"],
            "src_bytes": [181, 239],
            "dst_bytes": [5450, 486],
        }
    )
    preprocessor = build_preprocessor(frame)
    assert preprocessor is not None
'''


def _build_ml_presentation_outline(assignment_name: str, dataset_name: str) -> str:
    return (
        f"# {assignment_name} Presentation Outline\n\n"
        "## Slide 1: Business Problem\n"
        "- Explain the malware or intrusion-detection problem and why it matters.\n\n"
        f"## Slide 2: Dataset Selection ({dataset_name})\n"
        "- Describe the dataset, why it was chosen, and any limitations.\n\n"
        "## Slide 3: EDA Highlights\n"
        "- Show dataset size, data quality findings, and the most important graphs.\n\n"
        "## Slide 4: Feature Engineering and Preprocessing\n"
        "- Explain categorical encoding, scaling, and target construction.\n\n"
        "## Slide 5: Models and Metrics\n"
        "- Compare the baseline models and justify the evaluation metrics.\n\n"
        "## Slide 6: Results and Recommendations\n"
        "- Interpret the results and recommend next steps for the stakeholder.\n\n"
        "## Slide 7: Weekly Code Walkthrough Snippets\n"
        "- List the code snippets each group member should be ready to explain in class.\n"
    )


def _append_ml_readme_notes(existing_readme: str, dataset_name: str) -> str:
    return existing_readme.rstrip() + (
        "\n\n## ML Project Scaffold\n"
        f"- This scaffold is tailored for the {dataset_name} workflow with EDA, baseline model training, report writing, and presentation prep.\n"
        "- Set `KAGGLEHUB_DATASET` to the KaggleHub handle for your approved dataset before running the project.\n"
        "- Run `python main.py` to execute the end-to-end starter workflow and populate `outputs/`.\n"
        "- Review `PRESENTATION.md` for the slide-deck outline and `Report.md` for the written summary structure.\n"
        "- Use `pytest tests/test_ml_project.py` to validate the generated ML helper modules.\n"
    )


def _is_python_maze_assignment(requested_files: List[str], assignment_description: str) -> bool:
    requested_lower = {path.lower() for path in requested_files}
    description_lower = assignment_description.lower()
    return (
        "maze_solvers.py" in requested_lower
        or (
            "maze" in description_lower
            and "solver" in description_lower
            and "python" in description_lower
        )
    )


def _build_maze_solver_file(assignment_name: str, function_names: List[str]) -> str:
    solver_names = list(function_names[:3])
    defaults = ["maze_solver_one", "maze_solver_two", "maze_solver_three"]
    for default_name in defaults:
        if len(solver_names) >= 3:
            break
        if default_name not in solver_names:
            solver_names.append(default_name)

    body = '''from __future__ import annotations

from collections import deque
from heapq import heappop, heappush
from pathlib import Path
from typing import Iterable, Sequence

Point = tuple[int, int]
Grid = list[list[str]]


def _load_maze_lines(maze: str | Sequence[str]) -> list[str]:
    if isinstance(maze, (list, tuple)):
        lines = [str(line).rstrip("\\n") for line in maze]
    elif isinstance(maze, str):
        candidate_path = Path(maze)
        if "\\n" not in maze and candidate_path.exists():
            lines = candidate_path.read_text(encoding="utf-8").splitlines()
        else:
            lines = maze.splitlines()
    else:
        raise TypeError("maze must be a path, maze text, or a sequence of lines")

    lines = [line.rstrip("\\n") for line in lines if line is not None]
    if not lines:
        raise ValueError("maze input is empty")
    return lines


def _parse_maze(maze: str | Sequence[str]) -> tuple[int, int, Grid, Point, Point]:
    lines = _load_maze_lines(maze)
    try:
        width_text, height_text = lines[0].split()
        width = int(width_text)
        height = int(height_text)
    except ValueError as error:
        raise ValueError("first maze line must contain width and height") from error

    grid_lines = lines[1:]
    if len(grid_lines) != height:
        raise ValueError(f"maze height mismatch: expected {height}, found {len(grid_lines)}")

    grid = [list(row) for row in grid_lines]
    for row in grid:
        if len(row) != width:
            raise ValueError(f"maze width mismatch: expected {width}, found {len(row)}")

    start = _find_symbol(grid, "S")
    goal = _find_symbol(grid, "E")
    return width, height, grid, start, goal


def _find_symbol(grid: Grid, symbol: str) -> Point:
    for row_index, row in enumerate(grid):
        for col_index, value in enumerate(row):
            if value == symbol:
                return row_index, col_index
    raise ValueError(f"maze must contain exactly one {symbol}")


def _neighbors(grid: Grid, point: Point) -> Iterable[Point]:
    row, col = point
    candidates = [
        (row - 1, col),
        (row, col + 1),
        (row + 1, col),
        (row, col - 1),
    ]
    height = len(grid)
    width = len(grid[0]) if grid else 0
    for next_row, next_col in candidates:
        if 0 <= next_row < height and 0 <= next_col < width and grid[next_row][next_col] != "X":
            yield next_row, next_col


def _reconstruct_path(parents: dict[Point, Point | None], goal: Point) -> list[Point]:
    path: list[Point] = []
    current: Point | None = goal
    while current is not None:
        path.append(current)
        current = parents[current]
    path.reverse()
    return path


def _render_solution(width: int, height: int, grid: Grid, path: list[Point]) -> str:
    solved = [row[:] for row in grid]
    for row, col in path[1:-1]:
        if solved[row][col] == " ":
            solved[row][col] = "*"
    body = ["".join(row) for row in solved]
    return "\\n".join([f"{width} {height}", *body])


def _heuristic(point: Point, goal: Point) -> int:
    return abs(point[0] - goal[0]) + abs(point[1] - goal[1])


def _solve_bfs(maze: str | Sequence[str]) -> str:
    width, height, grid, start, goal = _parse_maze(maze)
    frontier: deque[Point] = deque([start])
    parents: dict[Point, Point | None] = {start: None}

    while frontier:
        current = frontier.popleft()
        if current == goal:
            return _render_solution(width, height, grid, _reconstruct_path(parents, goal))

        for neighbor in _neighbors(grid, current):
            if neighbor in parents:
                continue
            parents[neighbor] = current
            frontier.append(neighbor)

    raise ValueError("maze has no solution")


def _solve_dfs(maze: str | Sequence[str]) -> str:
    width, height, grid, start, goal = _parse_maze(maze)
    frontier: list[Point] = [start]
    parents: dict[Point, Point | None] = {start: None}

    while frontier:
        current = frontier.pop()
        if current == goal:
            return _render_solution(width, height, grid, _reconstruct_path(parents, goal))

        neighbors = list(_neighbors(grid, current))
        for neighbor in reversed(neighbors):
            if neighbor in parents:
                continue
            parents[neighbor] = current
            frontier.append(neighbor)

    raise ValueError("maze has no solution")


def _solve_astar(maze: str | Sequence[str]) -> str:
    width, height, grid, start, goal = _parse_maze(maze)
    frontier: list[tuple[int, int, Point]] = [(0, 0, start)]
    parents: dict[Point, Point | None] = {start: None}
    cost_so_far: dict[Point, int] = {start: 0}
    tie_breaker = 1

    while frontier:
        _, _, current = heappop(frontier)
        if current == goal:
            return _render_solution(width, height, grid, _reconstruct_path(parents, goal))

        for neighbor in _neighbors(grid, current):
            tentative_cost = cost_so_far[current] + 1
            if tentative_cost >= cost_so_far.get(neighbor, tentative_cost + 1):
                continue

            cost_so_far[neighbor] = tentative_cost
            parents[neighbor] = current
            priority = tentative_cost + _heuristic(neighbor, goal)
            heappush(frontier, (priority, tie_breaker, neighbor))
            tie_breaker += 1

    raise ValueError("maze has no solution")


'''

    algorithm_defs = [
        (solver_names[0], "breadth-first search", "_solve_bfs"),
        (solver_names[1], "depth-first search", "_solve_dfs"),
        (solver_names[2], "A* search with the Manhattan-distance heuristic", "_solve_astar"),
    ]

    function_blocks = []
    for function_name, description, implementation_name in algorithm_defs:
        function_blocks.append(
            f"def {function_name}(maze: str | Sequence[str]) -> str:\n"
            f'    """Solve the maze with {description} and return the solved maze text."""\n'
            f"    return {implementation_name}(maze)\n"
        )

    return f'"""{assignment_name} maze solver interface."""\n\n' + body + "\n\n".join(function_blocks) + "\n"


def _build_maze_runner_file(function_names: List[str]) -> str:
    solver_names = list(function_names[:3])
    defaults = ["maze_solver_one", "maze_solver_two", "maze_solver_three"]
    for default_name in defaults:
        if len(solver_names) >= 3:
            break
        if default_name not in solver_names:
            solver_names.append(default_name)

    return (
        '"""Command-line runner for the generated maze solvers."""\n\n'
        f"from maze_solvers import {solver_names[0]}, {solver_names[1]}, {solver_names[2]}\n\n"
        "\n"
        "def main() -> None:\n"
        '    """Load maze.txt and print each solver output."""\n'
        '    maze_path = "maze.txt"\n'
        f"    solvers = [(\"{solver_names[0]}\", {solver_names[0]}), (\"{solver_names[1]}\", {solver_names[1]}), (\"{solver_names[2]}\", {solver_names[2]})]\n"
        "    for name, solver in solvers:\n"
        "        print(f\"=== {name} ===\")\n"
        "        print(solver(maze_path))\n"
        "        print()\n\n"
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def _build_maze_solver_tests(function_names: List[str]) -> str:
    solver_names = list(function_names[:3])
    defaults = ["maze_solver_one", "maze_solver_two", "maze_solver_three"]
    for default_name in defaults:
        if len(solver_names) >= 3:
            break
        if default_name not in solver_names:
            solver_names.append(default_name)

    return (
        f"from maze_solvers import {solver_names[0]}, {solver_names[1]}, {solver_names[2]}\n\n"
        'SAMPLE_MAZE = """5 5\nS   X\nXX XX\nX   X\nX XXX\nX   E\n"""\n\n'
        "\n"
        "def _assert_valid_solution(result: str) -> int:\n"
        '    lines = result.splitlines()\n'
        '    assert lines[0] == "5 5"\n'
        '    body = "\\n".join(lines[1:])\n'
        '    assert "S" in body\n'
        '    assert "E" in body\n'
        '    assert "*" in body\n'
        '    return body.count("*")\n\n'
        f"def test_{solver_names[0]}_returns_solved_maze():\n"
        f"    steps = _assert_valid_solution({solver_names[0]}(SAMPLE_MAZE))\n"
        "    assert steps > 0\n\n"
        f"def test_{solver_names[1]}_returns_solved_maze():\n"
        f"    steps = _assert_valid_solution({solver_names[1]}(SAMPLE_MAZE))\n"
        "    assert steps > 0\n\n"
        f"def test_{solver_names[2]}_matches_bfs_path_length():\n"
        f"    bfs_steps = _assert_valid_solution({solver_names[0]}(SAMPLE_MAZE))\n"
        f"    astar_steps = _assert_valid_solution({solver_names[2]}(SAMPLE_MAZE))\n"
        "    assert astar_steps == bfs_steps\n"
    )


def _build_maze_report_template(assignment_name: str) -> str:
    return (
        f"# {assignment_name} Report\n\n"
        "## Introduction to Search Algorithms\n\n"
        "Summarize uninformed versus informed search and explain why maze solving is a useful benchmark problem.\n\n"
        "## Selected Algorithms\n\n"
        "- Breadth-first search (blind search)\n"
        "- Depth-first search (blind search)\n"
        "- A* search (heuristic search)\n\n"
        "## Heuristics Used\n\n"
        "Document the Manhattan-distance heuristic used by A* and explain why it is admissible for a 4-direction grid maze.\n\n"
        "## Performance Comparison\n\n"
        "Record the path length, nodes expanded, and runtime for each solver on the assigned report maze.\n\n"
        "## Optimality, Time, and Space Analysis\n\n"
        "Compare the optimality of the returned paths, the time taken, and the memory required by each approach.\n\n"
        "## Maze Variations and Performance Impact\n\n"
        "Describe how added walls, wider corridors, or misleading dead ends would change the performance of each algorithm.\n\n"
        "## Real-life Application\n\n"
        "Describe a real-world situation where one of these search algorithms would be useful.\n"
    )


def _append_maze_readme_notes(existing_readme: str) -> str:
    return existing_readme.rstrip() + (
        "\n\n## Maze Solver Interface\n"
        "- `maze_solvers.py` contains working implementations of breadth-first search, depth-first search, and A* search.\n"
        "- Each solver accepts either a maze file path, raw maze text, or a sequence of maze lines.\n"
        "- `main.py` runs all three solvers against `maze.txt` for quick smoke testing.\n"
        "- Run `pytest tests/test_maze_solvers.py` to validate the generated maze solver interface.\n"
    )


def _build_maze_benchmark_file(function_names: List[str], artifact_paths: List[str]) -> str:
    solver_names = list(function_names[:3])
    defaults = ["maze_solver_one", "maze_solver_two", "maze_solver_three"]
    for default_name in defaults:
        if len(solver_names) >= 3:
            break
        if default_name not in solver_names:
            solver_names.append(default_name)

    default_candidates = [*artifact_paths, "maze.txt"]
    candidate_lines = "\n".join(f'    "{path}",' for path in default_candidates)

    return (
        '"""Benchmark helper for generated maze assignments."""\n\n'
        "from __future__ import annotations\n\n"
        "import json\n"
        "import sys\n"
        "import tracemalloc\n"
        "from pathlib import Path\n"
        "from time import perf_counter\n\n"
        f"from maze_solvers import {solver_names[0]}, {solver_names[1]}, {solver_names[2]}\n\n"
        "DEFAULT_MAZE_CANDIDATES = [\n"
        f"{candidate_lines}\n"
        "]\n\n"
        "def _pick_maze_path(explicit_path: str | None = None) -> str:\n"
        "    if explicit_path:\n"
        "        return explicit_path\n"
        "    for candidate in DEFAULT_MAZE_CANDIDATES:\n"
        "        if Path(candidate).exists():\n"
        "            return candidate\n"
        '    return "maze.txt"\n\n'
        "def _path_cell_count(solved_maze: str) -> int:\n"
        '    body = "\\n".join(solved_maze.splitlines()[1:])\n'
        '    return body.count("*") + 2\n\n'
        "def _run_single(name: str, solver, maze_path: str) -> dict:\n"
        "    tracemalloc.start()\n"
        "    started_at = perf_counter()\n"
        "    solved_maze = solver(maze_path)\n"
        "    runtime_seconds = perf_counter() - started_at\n"
        "    _, peak_bytes = tracemalloc.get_traced_memory()\n"
        "    tracemalloc.stop()\n"
        "    return {\n"
        '        "algorithm": name,\n'
        '        "runtime_seconds": round(runtime_seconds, 6),\n'
        '        "peak_memory_bytes": peak_bytes,\n'
        '        "path_cell_count": _path_cell_count(solved_maze),\n'
        '        "solved_maze": solved_maze,\n'
        "    }\n\n"
        "def benchmark_solvers(maze_path: str | None = None) -> dict:\n"
        "    selected_maze = _pick_maze_path(maze_path)\n"
        "    results = [\n"
        f'        _run_single("{solver_names[0]}", {solver_names[0]}, selected_maze),\n'
        f'        _run_single("{solver_names[1]}", {solver_names[1]}, selected_maze),\n'
        f'        _run_single("{solver_names[2]}", {solver_names[2]}, selected_maze),\n'
        "    ]\n"
        "    return {\n"
        '        "maze_path": selected_maze,\n'
        '        "results": results,\n'
        "    }\n\n"
        "def _build_markdown_report(payload: dict) -> str:\n"
        "    lines = [\n"
        '        "# Maze Benchmark Results",\n'
        '        "",\n'
        '        f"- Maze: {payload[\"maze_path\"]}",\n'
        '        "",\n'
        '        "| Algorithm | Runtime (s) | Peak Memory (bytes) | Path Cells |",\n'
        '        "| --- | ---: | ---: | ---: |",\n'
        "    ]\n"
        "    for result in payload[\"results\"]:\n"
        "        lines.append(\n"
        '            f"| {result[\"algorithm\"]} | {result[\"runtime_seconds\"]:.6f} | {result[\"peak_memory_bytes\"]} | {result[\"path_cell_count\"]} |"\n'
        "        )\n"
        '    return "\\n".join(lines) + "\\n"\n\n'
        "def main() -> None:\n"
        "    maze_path = sys.argv[1] if len(sys.argv) > 1 else None\n"
        "    payload = benchmark_solvers(maze_path)\n"
        '    Path("benchmark_results.json").write_text(json.dumps(payload, indent=2) + "\\n", encoding="utf-8")\n'
        '    Path("BENCHMARK_RESULTS.md").write_text(_build_markdown_report(payload), encoding="utf-8")\n'
        '    print(json.dumps(payload, indent=2))\n\n'
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def _build_artifact_readme(assignment_artifacts: List[Dict[str, Any]]) -> str:
    lines = [
        "# Assignment Artifacts",
        "",
        "Downloaded maze files from assignment links are stored here.",
        "",
    ]
    for artifact in assignment_artifacts:
        lines.append(
            f"- {artifact.get('path', '').split('/')[-1]}: {artifact.get('source_url', 'unknown source')}"
        )
    return "\n".join(lines).rstrip() + "\n"


def _append_maze_benchmark_notes(existing_readme: str, artifact_paths: List[str]) -> str:
    lines = [
        "",
        "## Maze Benchmarking",
        "- Run `python benchmark_maze.py` to benchmark the generated BFS, DFS, and A* solvers.",
        "- The script writes machine-readable results to `benchmark_results.json` and a report-ready table to `BENCHMARK_RESULTS.md`.",
    ]
    if artifact_paths:
        lines.append(f"- Benchmarking will prefer the downloaded maze artifact files: {', '.join(artifact_paths)}.")
    else:
        lines.append("- If no linked maze artifacts are available, benchmarking falls back to `maze.txt`.")
    return existing_readme.rstrip() + "\n" + "\n".join(lines) + "\n"


def _append_maze_report_notes(existing_report: str) -> str:
    return existing_report.rstrip() + (
        "\n\n## Generated Benchmark Workflow\n\n"
        "Run `python benchmark_maze.py [optional-maze-path]` after you add the official report maze. "
        "Copy the metrics from `BENCHMARK_RESULTS.md` into the comparison sections above.\n"
    )


def build_assignment_specific_files(
    assignment_name: str,
    assignment_description: str,
    language: str,
    short_description: str = "",
) -> Dict[str, str]:
    """Generate files that are explicitly requested by assignment instructions."""
    language_lower = language.lower()
    if language_lower not in {"python", "py", "r", "rscript"}:
        return {}

    files: Dict[str, str] = {}
    requested_files = extract_required_filenames(assignment_description)
    requested_functions = extract_required_function_names(assignment_description)
    inferred_python_imports = infer_python_assignment_imports(assignment_description)
    assignment_summary = (short_description or assignment_description[:200]).strip()

    requested_lower = {path.lower() for path in requested_files}
    is_maze_assignment = language_lower in {"python", "py"} and _is_python_maze_assignment(
        requested_files,
        assignment_description,
    )
    is_ml_project_assignment = (
        language_lower in {"python", "py"}
        and not is_maze_assignment
        and _is_python_ml_project_assignment(requested_files, assignment_description)
    )
    dataset_name = "NSL-KDD" if _is_nsl_kdd_assignment(assignment_description) else "selected dataset"

    if is_maze_assignment:
        maze_functions = [
            name for name in requested_functions
            if name.startswith("maze_solver_") or name in {
                "maze_solver_one",
                "maze_solver_two",
                "maze_solver_three",
            }
        ]
        if not maze_functions:
            maze_functions = ["maze_solver_one", "maze_solver_two", "maze_solver_three"]

        files["maze_solvers.py"] = _build_maze_solver_file(assignment_name, maze_functions)
        files["main.py"] = _build_maze_runner_file(maze_functions)
        files["tests/test_maze_solvers.py"] = _build_maze_solver_tests(maze_functions)

    if is_maze_assignment or "maze.txt" in requested_lower or "maze" in assignment_description.lower():
        files["maze.txt"] = (
            "5 5\n"
            "S   X\n"
            "XX XX\n"
            "X   X\n"
            "X XXX\n"
            "X   E\n"
        )

    if is_maze_assignment:
        files["Report.md"] = _build_maze_report_template(assignment_name)
    elif is_ml_project_assignment:
        files["Report.md"] = _build_ml_project_report_template(assignment_name, dataset_name)
    elif "report.md" in requested_lower or "report" in assignment_description.lower():
        files["Report.md"] = _build_generic_report_template(assignment_name)

    if is_ml_project_assignment:
        files["main.py"] = _build_ml_project_runner_file(dataset_name)
        files["src/__init__.py"] = '"""Generated ML project helpers."""\n'
        files["src/data_loader.py"] = _build_nsl_kdd_data_loader_file()
        files["src/eda.py"] = _build_ml_eda_file(dataset_name)
        files["src/train_models.py"] = _build_ml_training_file()
        files["tests/test_ml_project.py"] = _build_ml_project_tests_file()
        files["PRESENTATION.md"] = _build_ml_presentation_outline(assignment_name, dataset_name)

    if language_lower in {"python", "py"} and assignment_mentions_jupyter_notebook(assignment_description):
        notebook_imports = inferred_python_imports
        notebook_target = _select_notebook_target(requested_files)
        files[notebook_target] = _build_python_notebook_file(
            assignment_name=assignment_name,
            assignment_summary=assignment_summary,
            function_names=requested_functions,
            import_lines=notebook_imports,
        )
        files["requirements.txt"] = _extend_python_requirements(
            files.get("requirements.txt", PYTHON_TEMPLATES["requirements.txt"]),
            infer_python_assignment_requirements(assignment_description),
        )

    if requested_functions:
        target_file = _select_function_stub_target(language_lower, requested_files)
        if target_file.lower() != "maze_solvers.py":
            include_main = target_file == SOURCE_FILE_BY_LANGUAGE.get(language_lower)
            files[target_file] = _build_function_stub_file(
                assignment_name=assignment_name,
                assignment_summary=assignment_summary,
                function_names=requested_functions,
                language=language_lower,
                import_lines=inferred_python_imports,
                include_main=include_main,
            )

    return files


def generate_starter_files(
    assignment_name: str,
    assignment_description: str,
    due_date: str,
    language: str = "python",
    short_description: str = "",
    course_context: Optional[List[Dict[str, Any]]] = None,
    assignment_artifacts: Optional[List[Dict[str, Any]]] = None,
) -> dict:
    """
    Generate starter files for an assignment.
    
    Args:
        assignment_name: Name of the assignment
        assignment_description: Full assignment description (Markdown) for README
        due_date: Due date string
        language: Programming language
        short_description: Brief plain-text description for code file comments
        
    Returns:
        Dictionary mapping file paths to their content
    """
    template = get_template_for_language(language)
    assignment_slug = normalize_slug(assignment_name)
    
    if not short_description:
        short_description = assignment_description[:200]
    
    files = {}
    for filepath, content_template in template.items():
        content = content_template.format(
            assignment_name=assignment_name,
            assignment_description=assignment_description if filepath == "README.md" else short_description,
            due_date=due_date,
            assignment_slug=assignment_slug
        )
        files[filepath] = content

    files["ASSIGNMENT.md"] = (
        f"# {assignment_name}\n\n"
        "## Full Assignment Brief\n"
        f"{assignment_description}\n\n"
        "## Due Date\n"
        f"{due_date}\n"
    )

    if course_context:
        files["COURSE_CONTEXT.md"] = build_course_context_markdown(course_context)
        files["README.md"] = files["README.md"].rstrip() + (
            "\n\n## Course Context\n"
            "See `COURSE_CONTEXT.md` for relevant excerpts retrieved from your course materials.\n"
        )
        files["ASSIGNMENT.md"] = files["ASSIGNMENT.md"].rstrip() + (
            "\n\n## Retrieved Course Context\n"
            "See `COURSE_CONTEXT.md` for supporting excerpts from course reference material.\n"
        )

    files.update(
        build_assignment_specific_files(
            assignment_name=assignment_name,
            assignment_description=assignment_description,
            language=language,
            short_description=short_description,
        )
    )

    maze_artifacts = list(assignment_artifacts or [])

    if language.lower() in {"python", "py"} and "maze_solvers.py" in files:
        maze_functions = [
            function_name
            for function_name in extract_required_function_names(assignment_description)
            if function_name.startswith("maze_solver_") or function_name in {
                "maze_solver_one",
                "maze_solver_two",
                "maze_solver_three",
            }
        ] or ["maze_solver_one", "maze_solver_two", "maze_solver_three"]
        artifact_paths = [artifact.get("path") for artifact in maze_artifacts if artifact.get("path")]
        files["benchmark_maze.py"] = _build_maze_benchmark_file(maze_functions, artifact_paths)
        files["README.md"] = _append_maze_readme_notes(files["README.md"])
        files["README.md"] = _append_maze_benchmark_notes(files["README.md"], artifact_paths)
        files["Report.md"] = _append_maze_report_notes(files["Report.md"])

        for artifact in maze_artifacts:
            artifact_path = artifact.get("path")
            artifact_content = artifact.get("content")
            if artifact_path and artifact_content:
                files[artifact_path] = artifact_content

        if maze_artifacts:
            files["artifacts/README.md"] = _build_artifact_readme(maze_artifacts)

    if language.lower() in {"python", "py"} and "src/train_models.py" in files:
        dataset_name = "NSL-KDD" if _is_nsl_kdd_assignment(assignment_description) else "selected dataset"
        files["README.md"] = _append_ml_readme_notes(files["README.md"], dataset_name)
        files["requirements.txt"] = _extend_python_requirements(
            files.get("requirements.txt", PYTHON_TEMPLATES["requirements.txt"]),
            [
                "kagglehub>=0.3.0",
                "pandas>=2.2.0",
                "matplotlib>=3.8.0",
                "seaborn>=0.13.0",
                "scikit-learn>=1.4.0",
            ],
        )

    if language.lower() in {"python", "py"}:
        inferred_imports = infer_python_assignment_imports(assignment_description)
        inferred_requirements = infer_python_assignment_requirements(assignment_description)

        python_targets = [
            path for path in files
            if path.endswith(".py") and not path.lower().startswith("tests/")
        ]
        for path in python_targets:
            files[path] = _inject_python_imports(files[path], inferred_imports)

        files["requirements.txt"] = _extend_python_requirements(
            files.get("requirements.txt", PYTHON_TEMPLATES["requirements.txt"]),
            inferred_requirements,
        )
    
    return files
