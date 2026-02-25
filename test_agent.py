"""
Tests for Canvas-GitHub Agent

Note: These tests require valid Canvas and GitHub credentials to run fully.
Mock tests are provided for basic functionality validation.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from templates import (
    generate_starter_files,
    get_template_for_language,
    build_agent_fact_card,
    extract_required_filenames,
    extract_required_function_names,
    normalize_slug,
    PYTHON_TEMPLATES,
    JAVA_TEMPLATES,
    JAVASCRIPT_TEMPLATES,
    CPP_TEMPLATES
)


class TestTemplates:
    """Test template generation functions."""
    
    def test_get_template_for_python(self):
        """Test getting Python template."""
        template = get_template_for_language("python")
        assert template == PYTHON_TEMPLATES
        
    def test_get_template_for_java(self):
        """Test getting Java template."""
        template = get_template_for_language("java")
        assert template == JAVA_TEMPLATES
        
    def test_get_template_for_javascript(self):
        """Test getting JavaScript template."""
        template = get_template_for_language("javascript")
        assert template == JAVASCRIPT_TEMPLATES
        
        # Test alias
        template = get_template_for_language("js")
        assert template == JAVASCRIPT_TEMPLATES
        
    def test_get_template_for_cpp(self):
        """Test getting C++ template."""
        template = get_template_for_language("cpp")
        assert template == CPP_TEMPLATES
        
        # Test alias
        template = get_template_for_language("c++")
        assert template == CPP_TEMPLATES
        
    def test_get_template_default_to_python(self):
        """Test that unknown languages default to Python."""
        template = get_template_for_language("unknown_language")
        assert template == PYTHON_TEMPLATES
        
    def test_generate_starter_files_python(self):
        """Test generating Python starter files."""
        files = generate_starter_files(
            assignment_name="Test Assignment",
            assignment_description="This is a test assignment",
            due_date="2024-12-31",
            language="python"
        )
        
        # Check that expected files are present
        assert "README.md" in files
        assert "ASSIGNMENT.md" in files
        assert "requirements.txt" in files
        assert "main.py" in files
        assert "tests/test_main.py" in files
        assert ".gitignore" in files
        
        # Check that content is properly formatted
        assert "Test Assignment" in files["README.md"]
        assert "2024-12-31" in files["README.md"]
        assert "This is a test assignment" in files["ASSIGNMENT.md"]
        assert "This is a test assignment" in files["main.py"]
        
    def test_generate_starter_files_java(self):
        """Test generating Java starter files."""
        files = generate_starter_files(
            assignment_name="Java Assignment",
            assignment_description="Java test",
            due_date="2024-12-31",
            language="java"
        )
        
        assert "README.md" in files
        assert "ASSIGNMENT.md" in files
        assert "Main.java" in files
        assert "Test.java" in files
        assert ".gitignore" in files
        
        assert "Java Assignment" in files["Main.java"]
        
    def test_generate_starter_files_javascript(self):
        """Test generating JavaScript starter files."""
        files = generate_starter_files(
            assignment_name="JS Assignment",
            assignment_description="JavaScript test",
            due_date="2024-12-31",
            language="javascript"
        )
        
        assert "README.md" in files
        assert "ASSIGNMENT.md" in files
        assert "package.json" in files
        assert "index.js" in files
        assert "index.test.js" in files
        assert ".gitignore" in files
        
        assert "JS Assignment" in files["index.js"]
        
    def test_generate_starter_files_cpp(self):
        """Test generating C++ starter files."""
        files = generate_starter_files(
            assignment_name="CPP Assignment",
            assignment_description="C++ test",
            due_date="2024-12-31",
            language="cpp"
        )
        
        assert "README.md" in files
        assert "ASSIGNMENT.md" in files
        assert "main.cpp" in files
        assert "test.cpp" in files
        assert ".gitignore" in files
        
        assert "CPP Assignment" in files["main.cpp"]
        
    def test_assignment_slug_generation(self):
        """Test that assignment names are properly converted to slugs."""
        files = generate_starter_files(
            assignment_name="My Test Assignment!",
            assignment_description="Test",
            due_date="2024-12-31",
            language="javascript"
        )
        
        # Check that the slug is used in package.json
        assert "my-test-assignment" in files["package.json"]
    
    def test_normalize_slug_basic(self):
        """Test basic slug normalization."""
        assert normalize_slug("My Test") == "my-test"
        assert normalize_slug("Hello World!") == "hello-world"
        
    def test_normalize_slug_special_chars(self):
        """Test slug normalization with special characters."""
        assert normalize_slug("My!! Test") == "my-test"
        assert normalize_slug("Test___Name") == "test-name"
        assert normalize_slug("A@#$%B") == "a-b"
        
    def test_normalize_slug_edge_cases(self):
        """Test slug normalization edge cases."""
        assert normalize_slug("!!!Test!!!") == "test"
        assert normalize_slug("---Test---") == "test"
        assert normalize_slug("Test   With   Spaces") == "test-with-spaces"

    def test_build_agent_fact_card(self):
        """Test creation of a provisional agent fact card payload."""
        fact_card = build_agent_fact_card(
            agent_id="My Agent",
            agent_name="My Agent",
            summary="Helps create repos",
            domain="education",
            capabilities=["create_repo", "generate_files"],
            registry_url="https://index.projectnanda.org",
            source_repository="https://github.com/example/my-agent",
            metadata={"course": "CS5500"},
        )

        assert fact_card["schema_version"] == "0.1-draft"
        assert fact_card["agent_id"] == "my-agent"
        assert fact_card["name"] == "My Agent"
        assert fact_card["registry"]["url"] == "https://index.projectnanda.org"
        assert fact_card["metadata"]["course"] == "CS5500"

    def test_extract_required_filenames(self):
        """Extract explicit filenames from assignment instructions."""
        text = (
            "This file must be named maze_solvers.py. "
            "Initialize `maze.txt` and include a report in Report.md."
        )
        files = extract_required_filenames(text)
        assert "maze_solvers.py" in files
        assert "maze.txt" in files
        assert "Report.md" in files

    def test_extract_required_function_names(self):
        """Extract required function names from assignment examples."""
        text = (
            "The file must include the function names: maze_solver_one, "
            "maze_solver_two and maze_solver_three. "
            "solution = maze_solver_one(maze)"
        )
        function_names = extract_required_function_names(text)
        assert "maze_solver_one" in function_names

    def test_assignment_specific_scaffold_files(self):
        """Generate requested files and solver stubs from assignment brief."""
        assignment_description = (
            "The file must be named maze_solvers.py. "
            "The file must include the function names: maze_solver_one, "
            "maze_solver_two and maze_solver_three. "
            "The maze will be stored as a text file. "
            "When you submit all code, include a README file and a report."
        )
        files = generate_starter_files(
            assignment_name="Maze Search Implementation",
            assignment_description=assignment_description,
            due_date="2026-03-11",
            language="python",
        )

        assert "maze_solvers.py" in files
        assert "def maze_solver_one(maze):" in files["maze_solvers.py"]
        assert "def maze_solver_two(maze):" in files["maze_solvers.py"]
        assert "def maze_solver_three(maze):" in files["maze_solvers.py"]
        assert "maze.txt" in files
        assert "Report.md" in files


class TestCanvasTools:
    """Test Canvas tools (mock tests)."""
    
    def test_canvas_tools_initialization(self):
        """Test that CanvasTools initializes correctly."""
        from canvas_tools import CanvasTools
        
        with patch.dict('os.environ', {
            'CANVAS_API_URL': 'https://test.canvas.com',
            'CANVAS_API_TOKEN': 'test_token'
        }):
            tools = CanvasTools()
            assert tools.canvas_url == 'https://test.canvas.com'
            assert tools.canvas_token == 'test_token'


class TestGitHubTools:
    """Test GitHub tools (mock tests)."""
    
    def test_github_tools_initialization(self):
        """Test that GitHubTools initializes correctly."""
        from github_tools import GitHubTools
        
        with patch.dict('os.environ', {
            'GITHUB_TOKEN': 'test_token',
            'GITHUB_USERNAME': 'testuser'
        }):
            tools = GitHubTools()
            assert tools.github_token == 'test_token'
            assert tools.github_username == 'testuser'


class TestCanvasGitHubAgent:
    """Test the main agent (mock tests)."""
    
    def test_agent_initialization(self):
        """Test that the agent initializes correctly."""
        from main import CanvasGitHubAgent
        
        with patch.dict('os.environ', {
            'CANVAS_API_URL': 'https://test.canvas.com',
            'CANVAS_API_TOKEN': 'test_token',
            'GITHUB_TOKEN': 'test_gh_token',
            'GITHUB_USERNAME': 'testuser'
        }):
            agent = CanvasGitHubAgent()
            assert agent.canvas_tools is not None
            assert agent.github_tools is not None
            assert agent.github_username == 'testuser'
            
    def test_create_assignment_fetcher_agent(self):
        """Test creation of assignment fetcher agent."""
        from main import CanvasGitHubAgent
        
        with patch.dict('os.environ', {
            'CANVAS_API_TOKEN': 'test_token',
            'GITHUB_TOKEN': 'test_gh_token',
            'GITHUB_USERNAME': 'testuser'
        }):
            agent = CanvasGitHubAgent()
            fetcher = agent.create_assignment_fetcher_agent()
            assert fetcher.role == "Assignment Fetcher"
            
    def test_create_repository_initializer_agent(self):
        """Test creation of repository initializer agent."""
        from main import CanvasGitHubAgent
        
        with patch.dict('os.environ', {
            'CANVAS_API_TOKEN': 'test_token',
            'GITHUB_TOKEN': 'test_gh_token',
            'GITHUB_USERNAME': 'testuser'
        }):
            agent = CanvasGitHubAgent()
            initializer = agent.create_repository_initializer_agent()
            assert initializer.role == "Repository Initializer"

    def test_infer_assignment_type_coding(self):
        """Infer coding assignment from assignment text."""
        from main import CanvasGitHubAgent

        with patch.dict('os.environ', {
            'CANVAS_API_TOKEN': 'test_token',
            'GITHUB_TOKEN': 'test_gh_token',
            'GITHUB_USERNAME': 'testuser'
        }):
            agent = CanvasGitHubAgent()
            assignment = {
                "name": "Implement Graph Search in Python",
                "description": "Write code, run tests, and submit a GitHub repository."
            }
            assert agent.infer_assignment_type(assignment) == "coding"

    def test_infer_assignment_type_writing(self):
        """Infer writing assignment from assignment text."""
        from main import CanvasGitHubAgent

        with patch.dict('os.environ', {
            'CANVAS_API_TOKEN': 'test_token',
            'GITHUB_TOKEN': 'test_gh_token',
            'GITHUB_USERNAME': 'testuser'
        }):
            agent = CanvasGitHubAgent()
            assignment = {
                "name": "Critical Reflection Essay",
                "description": "Write a 1200-word essay in APA format with citations."
            }
            assert agent.infer_assignment_type(assignment) == "writing"

    def test_run_routes_coding_to_github(self):
        """Run routes coding assignments to GitHub creation path."""
        from main import CanvasGitHubAgent

        with patch.dict('os.environ', {
            'CANVAS_API_TOKEN': 'test_token',
            'GITHUB_TOKEN': 'test_gh_token',
            'GITHUB_USERNAME': 'testuser'
        }):
            agent = CanvasGitHubAgent()
            assignment = {
                "name": "Coding Assignment",
                "description": "Implement and test a function",
                "due_at": "2026-03-01"
            }

            agent.create_repository_task = AsyncMock(return_value={
                "repository": {"name": "coding-assignment", "owner": {"login": "testuser"}},
                "files_created": ["README.md"],
                "assignment": assignment,
            })
            agent.create_notion_page_task = AsyncMock(return_value=None)

            result = asyncio.run(
                agent.run(
                    course_id=123,
                    assignment_data=assignment,
                    assignment_type="coding",
                )
            )

            agent.create_repository_task.assert_awaited_once()
            agent.create_notion_page_task.assert_not_awaited()
            assert result["destination"] == "github"

    def test_run_routes_writing_to_notion(self):
        """Run routes writing assignments to Notion page creation path."""
        from main import CanvasGitHubAgent

        with patch.dict('os.environ', {
            'CANVAS_API_TOKEN': 'test_token',
            'GITHUB_TOKEN': 'test_gh_token',
            'GITHUB_USERNAME': 'testuser'
        }):
            agent = CanvasGitHubAgent()
            assignment = {
                "name": "Writing Assignment",
                "description": "Write a reflection paper",
                "due_at": "2026-03-01"
            }

            agent.create_repository_task = AsyncMock(return_value=None)
            agent.create_notion_page_task = AsyncMock(return_value={
                "page": {"url": "https://notion.so/example"},
                "assignment": assignment,
            })

            result = asyncio.run(
                agent.run(
                    course_id=123,
                    assignment_data=assignment,
                    assignment_type="writing",
                )
            )

            agent.create_repository_task.assert_not_awaited()
            agent.create_notion_page_task.assert_awaited_once()
            assert result["destination"] == "notion"


class TestNotionTools:
    """Test Notion tools initialization."""

    def test_notion_tools_initialization(self):
        """Test that NotionTools initializes correctly."""
        from notion_tools import NotionTools

        with patch.dict('os.environ', {
            'NOTION_TOKEN': 'test_notion_token',
            'NOTION_PARENT_PAGE_ID': 'test_page_id'
        }):
            tools = NotionTools()
            assert tools.notion_token == 'test_notion_token'
            assert tools.parent_page_id == 'test_page_id'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
