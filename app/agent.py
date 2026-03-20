"""Deterministic workflow orchestrator for Canvas assignment routing."""

import asyncio
import os
import re
from datetime import datetime
from typing import Any, Optional, Sequence

from dateutil import parser as dateutil_parser
from dotenv import load_dotenv

from scaffolding.templates import generate_starter_files, html_to_markdown, normalize_slug
from tools.canvas_tools import CanvasTools
from tools.course_context_tools import CourseContextTools
from tools.github_tools import GitHubTools
from tools.notion_tools import NotionTools


load_dotenv()


def infer_assignment_type_from_text(name: str, description: str) -> str:
    """Infer whether an assignment is coding- or writing-oriented."""
    text = f"{name} {description}".lower()

    coding_keywords = {
        "code", "coding", "program", "programming", "algorithm", "implement",
        "function", "class", "method", "script", "compile", "run", "test",
        "pytest", "python", "rscript", "tidyverse", "ggplot2", "repository",
        "github", "git", "api", "software", "debug", "build",
    }
    writing_keywords = {
        "essay", "paper", "reflection", "journal", "discussion", "thesis",
        "annotated bibliography", "literature review", "report", "summary",
        "argument", "draft", "citation", "mla", "apa", "writing", "paragraph",
    }

    coding_score = sum(1 for keyword in coding_keywords if keyword in text)
    writing_score = sum(1 for keyword in writing_keywords if keyword in text)

    return "coding" if coding_score >= writing_score else "writing"


def choose_next_assignment(assignments: Sequence[dict], now: Optional[datetime] = None) -> dict:
    """Select next upcoming assignment; fallback to most recently created."""
    if not assignments:
        raise ValueError("No assignments found")

    reference_time = now or datetime.now()
    upcoming: list[dict] = []

    for assignment in assignments:
        due_at = assignment.get("due_at")
        if not due_at:
            continue
        try:
            due_date = dateutil_parser.parse(due_at)
        except (ValueError, TypeError):
            continue
        if due_date > reference_time:
            upcoming.append(assignment)

    if upcoming:
        upcoming.sort(key=lambda item: dateutil_parser.parse(item["due_at"]))
        return upcoming[0]

    return sorted(assignments, key=lambda item: item.get("created_at", ""), reverse=True)[0]


def get_missing_notion_config(env: Optional[dict] = None) -> list[str]:
    """Return missing Notion environment variables required for writing flow."""
    environment = env or os.environ
    missing = []
    if not environment.get("NOTION_TOKEN", "").strip():
        missing.append("NOTION_TOKEN")
    if not environment.get("NOTION_PARENT_PAGE_ID", "").strip():
        missing.append("NOTION_PARENT_PAGE_ID")
    return missing


