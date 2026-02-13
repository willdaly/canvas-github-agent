#!/usr/bin/env python3
"""
Simple CLI wrapper for Canvas-GitHub Agent
Makes it easy to quickly create repos without remembering command syntax
"""
import sys
import asyncio
from main import CanvasGitHubAgent, list_courses, list_course_assignments


async def interactive_mode():
    """Run in interactive mode with prompts."""
    print("=" * 80)
    print("Canvas-GitHub Agent - Interactive Mode")
    print("=" * 80)
    print("\nThis tool helps you create GitHub repositories from Canvas assignments.\n")
    
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
    print("  2. Java")
    print("  3. JavaScript")
    print("  4. C++")
    
    lang_input = input("\nSelect language (1-4 or press Enter for Python): ").strip()
    language_map = {
        "1": "python",
        "2": "java",
        "3": "javascript",
        "4": "cpp",
        "": "python"
    }
    language = language_map.get(lang_input, "python")
    
    # Confirm
    print("\n" + "=" * 80)
    print("Ready to create repository:")
    print(f"  Course ID: {course_id}")
    print(f"  Assignment ID: {assignment_id if assignment_id else 'Next upcoming'}")
    print(f"  Language: {language}")
    print("=" * 80)
    
    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        return
    
    # Create repository
    agent = CanvasGitHubAgent()
    print("\n")
    await agent.run(course_id=course_id, assignment_id=assignment_id, language=language)


def print_usage():
    """Print usage information."""
    print("""
Canvas-GitHub Agent - Quick Start

Usage:
  python cli.py                              Run in interactive mode
  python cli.py --help                       Show this help message
  
See main.py for advanced command-line options:
  python main.py list-courses                List all your Canvas courses
  python main.py list-assignments --course-id 12345
  python main.py create-repo --course-id 12345 --language python
  
For more information, see README.md
""")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h", "help"]:
        print_usage()
    else:
        try:
            asyncio.run(interactive_mode())
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Goodbye!")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\nMake sure you have:")
            print("  1. Created a .env file with your API tokens")
            print("  2. Installed dependencies: pip install -r requirements.txt")
            print("\nFor more help, run: python cli.py --help")
