"""
Starter code templates for different types of assignments.
"""

PYTHON_TEMPLATES = {
    "README.md": """# {assignment_name}

## Description
{assignment_description}

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

## Description
{assignment_description}

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

## Description
{assignment_description}

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

## Description
{assignment_description}

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


def generate_starter_files(
    assignment_name: str,
    assignment_description: str,
    due_date: str,
    language: str = "python"
) -> dict:
    """
    Generate starter files for an assignment.
    
    Args:
        assignment_name: Name of the assignment
        assignment_description: Description of the assignment
        due_date: Due date string
        language: Programming language
        
    Returns:
        Dictionary mapping file paths to their content
    """
    template = get_template_for_language(language)
    assignment_slug = assignment_name.lower().replace(" ", "-").replace("_", "-")
    
    files = {}
    for filepath, content_template in template.items():
        content = content_template.format(
            assignment_name=assignment_name,
            assignment_description=assignment_description,
            due_date=due_date,
            assignment_slug=assignment_slug
        )
        files[filepath] = content
    
    return files