class CanvasGitHubAgent:
    """Workflow orchestrator for Canvas assignments to GitHub/Notion destinations."""

    def __init__(self):
        self.canvas_tools = CanvasTools()
        self.course_context_tools = CourseContextTools()
        self.github_tools = GitHubTools()
        self.notion_tools = NotionTools()
        self.github_username = os.getenv("GITHUB_USERNAME")
        _org = os.getenv("GITHUB_ORG", "").strip()
        self.github_org = _org if _org and not _org.startswith("#") else ""

    @staticmethod
    def format_course_context(course_context: Sequence[dict], max_items: int = 3) -> str:
        """Format retrieved course context into a compact human-readable block."""
        if not course_context:
            return ""

        lines = ["Relevant course context:"]
        for item in list(course_context)[:max_items]:
            title = item.get("section_title") or item.get("document_name") or "Course reference"
            lines.append(f"- {title}: {item.get('text', '').strip()[:350]}")
        return "\n".join(lines)

    @staticmethod
    def strip_html(text: str) -> str:
        """Remove HTML tags from assignment text."""
        if not text:
            return ""
        return re.sub(r"<[^>]+>", "", text).strip()

    def infer_assignment_type(self, assignment: dict) -> str:
        """Infer whether an assignment is coding or writing based on content."""
        assignment_name = assignment.get("name", "")
        assignment_description = self.strip_html(assignment.get("description", ""))
        return infer_assignment_type_from_text(assignment_name, assignment_description)

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
        return get_missing_notion_config()

    async def fetch_assignment(self, course_id: int, assignment_id: Optional[int] = None) -> dict:
        """Fetch assignment details from Canvas."""
        if assignment_id:
            return await self.canvas_tools.get_assignment_details(course_id, assignment_id)

        assignments = await self.canvas_tools.get_course_assignments(course_id)
        try:
            return choose_next_assignment(assignments)
        except ValueError as error:
            raise ValueError(f"No assignments found for course {course_id}") from error

    async def create_repository_for_assignment(
        self,
        assignment: dict,
        language: str = "python",
        course_context: Optional[Sequence[dict]] = None,
    ) -> Optional[dict]:
        """Create a GitHub repository with assignment starter files."""
        assignment_name = assignment.get("name", "Assignment")
        assignment_description = assignment.get("description", "")
        due_at = assignment.get("due_at", "No due date")

        full_description = html_to_markdown(assignment_description)
        short_description = self.strip_html(assignment_description)[:200]
        repo_name = normalize_slug(assignment_name)

        print(f"\nCreating repository: {repo_name}")
        repo = await self.github_tools.create_repository(
            name=repo_name,
            description=f"{assignment_name} - Due: {due_at}"[:350],
            private=False,
            auto_init=True,
        )

        if not repo:
            print("\n❌ Failed to create repository. Possible causes:")
            print("   - GitHub token lacks 'Administration: Read and write' permission")
            print("   - Repository name already exists")
            print("   - GITHUB_ORG is set to an invalid organization")
            print(f"\n   Attempted repo name: {repo_name}")
            print(f"   Owner: {self.github_org or self.github_username}")
            return None

        starter_files = generate_starter_files(
            assignment_name=assignment_name,
            assignment_description=full_description,
            short_description=short_description,
            due_date=due_at,
            language=language,
            course_context=list(course_context or []),
        )

        owner = self.github_org if self.github_org else self.github_username
        print("\nAdding starter files to repository...")
        files_ok = await self.github_tools.create_directory_structure(
            owner=owner,
            repo=repo_name,
            files=starter_files,
        )

        if not files_ok:
            print("\n⚠️  Some files failed to upload. Check that your GitHub token")
            print("   has 'Contents: Read and write' permission.")

        return {
            "repository": repo,
            "assignment": assignment,
            "course_context": list(course_context or []),
            "files_created": list(starter_files.keys()),
            "files_uploaded": files_ok,
        }

    async def create_notion_page_for_assignment(self, assignment: dict) -> Optional[dict]:
        """Create a Notion page for a writing assignment."""
        return await self.create_notion_page_for_assignment_with_mode(assignment, content_mode="structured")

    async def create_notion_page_for_assignment_with_mode(
        self,
        assignment: dict,
        content_mode: str = "structured",
        course_context: Optional[Sequence[dict]] = None,
    ) -> Optional[dict]:
        """Create a Notion page for a writing assignment with a chosen content mode."""
        assignment_name = assignment.get("name", "Assignment")
        assignment_description = self.strip_html(assignment.get("description", ""))
        context_block = self.format_course_context(course_context or [])
        if context_block:
            assignment_description = f"{assignment_description}\n\n{context_block}".strip()
        due_at = assignment.get("due_at", "No due date")

        print(f"\nCreating Notion page for writing assignment: {assignment_name}")
        page = await self.notion_tools.create_assignment_page(
            title=assignment_name,
            description=assignment_description,
            due_date=due_at,
            content_mode=content_mode,
        )

        if not page:
            print("\n❌ Failed to create Notion page. Possible causes:")
            print("   - NOTION_TOKEN is missing or invalid")
            print("   - NOTION_PARENT_PAGE_ID is missing or invalid")
            return None

        return {"page": page, "assignment": assignment, "course_context": list(course_context or [])}

    async def fetch_course_context(self, course_id: int, assignment: dict, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve relevant course-document chunks for the given assignment."""
        assignment_name = assignment.get("name", "").strip()
        assignment_description = self.strip_html(assignment.get("description", ""))
        query = "\n\n".join(part for part in [assignment_name, assignment_description] if part).strip()
        if not query:
            return []

        try:
            results = await asyncio.to_thread(
                self.course_context_tools.search_context,
                course_id,
                query,
                limit,
            )
        except RuntimeError as error:
            print(f"\n⚠️  Course context search skipped: {error}")
            return []
        except Exception as error:
            print(f"\n⚠️  Course context search failed: {error}")
            return []

        if results:
            print(f"\n📎 Retrieved {len(results)} course context matches from your course documents.")
        return results

    async def run(
        self,
        course_id: int,
        assignment_id: Optional[int] = None,
        language: str = "python",
        assignment_type: Optional[str] = None,
        notion_content_mode: Optional[str] = None,
        confirm_assignment_type: bool = False,
        assignment_data: Optional[dict] = None,
    ):
        """Run the sequential assignment routing workflow."""
        print("=" * 80)
        print("Canvas Assignment Workflow")
        print("=" * 80)

        print(f"\n📚 Fetching assignment from Canvas (Course ID: {course_id})...")
        assignment = assignment_data or await self.fetch_assignment(course_id, assignment_id)

        if not assignment:
            print("❌ No assignment found!")
            return None

        print(f"\n✅ Found assignment: {assignment.get('name')}")
        print(f"   Description: {assignment.get('description', 'N/A')[:100]}...")
        print(f"   Due date: {assignment.get('due_at', 'N/A')}")
        course_context = await self.fetch_course_context(course_id, assignment)

        if assignment_type not in {"coding", "writing"}:
            assignment_type = self.infer_assignment_type(assignment)

        if confirm_assignment_type:
            assignment_type = self.confirm_assignment_type(assignment_type)

        print(f"\n🧭 Assignment type selected: {assignment_type}")

        if assignment_type == "coding":
            print(f"\n🚀 Creating GitHub repository with {language} starter code...")
            result = await self.create_repository_for_assignment(
                assignment,
                language,
                course_context=course_context,
            )

            if not result or "repository" not in result:
                print("\n❌ Repository creation failed. See errors above.")
                return None

            repo_info = result["repository"]
            owner = repo_info.get("owner", {}).get("login", self.github_username)
            repo_name = repo_info.get("name", "unknown")

            if result.get("files_uploaded", False):
                print("\n✅ Repository created successfully!")
                print(f"   Repository: https://github.com/{owner}/{repo_name}")
                print(f"   Files created: {', '.join(result['files_created'])}")
            else:
                print("\n⚠️  Repository created but files failed to upload.")
                print(f"   Repository: https://github.com/{owner}/{repo_name}")
                print("   Make sure your GitHub token has 'Contents: Read and write' permission.")

            result["destination"] = "github"
        else:
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
            notion_content_mode = notion_content_mode or "structured"
            result = await self.create_notion_page_for_assignment_with_mode(
                assignment,
                content_mode=notion_content_mode,
                course_context=course_context,
            )

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

        if result is not None:
            result["course_context"] = course_context

        return result


async def ingest_course_pdf(course_id: int, file_path: str, document_name: Optional[str] = None):
    """Ingest a course PDF into the local Chroma-backed course context store."""
    tools = CourseContextTools()
    result = await asyncio.to_thread(tools.ingest_pdf, course_id, file_path, document_name)
    print("\n✅ Course document ingested successfully!")
    print(f"   Course ID: {result['course_id']}")
    print(f"   Document: {result['document_name']}")
    print(f"   Chunks indexed: {result['chunk_count']}")
    print(f"   Collection: {result['collection']}")


async def search_course_context(course_id: int, query: str, limit: int = 5):
    """Search ingested course context for an assignment-like query."""
    tools = CourseContextTools()
    results = await asyncio.to_thread(tools.search_context, course_id, query, limit)

    print(f"\n🔎 Retrieved {len(results)} course context matches")
    print("-" * 80)
    for index, item in enumerate(results, start=1):
        print(f"{index}. {item.get('section_title') or item.get('document_name') or 'Match'}")
        print(f"   Source: {item.get('document_name', 'Unknown document')}")
        if item.get("distance") is not None:
            print(f"   Distance: {item['distance']:.4f}")
        print(f"   {item.get('text', '')[:400]}\n")


async def list_course_documents(course_id: int):
    """List PDFs already indexed for a course."""
    tools = CourseContextTools()
    documents = await asyncio.to_thread(tools.list_documents, course_id)

    print(f"\n📚 Indexed course documents for course {course_id}")
    print("-" * 80)
    for document in documents:
        print(
            f"{document['document_name']} | chunks={document['chunk_count']} | "
            f"source={document.get('source_path', 'N/A')}"
        )


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
            "Canvas Assignment Workflow: create GitHub repos for coding assignments "
            "or Notion pages for writing assignments"
        )
    )
    parser.add_argument(
        "command",
        choices=[
            "list-courses",
            "list-assignments",
            "create-repo",
            "ingest-pdf",
            "list-documents",
            "search-context",
        ],
        help="Command to execute",
    )
    parser.add_argument("--course-id", type=int, help="Canvas course ID")
    parser.add_argument(
        "--assignment-id",
        type=int,
        help="Canvas assignment ID (optional, will use next upcoming if not specified)",
    )
    parser.add_argument(
        "--language",
        default="python",
        choices=["python", "r"],
        help="Programming language for starter code (default: python)",
    )
    parser.add_argument(
        "--assignment-type",
        choices=["coding", "writing"],
        help="Override assignment type routing (coding or writing)",
    )
    parser.add_argument(
        "--confirm-type",
        action="store_true",
        help="Prompt to confirm inferred assignment type before creating destination",
    )
    parser.add_argument("--file-path", help="Path to a course PDF to ingest into Chroma")
    parser.add_argument("--document-name", help="Optional display name for the ingested course PDF")
    parser.add_argument("--query", help="Query text for course context search")
    parser.add_argument("--limit", type=int, default=5, help="Maximum number of search results to return")

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
    elif args.command == "ingest-pdf":
        if not args.course_id or not args.file_path:
            print("Error: --course-id and --file-path are required for ingest-pdf")
            return
        await ingest_course_pdf(args.course_id, args.file_path, args.document_name)
    elif args.command == "list-documents":
        if not args.course_id:
            print("Error: --course-id is required for list-documents")
            return
        await list_course_documents(args.course_id)
    elif args.command == "search-context":
        if not args.course_id or not args.query:
            print("Error: --course-id and --query are required for search-context")
            return
        await search_course_context(args.course_id, args.query, args.limit)


def run() -> None:
    """Synchronous entry point for installed console scripts."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
