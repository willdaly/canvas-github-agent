#!/usr/bin/env python3
"""
Simple CLI wrapper for Canvas Assignment Agent
Creates GitHub repositories for coding assignments and Notion pages for writing assignments.
"""
import sys
import asyncio
from app.agent import CanvasGitHubAgent, list_courses, list_course_assignments


async def interactive_mode():
    """Run in interactive mode with prompts."""
    print("=" * 80)
    print("Canvas Assignment Agent - Interactive Mode")
    print("=" * 80)
    print("\nThis tool creates a GitHub repo (coding) or Notion page (writing) from Canvas assignments.\n")
    
    # List courses
    print("Fetching your Canvas courses...\n")
    await list_courses()
    
    # Get course selection
    while True:
        course_input = input("\nEnter course ID (or 'q' to quit): ").strip()
        if course_input.lower() == 'q':
            print("Goodbye!")
            return
        if course_input.isdigit():
            course_id = int(course_input)
            break
        print("❌ Please enter a valid course ID number")
    
    # List assignments
    print(f"\nFetching assignments for course {course_id}...\n")
    await list_course_assignments(course_id)
    
    # Get assignment selection (optional)
    assignment_input = input(
        "\nEnter assignment ID (or press Enter for next upcoming): "
    ).strip()
    assignment_id = int(assignment_input) if assignment_input.isdigit() else None
    
    # Get language preference
    print("\nAvailable languages:")
    print("  1. Python (default)")
    print("  2. R")
    
    lang_input = input("\nSelect language (1-2 or press Enter for Python): ").strip()
    language_map = {
        "1": "python",
        "2": "r",
        "": "python"
    }
    language = language_map.get(lang_input, "python")
    
    # Pre-fetch assignment for type inference and confirmation
    agent = CanvasGitHubAgent()
    assignment = await agent.fetch_assignment(course_id, assignment_id)
    inferred_type = agent.infer_assignment_type(assignment)

    print(f"\nDetected assignment: {assignment.get('name', 'Unknown')}")
    print(f"Inferred assignment type: {inferred_type}")

    while True:
        assignment_type_input = input(
            "Confirm assignment type ([c]oding/[w]riting, Enter to accept inferred): "
        ).strip().lower()
        if assignment_type_input == "":
            assignment_type = inferred_type
            break
        if assignment_type_input in {"c", "coding"}:
            assignment_type = "coding"
            break
        if assignment_type_input in {"w", "writing"}:
            assignment_type = "writing"
            break
        print("❌ Please enter 'c', 'w', 'coding', 'writing', or press Enter.")

    # Confirm
    print("\n" + "=" * 80)
    print("Ready to process assignment:")
    print(f"  Course ID: {course_id}")
    print(f"  Assignment ID: {assignment_id if assignment_id else 'Next upcoming'}")
    print(f"  Assignment Type: {assignment_type}")
    if assignment_type == "coding":
        print(f"  Language: {language}")
    print("=" * 80)
    
    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    # Process assignment (GitHub repo for coding, Notion page for writing)
    print("\n")
    await agent.run(
        course_id=course_id,
        assignment_id=assignment_id,
        language=language,
        assignment_type=assignment_type,
        assignment_data=assignment,
    )


def print_usage():
    """Print usage information."""
    print("""
Canvas Assignment Agent - Quick Start

Usage:
    canvas-github-agent-cli                    Run in interactive mode
    canvas-github-agent-cli --help             Show this help message

Advanced command-line mode:
    canvas-github-agent list-courses
    canvas-github-agent list-assignments --course-id 12345
    canvas-github-agent create-repo --course-id 12345 --language python
    canvas-github-agent create-repo --course-id 12345 --confirm-type
  
For more information, see README.md
""")


def run() -> None:
    """Synchronous entry point for installed console scripts."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h", "help"]:
        print_usage()
        return

    try:
        asyncio.run(interactive_mode())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as error:
        print(f"\n❌ Error: {error}")
        print("\nMake sure you have:")
        print("  1. Created a .env file with your API tokens")
        print("  2. Installed dependencies: pip install -r requirements.txt")
        print("\nFor more help, run: canvas-github-agent-cli --help")


if __name__ == "__main__":
    run()
