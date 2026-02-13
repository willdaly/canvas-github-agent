"""
Tests for Canvas-GitHub Agent

Note: These tests require valid Canvas and GitHub credentials to run fully.
Mock tests are provided for basic functionality validation.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from templates import (
    generate_starter_files,
    get_template_for_language,
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
        assert "requirements.txt" in files
        assert "main.py" in files
        assert "tests/test_main.py" in files
        assert ".gitignore" in files
        
        # Check that content is properly formatted
        assert "Test Assignment" in files["README.md"]
        assert "2024-12-31" in files["README.md"]
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


class TestCanvasTools:
    """Test Canvas tools (mock tests)."""
    
    @pytest.mark.asyncio
    async def test_canvas_tools_initialization(self):
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
    
    @pytest.mark.asyncio
    async def test_github_tools_initialization(self):
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
