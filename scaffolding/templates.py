"""
Starter code templates for different types of assignments.
"""
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

JAVA_TEMPLATES = {
    "README.md": """# {assignment_name}

## Overview
This repository contains starter code for this assignment.

## Full Assignment
See `ASSIGNMENT.md` for the complete assignment brief.

## Due Date
{due_date}

## Setup
Ensure you have Java 11+ installed.

## Building
```bash
javac Main.java
```

## Running
```bash
java Main
```

## Testing
```bash
javac -cp .:junit-platform-console-standalone.jar Test.java
java -jar junit-platform-console-standalone.jar --class-path . --scan-class-path
```

## Submission
Complete the implementation in `Main.java` and ensure all tests pass.
""",
    "Main.java": """/**
 * {assignment_name}
 * 
 * {assignment_description}
 */
public class Main {{
    public static void main(String[] args) {{
        // TODO: Implement your solution here
        System.out.println("Hello, World!");
    }}
}}
""",
    "Test.java": """import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for {assignment_name}
 */
public class Test {{
    @Test
    public void testMain() {{
        // TODO: Add your test cases here
        assertTrue(true);
    }}
}}
""",
    ".gitignore": """# Java
*.class
*.jar
*.war
*.ear
target/
build/
.gradle/
.idea/
*.iml
"""
}

JAVASCRIPT_TEMPLATES = {
    "README.md": """# {assignment_name}

## Overview
This repository contains starter code for this assignment.

## Full Assignment
See `ASSIGNMENT.md` for the complete assignment brief.

## Due Date
{due_date}

## Setup
```bash
npm install
```

## Running Tests
```bash
npm test
```

## Running the Application
```bash
npm start
```

## Submission
Complete the implementation in `index.js` and ensure all tests pass.
""",
    "package.json": """{{
  "name": "{assignment_slug}",
  "version": "1.0.0",
  "description": "{assignment_description}",
  "main": "index.js",
  "scripts": {{
    "test": "jest",
    "start": "node index.js"
  }},
  "devDependencies": {{
    "jest": "^29.0.0"
  }}
}}
""",
    "index.js": """/**
 * {assignment_name}
 * 
 * {assignment_description}
 */

function main() {{
  // TODO: Implement your solution here
  console.log('Hello, World!');
}}

if (require.main === module) {{
  main();
}}

module.exports = {{ main }};
""",
    "index.test.js": """/**
 * Tests for {assignment_name}
 */
const {{ main }} = require('./index');

describe('{assignment_name}', () => {{
  test('main function exists', () => {{
    expect(main).toBeDefined();
  }});
  
  // TODO: Add your test cases here
}});
""",
    ".gitignore": """# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
.env
.DS_Store
coverage/
dist/
"""
}

CPP_TEMPLATES = {
    "README.md": """# {assignment_name}

## Overview
This repository contains starter code for this assignment.

## Full Assignment
See `ASSIGNMENT.md` for the complete assignment brief.

## Due Date
{due_date}

## Setup
Ensure you have a C++ compiler (g++ or clang++) installed.

## Building
```bash
g++ -std=c++17 main.cpp -o main
```

## Running
```bash
./main
```

## Testing
```bash
g++ -std=c++17 test.cpp -o test
./test
```

## Submission
Complete the implementation in `main.cpp` and ensure all tests pass.
""",
    "main.cpp": """/**
 * {assignment_name}
 * 
 * {assignment_description}
 */
#include <iostream>

int main() {{
    // TODO: Implement your solution here
    std::cout << "Hello, World!" << std::endl;
    return 0;
}}
""",
    "test.cpp": """/**
 * Tests for {assignment_name}
 */
#include <cassert>
#include <iostream>

void test_main() {{
    // TODO: Add your test cases here
    assert(true);
    std::cout << "All tests passed!" << std::endl;
}}

int main() {{
    test_main();
    return 0;
}}
""",
    ".gitignore": """# C++
*.o
*.exe
*.out
main
test
.vscode/
.idea/
"""
}

# Map of language/type keywords to templates
TEMPLATE_MAP = {
    "python": PYTHON_TEMPLATES,
    "py": PYTHON_TEMPLATES,
    "java": JAVA_TEMPLATES,
    "javascript": JAVASCRIPT_TEMPLATES,
    "js": JAVASCRIPT_TEMPLATES,
    "node": JAVASCRIPT_TEMPLATES,
    "cpp": CPP_TEMPLATES,
    "c++": CPP_TEMPLATES,
}


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
    
    # Then try partial match, but prioritize longer keys to avoid "java" matching "javascript"
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
        r"(?:py|txt|md|json|ya?ml|csv|java|js|cpp|cxx|cc|h|hpp))\b"
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

    names = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", assignment_description)
    filtered = []
    seen = set()
    for name in names:
        lower = name.lower()
        if name.startswith("__"):
            continue
        if lower in {"solution", "print", "main"}:
            continue
        if name not in seen:
            seen.add(name)
            filtered.append(name)
    return filtered


def build_assignment_specific_files(
    assignment_name: str,
    assignment_description: str,
    language: str,
) -> Dict[str, str]:
    """Generate files that are explicitly requested by assignment instructions."""
    if language.lower() not in {"python", "py"}:
        return {}

    files: Dict[str, str] = {}
    requested_files = extract_required_filenames(assignment_description)
    requested_functions = extract_required_function_names(assignment_description)

    requested_lower = {path.lower() for path in requested_files}

    if "maze_solvers.py" in requested_lower:
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
        )
    )
    
    return files
