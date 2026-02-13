"""
Example usage of Canvas-GitHub Agent

This script demonstrates how to use the CanvasGitHubAgent programmatically.
"""
import asyncio
from main import CanvasGitHubAgent, list_courses, list_course_assignments


async def example_workflow():
    """
    Example workflow showing how to use the agent.
    """
    print("Canvas-GitHub Agent - Example Workflow")
    print("=" * 80)
    
    # Step 1: List your courses
    print("\nStep 1: List your Canvas courses")
    print("-" * 80)
    await list_courses()
    
    # Step 2: Get course ID from user
    print("\n\nStep 2: Select a course")
    print("-" * 80)
    course_id = input("Enter a course ID from the list above: ")
    
    if not course_id.isdigit():
        print("Invalid course ID. Exiting.")
        return
    
    course_id = int(course_id)
    
    # Step 3: List assignments for the course
    print(f"\n\nStep 3: List assignments for course {course_id}")
    print("-" * 80)
    await list_course_assignments(course_id)
    
    # Step 4: Ask user if they want to create a repo
    print("\n\nStep 4: Create repository")
    print("-" * 80)
    create = input("Do you want to create a repository for an assignment? (y/n): ")
    
    if create.lower() != 'y':
        print("Exiting without creating repository.")
        return
    
    # Step 5: Get assignment ID (optional)
    assignment_id_input = input(
        "Enter assignment ID (or press Enter to use next upcoming assignment): "
    )
    assignment_id = int(assignment_id_input) if assignment_id_input.isdigit() else None
    
    # Step 6: Get language preference
    print("\nAvailable languages: python, java, javascript, cpp")
    language = input("Enter programming language (default: python): ").strip().lower()
    if not language or language not in ["python", "java", "javascript", "cpp"]:
        language = "python"
    
    # Step 7: Create the repository
    print(f"\n\nStep 5: Creating repository with {language} starter code")
    print("-" * 80)
    
    agent = CanvasGitHubAgent()
    result = await agent.run(
        course_id=course_id,
        assignment_id=assignment_id,
        language=language
    )
    
    if result:
        print("\n✅ Success! Repository created and ready to use.")
        print("\nNext steps:")
        print("1. Clone the repository")
        print("2. Complete the assignment")
        print("3. Commit and push your changes")
        print("4. Submit the repository link to Canvas")


async def quick_create_example():
    """
    Quick example: Create a repository directly if you know the course and assignment IDs.
    
    NOTE: Replace the values below with your actual Canvas course and assignment IDs
    before running this function.
    """
    # TODO: Replace these with your actual IDs from Canvas
    COURSE_ID = 12345  # Replace with your Canvas course ID (e.g., from list-courses)
    ASSIGNMENT_ID = 67890  # Replace with Canvas assignment ID, or set to None for next upcoming
    LANGUAGE = "python"  # Choose: python, java, javascript, or cpp
    
    print("Quick Create Example")
    print("=" * 80)
    print(f"Creating repository for course {COURSE_ID}")
    print("\nNOTE: Make sure to update COURSE_ID and ASSIGNMENT_ID with real values!")
    
    agent = CanvasGitHubAgent()
    result = await agent.run(
        course_id=COURSE_ID,
        assignment_id=ASSIGNMENT_ID,
        language=LANGUAGE
    )
    
    return result


if __name__ == "__main__":
    # Run the interactive example workflow
    asyncio.run(example_workflow())
    
    # To run the quick create example instead, uncomment the line below:
    # asyncio.run(quick_create_example())
