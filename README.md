# Canvas-GitHub Agent

A CrewAI-powered agent that automatically fetches assignments from Canvas LMS using [canvas-mcp](https://smithery.ai/servers/aryankeluskar/canvas-mcp) and creates GitHub repositories with helpful file structure and starter code using GitHub MCP.

## Features

- 🎓 **Canvas Integration**: Fetch assignments directly from your Canvas LMS courses
- 🚀 **Automated Repository Creation**: Create GitHub repositories with one command
- 📁 **Smart Starter Code**: Generate language-specific project scaffolding
- 🔧 **Multiple Languages**: Support for Python, Java, JavaScript, and C++
- 📝 **README Generation**: Auto-generate README with assignment details and due dates
- ✅ **Test Setup**: Include basic test structure and configuration

## Prerequisites

- Python 3.10 or higher
- Node.js (for GitHub MCP server)
- Canvas LMS API token
- GitHub Personal Access Token

## Installation

1. Clone the repository:
```bash
git clone https://github.com/willdaly/canvas-github-agent.git
cd canvas-github-agent
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
- `CANVAS_API_URL`: Your Canvas instance URL (e.g., https://canvas.instructure.com)
- `CANVAS_API_TOKEN`: Your Canvas API token
- `GITHUB_TOKEN`: Your GitHub Personal Access Token
- `GITHUB_USERNAME`: Your GitHub username
- `OPENAI_API_KEY`: Your OpenAI API key (for CrewAI)

### Getting Canvas API Token

1. Log into your Canvas account
2. Go to Account → Settings
3. Scroll down to "Approved Integrations"
4. Click "+ New Access Token"
5. Give it a purpose and generate the token
6. Copy the token to your `.env` file

### Getting GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select scopes: `repo`, `workflow`
4. Copy the token to your `.env` file

## Usage

### Interactive Mode (Easiest)

For the simplest experience, use the interactive CLI:

```bash
python cli.py
```

This will guide you through:
1. Selecting a course
2. Choosing an assignment
3. Picking a programming language
4. Creating the repository

### Command-Line Mode

### List Your Canvas Courses

```bash
python main.py list-courses
```

This will display all your Canvas courses with their IDs.

### List Assignments for a Course

```bash
python main.py list-assignments --course-id 12345
```

Replace `12345` with your actual course ID.

### Create a Repository for an Assignment

Create a repository for the next upcoming assignment:

```bash
python main.py create-repo --course-id 12345
```

Create a repository for a specific assignment:

```bash
python main.py create-repo --course-id 12345 --assignment-id 67890
```

Specify the programming language:

```bash
python main.py create-repo --course-id 12345 --language python
```

Available languages:
- `python` (default)
- `java`
- `javascript`
- `cpp`

## Generated Repository Structure

### Python Projects
```
assignment-name/
├── README.md           # Assignment details and instructions
├── requirements.txt    # Python dependencies
├── main.py            # Main implementation file
├── tests/
│   └── test_main.py   # Test file
└── .gitignore         # Python-specific gitignore
```

### Java Projects
```
assignment-name/
├── README.md          # Assignment details and instructions
├── Main.java         # Main implementation file
├── Test.java         # Test file
└── .gitignore        # Java-specific gitignore
```

### JavaScript Projects
```
assignment-name/
├── README.md          # Assignment details and instructions
├── package.json       # Node.js dependencies and scripts
├── index.js          # Main implementation file
├── index.test.js     # Test file
└── .gitignore        # Node-specific gitignore
```

### C++ Projects
```
assignment-name/
├── README.md          # Assignment details and instructions
├── main.cpp          # Main implementation file
├── test.cpp          # Test file
└── .gitignore        # C++-specific gitignore
```

## How It Works

1. **Canvas Integration**: The agent connects to Canvas LMS using the canvas-mcp server to fetch assignment details including name, description, and due date.

2. **Repository Creation**: Using GitHub MCP, it creates a new repository in your GitHub account with the assignment name.

3. **Starter Code Generation**: Based on the programming language specified, it generates appropriate starter files including:
   - README with assignment details
   - Main source file with TODO comments
   - Test files with basic structure
   - Configuration files (requirements.txt, package.json, etc.)
   - Language-specific .gitignore

4. **File Upload**: All generated files are committed to the repository with appropriate commit messages.

## Architecture

The project uses:
- **CrewAI**: For agent orchestration and task management
- **Canvas MCP**: For Canvas LMS integration via Model Context Protocol
- **GitHub MCP**: For GitHub operations via Model Context Protocol
- **Templates**: Language-specific starter code templates

## Troubleshooting

### Canvas API Issues

If you get authentication errors:
- Verify your Canvas API token is correct
- Check that your Canvas URL is correct (include https://)
- Ensure your token has not expired

### GitHub API Issues

If repository creation fails:
- Verify your GitHub token has `repo` scope
- Check that the repository name doesn't already exist
- Ensure you have permission to create repositories

### MCP Server Issues

If Canvas MCP fails:
- Verify your Canvas API token is valid
- Check that your Canvas URL is correct in `.env`
- The Canvas MCP server is hosted remotely via [Smithery](https://smithery.ai/servers/aryankeluskar/canvas-mcp) — check its status page for outages

If GitHub MCP fails:
- Ensure Node.js is installed (`node --version`)
- Try running `npx -y @modelcontextprotocol/server-github` manually to test

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [canvas-mcp](https://smithery.ai/servers/aryankeluskar/canvas-mcp) for Canvas LMS integration via Smithery
- [CrewAI](https://github.com/joaomdmoura/crewAI) for agent framework
- Model Context Protocol (MCP) for standardized tool integration