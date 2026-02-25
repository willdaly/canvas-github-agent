"""
Canvas-GitHub Agent using CrewAI

This agent fetches assignments from Canvas LMS and creates GitHub repositories
with appropriate starter code and file structure.
"""
import os
import asyncio
import re
from datetime import datetime
from dateutil import parser as dateutil_parser
from typing import Optional
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from canvas_tools import CanvasTools
from github_tools import GitHubTools
from templates import generate_starter_files, normalize_slug, html_to_markdown
from notion_tools import NotionTools


# Load environment variables
load_dotenv()


class CanvasGitHubAgent:
    """Main agent class for Canvas-GitHub integration."""
    
    def __init__(self):
        self.canvas_tools = CanvasTools()
        self.github_tools = GitHubTools()
        self.notion_tools = NotionTools()
        self.github_username = os.getenv("GITHUB_USERNAME")
        _org = os.getenv("GITHUB_ORG", "").strip()
        self.github_org = _org if _org and not _org.startswith("#") else ""

    @staticmethod
    def strip_html(text: str) -> str:
        """Remove HTML tags from assignment text."""
        if not text:
            return ""
        return re.sub(r'<[^>]+>', '', text).strip()

    def infer_assignment_type(self, assignment: dict) -> str:
        """Infer whether an assignment is coding or writing based on content."""
        assignment_name = assignment.get("name", "")
        assignment_description = self.strip_html(assignment.get("description", ""))
        text = f"{assignment_name} {assignment_description}".lower()

        coding_keywords = {
            "code", "coding", "program", "programming", "algorithm", "implement",
            "function", "class", "method", "script", "compile", "run", "test",
            "pytest", "java", "python", "javascript", "c++", "cpp", "repository",
            "github", "git", "api", "software", "debug", "build"
        }
        writing_keywords = {
            "essay", "paper", "reflection", "journal", "discussion", "thesis",
            "annotated bibliography", "literature review", "report", "summary",
            "argument", "draft", "citation", "mla", "apa", "writing", "paragraph"
        }

        coding_score = sum(1 for keyword in coding_keywords if keyword in text)
        writing_score = sum(1 for keyword in writing_keywords if keyword in text)

        return "coding" if coding_score >= writing_score else "writing"

    def confirm_assignment_type(self, inferred_type: str) -> str:
        """Prompt user to confirm or override inferred assignment type."""
        while True:
            response = input(
                f"\nInferred assignment type: {inferred_type}. Confirm? "
                "[c]oding/[w]riting (Enter to accept): "
            ).strip().lower()

            if response == "":
                return inferred_type
            if response in {"c", "coding"}:
                return "coding"
            if response in {"w", "writing"}:
                return "writing"

            print("❌ Please enter 'c', 'w', 'coding', 'writing', or press Enter.")

    def validate_notion_config(self) -> list[str]:
        """Return missing Notion environment variables required for writing flow."""
        missing = []
        if not os.getenv("NOTION_TOKEN", "").strip():
            missing.append("NOTION_TOKEN")
        if not os.getenv("NOTION_PARENT_PAGE_ID", "").strip():
            missing.append("NOTION_PARENT_PAGE_ID")
        return missing
        
    def create_assignment_fetcher_agent(self) -> Agent:
        """Create an agent responsible for fetching Canvas assignments."""
        return Agent(
            role="Assignment Fetcher",
            goal="Fetch assignment details from Canvas LMS",
            backstory=(
                "You are an expert at retrieving and understanding assignment "
                "requirements from Canvas LMS. You carefully extract all relevant "
                "information including assignment name, description, due dates, "
                "and any technical requirements."
            ),
            verbose=True,
            allow_delegation=False,
        )
    
    def create_repository_initializer_agent(self) -> Agent:
        """Create an agent responsible for initializing GitHub repositories."""
        return Agent(
            role="Repository Initializer",
            goal="Create well-structured GitHub repositories with starter code",
            backstory=(
                "You are an expert software engineer who specializes in setting up "
                "project repositories with appropriate file structures, starter code, "
                "and best practices. You understand different programming languages "
                "and can create appropriate scaffolding for various types of projects."
            ),
            verbose=True,
            allow_delegation=False,
        )
    
    async def fetch_assignment_task(
        self,
        course_id: int,
        assignment_id: Optional[int] = None
    ) -> dict:
        """
        Fetch assignment details from Canvas.
        
        Args:
            course_id: Canvas course ID
            assignment_id: Optional specific assignment ID. If not provided,
                          fetches the first upcoming assignment.
        
        Returns:
            Assignment details dictionary
        """
        if assignment_id:
            assignment = await self.canvas_tools.get_assignment_details(
                course_id, assignment_id
            )
            return assignment
        else:
            # Get all assignments and find the next upcoming one
            assignments = await self.canvas_tools.get_course_assignments(course_id)
            if not assignments:
                raise ValueError(f"No assignments found for course {course_id}")
            
            # Sort by due date and get the next upcoming assignment
            now = datetime.now()
            upcoming = []
            for a in assignments:
                if a.get("due_at"):
                    try:
                        due_date = dateutil_parser.parse(a["due_at"])
                        if due_date > now:
                            upcoming.append(a)
                    except (ValueError, TypeError):
                        # Skip assignments with invalid due dates
                        continue
            
            if upcoming:
                upcoming.sort(key=lambda x: dateutil_parser.parse(x["due_at"]))
                return upcoming[0]
            else:
                # If no upcoming assignments, return the most recent one
                assignments.sort(key=lambda x: x.get("created_at", ""), reverse=True)
                return assignments[0]
    
    async def create_repository_task(
        self,
        assignment: dict,
        language: str = "python"
    ) -> dict:
        """
        Create a GitHub repository for an assignment.
        
        Args:
            assignment: Assignment details from Canvas
            language: Programming language for the assignment
        
        Returns:
            Repository details
        """
        assignment_name = assignment.get("name", "Assignment")
        assignment_description = assignment.get("description", "")
        due_at = assignment.get("due_at", "No due date")

        # Convert HTML assignment content to Markdown for the README
        full_description = html_to_markdown(assignment_description)
        # Short plain-text version for GitHub repo description and code comments
        short_description = self.strip_html(assignment_description)[:200]
        
        # Create a slug for the repo name using shared utility
        repo_name = normalize_slug(assignment_name)
        
        # Create the repository
        print(f"\nCreating repository: {repo_name}")
        repo = await self.github_tools.create_repository(
            name=repo_name,
            description=f"{assignment_name} - Due: {due_at}"[:350],
            private=False,
            auto_init=True
        )
        
        if not repo:
            print("\n❌ Failed to create repository. Possible causes:")
            print("   - GitHub token lacks 'Administration: Read and write' permission")
            print("   - Repository name already exists")
            print("   - GITHUB_ORG is set to an invalid organization")
            print(f"\n   Attempted repo name: {repo_name}")
            print(f"   Owner: {self.github_org or self.github_username}")
            return None
        
        # Generate starter files with full assignment content in README
        starter_files = generate_starter_files(
            assignment_name=assignment_name,
            assignment_description=full_description,
            short_description=short_description,
            due_date=due_at,
            language=language
        )
        
        # Create files in the repository
        owner = self.github_org if self.github_org else self.github_username
        print(f"\nAdding starter files to repository...")
        files_ok = await self.github_tools.create_directory_structure(
            owner=owner,
            repo=repo_name,
            files=starter_files
        )
        
        if not files_ok:
            print("\n⚠️  Some files failed to upload. Check that your GitHub token")
            print("   has 'Contents: Read and write' permission.")
        
        return {
            "repository": repo,
            "assignment": assignment,
            "files_created": list(starter_files.keys()),
            "files_uploaded": files_ok
        }

    async def create_notion_page_task(self, assignment: dict) -> Optional[dict]:
        """Create a Notion page for a writing assignment."""
        assignment_name = assignment.get("name", "Assignment")
        assignment_description = self.strip_html(assignment.get("description", ""))
        due_at = assignment.get("due_at", "No due date")

        print(f"\nCreating Notion page for writing assignment: {assignment_name}")
        page = await self.notion_tools.create_assignment_page(
            title=assignment_name,
            description=assignment_description,
            due_date=due_at,
        )

        if not page:
            print("\n❌ Failed to create Notion page. Possible causes:")
            print("   - NOTION_TOKEN is missing or invalid")
            print("   - NOTION_PARENT_PAGE_ID is missing or invalid")
            return None

        return {
            "page": page,
            "assignment": assignment,
        }
    
    async def run(
        self,
        course_id: int,
        assignment_id: Optional[int] = None,
        language: str = "python",
        assignment_type: Optional[str] = None,
        confirm_assignment_type: bool = False,
        assignment_data: Optional[dict] = None,
    ):
        """
        Run the complete workflow.
        
        Args:
            course_id: Canvas course ID
            assignment_id: Optional specific assignment ID
            language: Programming language for starter code
            assignment_type: Optional explicit assignment type (coding/writing)
            confirm_assignment_type: Whether to prompt user to confirm inferred type
            assignment_data: Optional pre-fetched assignment details
        """
        print("=" * 80)
        print("Canvas-GitHub Agent")
        print("=" * 80)
        
        # Step 1: Fetch assignment from Canvas
        print(f"\n📚 Fetching assignment from Canvas (Course ID: {course_id})...")
        assignment = assignment_data or await self.fetch_assignment_task(course_id, assignment_id)
        
        if not assignment:
            print("❌ No assignment found!")
            return
        
        print(f"\n✅ Found assignment: {assignment.get('name')}")
        print(f"   Description: {assignment.get('description', 'N/A')[:100]}...")
        print(f"   Due date: {assignment.get('due_at', 'N/A')}")

        # Step 2: Determine assignment type (coding vs writing)
        if assignment_type not in {"coding", "writing"}:
            assignment_type = self.infer_assignment_type(assignment)

        if confirm_assignment_type:
            assignment_type = self.confirm_assignment_type(assignment_type)

        print(f"\n🧭 Assignment type selected: {assignment_type}")
        
        if assignment_type == "coding":
            # Step 3a: Create GitHub repository with starter code
            print(f"\n🚀 Creating GitHub repository with {language} starter code...")
            result = await self.create_repository_task(assignment, language)

            if not result or "repository" not in result:
                print("\n❌ Repository creation failed. See errors above.")
                return None

            repo_info = result["repository"]
            owner = repo_info.get("owner", {}).get("login", self.github_username)
            repo_name = repo_info.get("name", "unknown")

            if result.get("files_uploaded", False):
                print(f"\n✅ Repository created successfully!")
                print(f"   Repository: https://github.com/{owner}/{repo_name}")
                print(f"   Files created: {', '.join(result['files_created'])}")
            else:
                print(f"\n⚠️  Repository created but files failed to upload.")
                print(f"   Repository: https://github.com/{owner}/{repo_name}")
                print("   Make sure your GitHub token has 'Contents: Read and write' permission.")

            result["destination"] = "github"
        else:
            # Step 3b: Create Notion page for writing assignment
            missing_notion_config = self.validate_notion_config()
            if missing_notion_config:
                print("\n❌ Notion configuration is incomplete for writing assignments.")
                print(f"   Missing: {', '.join(missing_notion_config)}")
                print("   Set these values in your .env file and try again.")
                print(
                    "   NOTION_PARENT_PAGE_ID should be the page ID of a Notion page "
                    "shared with your integration."
                )
                return None

            print("\n📝 Creating Notion page for writing assignment...")
            result = await self.create_notion_page_task(assignment)

            if not result or "page" not in result:
                print("\n❌ Notion page creation failed. See errors above.")
                return None

            page_url = result["page"].get("url", "N/A")
            print("\n✅ Notion page created successfully!")
            print(f"   Page URL: {page_url}")
            result["destination"] = "notion"
        
        print("\n" + "=" * 80)
        if assignment_type == "coding":
            print("✨ Done! Your assignment repository is ready.")
        else:
            print("✨ Done! Your writing assignment Notion page is ready.")
        print("=" * 80)
        
        return result


