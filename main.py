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
from templates import generate_starter_files, normalize_slug


# Load environment variables
load_dotenv()


class CanvasGitHubAgent:
    """Main agent class for Canvas-GitHub integration."""
    
    def __init__(self):
        self.canvas_tools = CanvasTools()
        self.github_tools = GitHubTools()
        self.github_username = os.getenv("GITHUB_USERNAME")
        _org = os.getenv("GITHUB_ORG", "").strip()
        self.github_org = _org if _org and not _org.startswith("#") else ""
        
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
        
        # Clean up the description (remove HTML tags if present)
        clean_description = re.sub(r'<[^>]+>', '', assignment_description)
        clean_description = clean_description.strip()[:200]  # Limit length
        
        # Create a slug for the repo name using shared utility
        repo_name = normalize_slug(assignment_name)
        
        # Create the repository
        print(f"\nCreating repository: {repo_name}")
        repo = await self.github_tools.create_repository(
            name=repo_name,
            description=f"{assignment_name} - Due: {due_at}",
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
        
        # Generate starter files
        starter_files = generate_starter_files(
            assignment_name=assignment_name,
            assignment_description=clean_description,
            due_date=due_at,
            language=language
        )
        
        # Create files in the repository
        owner = self.github_org if self.github_org else self.github_username
        print(f"\nAdding starter files to repository...")
        await self.github_tools.create_directory_structure(
            owner=owner,
            repo=repo_name,
            files=starter_files
        )
        
        return {
            "repository": repo,
            "assignment": assignment,
            "files_created": list(starter_files.keys())
        }
    
    async def run(
        self,
        course_id: int,
        assignment_id: Optional[int] = None,
        language: str = "python"
    ):
        """
        Run the complete workflow.
        
        Args:
            course_id: Canvas course ID
            assignment_id: Optional specific assignment ID
            language: Programming language for starter code
        """
        print("=" * 80)
        print("Canvas-GitHub Agent")
        print("=" * 80)
        
        # Step 1: Fetch assignment from Canvas
        print(f"\n📚 Fetching assignment from Canvas (Course ID: {course_id})...")
        assignment = await self.fetch_assignment_task(course_id, assignment_id)
        
        if not assignment:
            print("❌ No assignment found!")
            return
        
        print(f"\n✅ Found assignment: {assignment.get('name')}")
        print(f"   Description: {assignment.get('description', 'N/A')[:100]}...")
        print(f"   Due date: {assignment.get('due_at', 'N/A')}")
        
        # Step 2: Create GitHub repository with starter code
        print(f"\n🚀 Creating GitHub repository with {language} starter code...")
        result = await self.create_repository_task(assignment, language)
        
        if not result or "repository" not in result:
            print("\n❌ Repository creation failed. See errors above.")
            return None
        
        repo_info = result["repository"]
        owner = repo_info.get("owner", {}).get("login", self.github_username)
        repo_name = repo_info.get("name", "unknown")
        
        print(f"\n✅ Repository created successfully!")
        print(f"   Repository: https://github.com/{owner}/{repo_name}")
        print(f"   Files created: {', '.join(result['files_created'])}")
        
        print("\n" + "=" * 80)
        print("✨ Done! Your assignment repository is ready.")
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
        description="Canvas-GitHub Agent: Create GitHub repos from Canvas assignments"
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
            language=args.language
        )


if __name__ == "__main__":
    asyncio.run(main())
