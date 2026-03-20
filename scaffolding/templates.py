"""
Starter code templates for different types of assignments.
"""
import json
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
            "mcp": "#registry:server-name",
        },
        "registry": {
            "url": registry_url,
            "status": "not_registered",
        },
        "source_repository": source_repository,
        "metadata": metadata or {},
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


def _build_python_stub_file(
    assignment_name: str,
    assignment_summary: str,
    function_names: List[str],
    include_main: bool,
) -> str:
    blocks = [
        f'"""{assignment_name}\n\n{assignment_summary}\n"""',
        "",
    ]

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
    include_main: bool,
) -> str:
    if language in {"python", "py"}:
        return _build_python_stub_file(assignment_name, assignment_summary, function_names, include_main)
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
    assignment_summary = (short_description or assignment_description[:200]).strip()

    requested_lower = {path.lower() for path in requested_files}

    if language_lower in {"python", "py"} and "maze_solvers.py" in requested_lower:
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

        function_blocks = []
        for function_name in maze_functions:
            function_blocks.append(
                f"def {function_name}(maze):\n"
                "    \"\"\"Solve the maze and return the solved maze output.\"\"\"\n"
                "    return maze\n"
            )

        files["maze_solvers.py"] = (
            f'"""{assignment_name} maze solver interface."""\n\n' +
            "\n\n".join(function_blocks) +
            "\n"
        )

    if "maze.txt" in requested_lower or "maze" in assignment_description.lower():
        files["maze.txt"] = (
            "10 6\n"
            "XXXXXXXXXX\n"
            "X        S\n"
            "X XXXXXX X\n"
            "X X    XXX\n"
            "X   XX   E\n"
            "XXXXXXXXXX\n"
        )

    if "report.md" in requested_lower or "report" in assignment_description.lower():
        files["Report.md"] = (
            f"# {assignment_name} Report\n\n"
            "## Introduction to Search Algorithms\n\n"
            "## Selected Algorithms\n\n"
            "## Heuristics Used\n\n"
            "## Performance Comparison\n\n"
            "## Optimality, Time, and Space Analysis\n\n"
            "## Maze Variations and Performance Impact\n\n"
            "## Real-life Application\n"
        )

    if language_lower in {"python", "py"} and assignment_mentions_jupyter_notebook(assignment_description):
        notebook_imports = infer_python_notebook_imports(assignment_description)
        notebook_target = _select_notebook_target(requested_files)
        files[notebook_target] = _build_python_notebook_file(
            assignment_name=assignment_name,
            assignment_summary=assignment_summary,
            function_names=requested_functions,
            import_lines=notebook_imports,
        )
        files["requirements.txt"] = _extend_python_requirements(
            files.get("requirements.txt", PYTHON_TEMPLATES["requirements.txt"]),
            infer_python_notebook_requirements(assignment_description),
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
                include_main=include_main,
            )

    return files


def generate_starter_files(
    assignment_name: str,
    assignment_description: str,
    due_date: str,
    language: str = "python",
    short_description: str = "",
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

    files.update(
        build_assignment_specific_files(
            assignment_name=assignment_name,
            assignment_description=assignment_description,
            language=language,
            short_description=short_description,
        )
    )
    
    return files