async def list_courses():
    """Helper function to list available courses."""
    canvas_tools = CanvasTools()
    print("\n📚 Fetching your Canvas courses...\n")
    courses = await canvas_tools.list_courses()
    
    if not courses:
        print("No courses found. Please check your Canvas API token.")
        return
    
    print("Available courses:")
    print("-" * 80)
    for course in courses:
        print(f"ID: {course.get('id', 'N/A'):>10} | {course.get('name', 'Unknown Course')}")
    print("-" * 80)
    print(f"\nTotal: {len(courses)} courses")


async def list_course_assignments(course_id: int):
    """Helper function to list assignments for a course."""
    canvas_tools = CanvasTools()
    print(f"\n📝 Fetching assignments for course {course_id}...\n")
    assignments = await canvas_tools.get_course_assignments(course_id)
    
    if not assignments:
        print("No assignments found for this course.")
        return
    
    print("Available assignments:")
    print("-" * 80)
    for assignment in assignments:
        print(f"ID: {assignment.get('id', 'N/A'):>10} | {assignment.get('name', 'Unknown Assignment')}")
        print(f"             Due: {assignment.get('due_at', 'No due date')}")
        print("-" * 80)
    print(f"\nTotal: {len(assignments)} assignments")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description=(
            "Canvas Assignment Agent: Create GitHub repos for coding assignments "
            "or Notion pages for writing assignments"
        )
    )
    parser.add_argument(
        "command",
        choices=["list-courses", "list-assignments", "create-repo"],
        help="Command to execute"
    )
    parser.add_argument(
        "--course-id",
        type=int,
        help="Canvas course ID"
    )
    parser.add_argument(
        "--assignment-id",
        type=int,
        help="Canvas assignment ID (optional, will use next upcoming if not specified)"
    )
    parser.add_argument(
        "--language",
        default="python",
        choices=["python", "java", "javascript", "cpp"],
        help="Programming language for starter code (default: python)"
    )
    parser.add_argument(
        "--assignment-type",
        choices=["coding", "writing"],
        help="Override assignment type routing (coding or writing)"
    )
    parser.add_argument(
        "--confirm-type",
        action="store_true",
        help="Prompt to confirm inferred assignment type before creating destination"
    )
    
    args = parser.parse_args()
    
    if args.command == "list-courses":
        await list_courses()
    
    elif args.command == "list-assignments":
        if not args.course_id:
            print("Error: --course-id is required for list-assignments")
            return
        await list_course_assignments(args.course_id)
    
    elif args.command == "create-repo":
        if not args.course_id:
            print("Error: --course-id is required for create-repo")
            return
        
        agent = CanvasGitHubAgent()
        await agent.run(
            course_id=args.course_id,
            assignment_id=args.assignment_id,
            language=args.language,
            assignment_type=args.assignment_type,
            confirm_assignment_type=args.confirm_type,
        )


if __name__ == "__main__":
    asyncio.run(main())
