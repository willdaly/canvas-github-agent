"""
Tests for Canvas-GitHub Agent

Note: These tests require valid Canvas and GitHub credentials to run fully.
Mock tests are provided for basic functionality validation.
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import pytest
from scaffolding.templates import (
    assignment_mentions_jupyter_notebook,
    build_service_fact_card,
    build_service_oasf_record,
    infer_python_assignment_imports,
    infer_python_assignment_requirements,
    generate_starter_files,
    get_template_for_language,
    build_agent_fact_card,
    infer_python_notebook_imports,
    infer_python_notebook_requirements,
    extract_required_filenames,
    extract_required_function_names,
    normalize_slug,
    PYTHON_TEMPLATES,
    R_TEMPLATES,
)


class TestTemplates:
    """Test template generation functions."""
    
    def test_get_template_for_python(self):
        """Test getting Python template."""
        template = get_template_for_language("python")
        assert template == PYTHON_TEMPLATES
        
    def test_get_template_for_r(self):
        """Test getting R template."""
        template = get_template_for_language("r")
        assert template == R_TEMPLATES

        template = get_template_for_language("rscript")
        assert template == R_TEMPLATES
        
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
        
    def test_generate_starter_files_r(self):
        """Test generating R starter files."""
        files = generate_starter_files(
            assignment_name="R Assignment",
            assignment_description="R test",
            due_date="2024-12-31",
            language="r"
        )

        assert "README.md" in files
        assert "ASSIGNMENT.md" in files
        assert "main.R" in files
        assert "tests/test_main.R" in files
        assert ".gitignore" in files

        assert "R Assignment" in files["main.R"]
    
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

    def test_build_service_fact_card_matches_checked_in_json(self):
        """The checked-in service fact card should match the generated payload."""
        expected = build_service_fact_card()
        fact_card_path = (
            Path(__file__).resolve().parent.parent
            / "metadata"
            / "agent-fact-cards"
            / "service.canvas-assignment-workflow.fact-card.json"
        )

        with fact_card_path.open("r", encoding="utf-8") as handle:
            checked_in = json.load(handle)

        assert checked_in == expected
        assert checked_in["name"] == "Canvas Assignment Workflow"
        assert checked_in["metadata"]["architecture"] == "deterministic workflow orchestrator"
        assert checked_in["interoperability"]["mcp"] == "canvas-github-agent-mcp"

    def test_build_service_oasf_record_matches_checked_in_json(self):
        """The checked-in OASF record should match the generated payload."""
        expected = build_service_oasf_record()
        record_path = (
            Path(__file__).resolve().parent.parent
            / "metadata"
            / "oasf-records"
            / "service.canvas-assignment-workflow.record.json"
        )

        with record_path.open("r", encoding="utf-8") as handle:
            checked_in = json.load(handle)

        assert checked_in == expected
        assert checked_in["schema_version"] == "1.0.0"
        assert checked_in["skills"][0]["name"] == "agent_orchestration/task_decomposition"
        assert checked_in["skills"][0]["id"] == 1001
        assert checked_in["locators"][0]["type"] == "source_code"
        assert checked_in["locators"][1]["type"] == "url"
        assert checked_in["annotations"]["mcp_stdio_command"] == "canvas-github-agent-mcp"
        assert checked_in["annotations"]["task_submission_endpoint"] == "http://localhost:8000/tasks"
        assert checked_in["annotations"]["task_status_schema"] == "task_status_v1"
        assert checked_in["annotations"]["health_endpoint"] == "http://localhost:8000/health"

    def test_extract_required_filenames(self):
        """Extract explicit filenames from assignment instructions."""
        text = (
            "This file must be named maze_solvers.py. "
            "Initialize `maze.txt`, include a report in Report.md, "
            "and submit analysis.ipynb."
        )
        files = extract_required_filenames(text)
        assert "maze_solvers.py" in files
        assert "maze.txt" in files
        assert "Report.md" in files
        assert "analysis.ipynb" in files

    def test_assignment_mentions_jupyter_notebook(self):
        """Detect explicit notebook submission requirements."""
        assert assignment_mentions_jupyter_notebook(
            "Submission: upload a Jupyter notebook file."
        )
        assert assignment_mentions_jupyter_notebook(
            "Turn in your work as an analysis.ipynb file."
        )
        assert not assignment_mentions_jupyter_notebook(
            "Implement the functions in main.py and submit your code."
        )

    def test_infer_python_notebook_dependencies_for_bayes_theorem(self):
        """Infer notebook dependencies for Bayes-theorem assignments."""
        description = (
            "Use Bayes theorem to update the posterior after observing the data."
        )

        assert infer_python_notebook_imports(description) == ["from scipy.stats import beta"]
        assert infer_python_notebook_requirements(description) == ["scipy>=1.11.0"]

    def test_infer_python_assignment_dependencies_from_library_mentions(self):
        """Infer normal Python imports and requirements from assignment text."""
        description = "Use pandas and matplotlib to analyze the CSV and plot the results."

        assert infer_python_assignment_imports(description) == [
            "import pandas as pd",
            "import matplotlib.pyplot as plt",
        ]
        assert infer_python_assignment_requirements(description) == [
            "pandas>=2.2.0",
            "matplotlib>=3.8.0",
        ]

    def test_infer_python_assignment_prefers_explicit_import_lines(self):
        """Preserve explicit import lines found directly in the assignment text."""
        description = (
            "Starter code should include import pandas as pd and from bs4 import BeautifulSoup."
        )

        assert infer_python_assignment_imports(description) == [
            "import pandas as pd",
            "from bs4 import BeautifulSoup",
        ]

    def test_python_project_adds_imports_and_requirements_from_assignment(self):
        """Normal Python scaffolds should import libraries mentioned in the assignment."""
        files = generate_starter_files(
            assignment_name="Data Plotting",
            assignment_description=(
                "Use pandas to load the dataset and matplotlib to plot the results."
            ),
            due_date="2026-03-19",
            language="python",
        )

        assert "import pandas as pd" in files["main.py"]
        assert "import matplotlib.pyplot as plt" in files["main.py"]
        assert "pandas>=2.2.0" in files["requirements.txt"]
        assert "matplotlib>=3.8.0" in files["requirements.txt"]

    def test_extract_required_function_names(self):
        """Extract required function names from assignment examples."""
        text = (
            "The file must include the function names: maze_solver_one, "
            "maze_solver_two and maze_solver_three. "
            "solution = maze_solver_one(maze)"
        )
        function_names = extract_required_function_names(text)
        assert "maze_solver_one" in function_names
        assert "maze_solver_two" in function_names
        assert "maze_solver_three" in function_names

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

    def test_python_function_stubs_default_to_main(self):
        """Create Python function stubs in main.py when no source file is named."""
        files = generate_starter_files(
            assignment_name="Stats Functions",
            assignment_description=(
                "Implement the functions normalize_scores, summarize_results, "
                "and plot_summary."
            ),
            due_date="2026-03-19",
            language="python",
        )

        assert "def normalize_scores():" in files["main.py"]
        assert "def summarize_results():" in files["main.py"]
        assert "def plot_summary():" in files["main.py"]

    def test_r_function_stubs_use_named_source_file(self):
        """Create R function stubs in an explicitly requested R file."""
        files = generate_starter_files(
            assignment_name="Data Analysis",
            assignment_description=(
                "Include a file named analysis.R. "
                "The functions called clean_data and build_plot should be defined there."
            ),
            due_date="2026-03-19",
            language="r",
        )

        assert "analysis.R" in files
        assert "clean_data <- function()" in files["analysis.R"]
        assert "build_plot <- function()" in files["analysis.R"]
        assert "main <- function()" not in files["analysis.R"]

    def test_python_notebook_added_when_submission_mentions_jupyter(self):
        """Add a notebook scaffold for Python notebook submissions."""
        files = generate_starter_files(
            assignment_name="Notebook Assignment",
            assignment_description=(
                "Submission information: upload a Jupyter notebook. "
                "Implement the functions clean_data and build_chart."
            ),
            due_date="2026-03-19",
            language="python",
        )

        assert "main.ipynb" in files
        assert '"cell_type": "markdown"' in files["main.ipynb"]
        assert '"cell_type": "code"' in files["main.ipynb"]
        assert "def clean_data():" in files["main.ipynb"]
        assert "def build_chart():" in files["main.ipynb"]

    def test_python_bayes_notebook_adds_imports_and_requirement(self):
        """Bayes-theorem notebook assignments should get a usable stats import."""
        files = generate_starter_files(
            assignment_name="Bayes Notebook",
            assignment_description=(
                "Submission information: upload a Jupyter notebook. "
                "Use Bayes theorem to compute a posterior distribution."
            ),
            due_date="2026-03-19",
            language="python",
        )

        notebook = json.loads(files["main.ipynb"])
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]

        assert len(code_cells) == 2
        assert "from scipy.stats import beta\n" in code_cells[0]["source"]
        assert "scipy>=1.11.0" in files["requirements.txt"]

    def test_python_notebook_combines_library_mentions_and_topic_imports(self):
        """Notebook scaffolds should combine explicit library mentions with topic imports."""
        files = generate_starter_files(
            assignment_name="Bayes Data Notebook",
            assignment_description=(
                "Submission information: upload a Jupyter notebook. "
                "Use pandas for the dataset and apply Bayes theorem to compute a posterior."
            ),
            due_date="2026-03-19",
            language="python",
        )

        notebook = json.loads(files["main.ipynb"])
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]

        assert "import pandas as pd\n" in code_cells[0]["source"]
        assert "from scipy.stats import beta\n" in code_cells[0]["source"]
        assert "pandas>=2.2.0" in files["requirements.txt"]
        assert "scipy>=1.11.0" in files["requirements.txt"]

    def test_python_notebook_uses_explicit_filename(self):
        """Honor an explicit notebook filename from the assignment brief."""
        files = generate_starter_files(
            assignment_name="Analysis Notebook",
            assignment_description=(
                "Create a file named analysis.ipynb. "
                "Your submission should be a notebook upload."
            ),
            due_date="2026-03-19",
            language="python",
        )

        assert "analysis.ipynb" in files
        assert "main.ipynb" not in files


class TestCanvasTools:
    """Test Canvas tools (mock tests)."""
    
    def test_canvas_tools_initialization(self):
        """Test that CanvasTools initializes correctly."""
        from tools.canvas_tools import CanvasTools
        
        with patch.dict('os.environ', {
            'CANVAS_API_URL': 'https://test.canvas.com',
            'CANVAS_API_TOKEN': 'test_token'
        }):
            tools = CanvasTools()
            assert tools.canvas_url == 'https://test.canvas.com'
            assert tools.canvas_token == 'test_token'

    def test_canvas_tools_mcp_toggle_false(self):
        """Test that CANVAS_USE_MCP disables MCP path."""
        from tools.canvas_tools import CanvasTools

        with patch.dict('os.environ', {
            'CANVAS_API_URL': 'https://test.canvas.com',
            'CANVAS_API_TOKEN': 'test_token',
            'CANVAS_USE_MCP': 'false'
        }):
            tools = CanvasTools()
            assert tools.use_mcp is False

    def test_list_courses_falls_back_to_direct_api(self):
        """If MCP path errors, list_courses should use direct Canvas REST fallback."""
        from tools.canvas_tools import CanvasTools

        with patch.dict('os.environ', {
            'CANVAS_API_URL': 'https://test.canvas.com',
            'CANVAS_API_TOKEN': 'test_token',
            'CANVAS_USE_MCP': 'true'
        }):
            tools = CanvasTools()

            with patch.object(
                CanvasTools,
                'get_canvas_session',
                side_effect=RuntimeError('mcp unavailable'),
            ), patch.object(
                CanvasTools,
                '_direct_list_courses',
                return_value=[{'id': 1, 'name': 'CS Test'}],
            ) as direct_mock:
                result = asyncio.run(tools.list_courses())

            assert result == [{'id': 1, 'name': 'CS Test'}]
            direct_mock.assert_called_once()

    def test_get_course_assignments_falls_back_to_direct_api(self):
        """If MCP path errors, assignment listing should use direct Canvas REST fallback."""
        from tools.canvas_tools import CanvasTools

        with patch.dict('os.environ', {
            'CANVAS_API_URL': 'https://test.canvas.com',
            'CANVAS_API_TOKEN': 'test_token',
            'CANVAS_USE_MCP': 'true'
        }):
            tools = CanvasTools()

            with patch.object(
                CanvasTools,
                'get_canvas_session',
                side_effect=RuntimeError('mcp unavailable'),
            ), patch.object(
                CanvasTools,
                '_direct_get_course_assignments',
                return_value=[{'id': 2, 'name': 'HW1'}],
            ) as direct_mock:
                result = asyncio.run(tools.get_course_assignments(123))

            assert result == [{'id': 2, 'name': 'HW1'}]
            direct_mock.assert_called_once_with(123)

    def test_normalize_assignment_marks_completed_from_submission(self):
        """Assignment normalization should expose completion-friendly fields."""
        from tools.canvas_tools import CanvasTools

        with patch.dict('os.environ', {
            'CANVAS_API_URL': 'https://test.canvas.com',
            'CANVAS_API_TOKEN': 'test_token'
        }):
            tools = CanvasTools()
            assignment = tools._normalize_assignment({
                'id': 7,
                'name': 'Essay Draft',
                'description': 'Submit draft',
                'due_at': '2026-03-20T12:00:00Z',
                'submission': {'workflow_state': 'submitted', 'submitted_at': '2026-03-18T11:00:00Z'},
            })

        assert assignment['is_completed'] is True
        assert assignment['workflow_state'] == 'submitted'
        assert assignment['submitted_at'] == '2026-03-18T11:00:00Z'


class TestGitHubTools:
    """Test GitHub tools (mock tests)."""
    
    def test_github_tools_initialization(self):
        """Test that GitHubTools initializes correctly."""
        from tools.github_tools import GitHubTools
        
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
        from app.agent import CanvasGitHubAgent
        
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
            
    def test_infer_assignment_type_coding(self):
        """Infer coding assignment from assignment text."""
        from app.agent import CanvasGitHubAgent

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
        from app.agent import CanvasGitHubAgent

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
        from app.agent import CanvasGitHubAgent

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

            agent.create_repository_for_assignment = AsyncMock(return_value={
                "repository": {"name": "coding-assignment", "owner": {"login": "testuser"}},
                "files_created": ["README.md"],
                "assignment": assignment,
            })
            agent.create_notion_page_for_assignment = AsyncMock(return_value=None)

            result = asyncio.run(
                agent.run(
                    course_id=123,
                    assignment_data=assignment,
                    assignment_type="coding",
                )
            )

            agent.create_repository_for_assignment.assert_awaited_once()
            agent.create_notion_page_for_assignment.assert_not_awaited()
            assert result["destination"] == "github"

    def test_run_routes_writing_to_notion(self):
        """Run routes writing assignments to Notion page creation path."""
        from app.agent import CanvasGitHubAgent

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

            agent.create_repository_for_assignment = AsyncMock(return_value=None)
            agent.create_notion_page_for_assignment_with_mode = AsyncMock(return_value={
                "page": {"url": "https://notion.so/example"},
                "assignment": assignment,
            })

            result = asyncio.run(
                agent.run(
                    course_id=123,
                    assignment_data=assignment,
                    assignment_type="writing",
                    notion_content_mode="text",
                )
            )

            agent.create_repository_for_assignment.assert_not_awaited()
            agent.create_notion_page_for_assignment_with_mode.assert_awaited_once_with(
                assignment,
                content_mode="text",
            )
            assert result["destination"] == "notion"

    def test_run_routes_writing_to_motion(self):
        """Compatibility alias for a historical typo in CI test selectors."""
        self.test_run_routes_writing_to_notion()


class TestNotionTools:
    """Test Notion tools initialization."""

    def test_notion_tools_initialization(self):
        """Test that NotionTools initializes correctly."""
        from tools.notion_tools import NotionTools

        with patch.dict('os.environ', {
            'NOTION_TOKEN': 'test_notion_token',
            'NOTION_PARENT_PAGE_ID': 'test_page_id'
        }):
            tools = NotionTools()
            assert tools.notion_token == 'test_notion_token'
            assert tools.parent_page_id == 'test_page_id'

    def test_text_mode_uses_single_paragraph_payload(self):
        """Text mode should avoid adding structured heading/due-date blocks."""
        from tools.notion_tools import NotionTools

        with patch.dict('os.environ', {
            'NOTION_TOKEN': 'test_notion_token',
            'NOTION_PARENT_PAGE_ID': 'test_page_id'
        }):
            tools = NotionTools()
            with patch('tools.notion_tools.requests.post') as post_mock:
                response_mock = Mock()
                response_mock.raise_for_status.return_value = None
                response_mock.json.return_value = {'url': 'https://notion.so/test'}
                post_mock.return_value = response_mock

                result = tools._create_assignment_page_sync(
                    title='Writing Assignment',
                    description='Plain text body',
                    due_date='2026-03-20',
                    content_mode='text',
                )

        assert result == {'url': 'https://notion.so/test'}
        payload = post_mock.call_args.kwargs['json']
        assert len(payload['children']) == 1
        assert payload['children'][0]['type'] == 'paragraph'


class TestWorkflowHelpers:
    """Test pure helper functions used by orchestrator flow."""

    def test_choose_next_assignment_prefers_soonest_upcoming(self):
        from app.agent import choose_next_assignment

        now = datetime(2026, 3, 19, 12, 0, 0)
        assignments = [
            {
                "id": 1,
                "name": "Later",
                "due_at": "2026-03-22T10:00:00",
                "created_at": "2026-03-10T08:00:00",
            },
            {
                "id": 2,
                "name": "Sooner",
                "due_at": "2026-03-20T09:00:00",
                "created_at": "2026-03-11T08:00:00",
            },
        ]

        result = choose_next_assignment(assignments, now=now)
        assert result["id"] == 2

    def test_choose_next_assignment_falls_back_to_latest_created(self):
        from app.agent import choose_next_assignment

        now = datetime(2026, 3, 19, 12, 0, 0)
        assignments = [
            {
                "id": 1,
                "name": "Older",
                "due_at": "2026-03-01T10:00:00",
                "created_at": "2026-02-01T08:00:00",
            },
            {
                "id": 2,
                "name": "Newest",
                "due_at": None,
                "created_at": "2026-03-10T08:00:00",
            },
        ]

        result = choose_next_assignment(assignments, now=now)
        assert result["id"] == 2

    def test_fetch_assignment_uses_explicit_assignment_id(self):
        from app.agent import CanvasGitHubAgent

        with patch.dict('os.environ', {
            'CANVAS_API_TOKEN': 'test_token',
            'GITHUB_TOKEN': 'test_gh_token',
            'GITHUB_USERNAME': 'testuser'
        }):
            agent = CanvasGitHubAgent()
            expected = {"id": 99, "name": "Explicit Assignment"}
            agent.canvas_tools.get_assignment_details = AsyncMock(return_value=expected)
            agent.canvas_tools.get_course_assignments = AsyncMock(return_value=[])

            result = asyncio.run(agent.fetch_assignment(course_id=123, assignment_id=99))

            agent.canvas_tools.get_assignment_details.assert_awaited_once_with(123, 99)
            agent.canvas_tools.get_course_assignments.assert_not_awaited()
            assert result == expected

    def test_get_missing_notion_config(self):
        from app.agent import get_missing_notion_config

        missing = get_missing_notion_config({"NOTION_TOKEN": "abc"})
        assert missing == ["NOTION_PARENT_PAGE_ID"]

    def test_validate_notion_config(self):
        from app.agent import CanvasGitHubAgent

        with patch.dict('os.environ', {
            'CANVAS_API_TOKEN': 'test_token',
            'GITHUB_TOKEN': 'test_gh_token',
            'GITHUB_USERNAME': 'testuser',
            'NOTION_TOKEN': '',
            'NOTION_PARENT_PAGE_ID': ''
        }, clear=False):
            agent = CanvasGitHubAgent()
            missing = agent.validate_notion_config()

        assert "NOTION_TOKEN" in missing
        assert "NOTION_PARENT_PAGE_ID" in missing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
