# Canvas Assignment Agent

A CrewAI-powered agent that automatically fetches assignments from Canvas LMS using [canvas-mcp](https://smithery.ai/servers/aryankeluskar/canvas-mcp), then routes to GitHub or Notion based on assignment type.

## Features

- 🎓 **Canvas Integration**: Fetch assignments directly from your Canvas LMS courses
- 🧭 **Smart Assignment Routing**: Detect coding vs writing assignments from assignment text
- 🚀 **Automated Repository Creation**: Create GitHub repositories for coding assignments
- 📝 **Notion Integration**: Create Notion pages for writing assignments
- 📁 **Smart Starter Code**: Generate language-specific project scaffolding
- 🔧 **Multiple Languages**: Support for Python, Java, JavaScript, and C++
- 📝 **README Generation**: Auto-generate README with assignment details and due dates
- ✅ **Test Setup**: Include basic test structure and configuration

## Prerequisites

- Python 3.10 or higher
- Node.js 20 or higher (for MCP/Smithery tooling)
- Canvas LMS API token
- GitHub Personal Access Token

## Installation

1. Clone the repository:

```bash
git clone https://github.com/willdaly/canvas-github-agent.git
cd canvas-github-agent
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Configure environment variables:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

- `CANVAS_API_URL`: Your Canvas instance URL, for example your hosted Canvas domain
- `CANVAS_API_TOKEN`: Your Canvas API token
- `CANVAS_USE_MCP`: Set to `false` to bypass Canvas MCP and call Canvas REST API directly (recommended for headless server deployments)
- `GITHUB_TOKEN`: Your GitHub Personal Access Token
- `GITHUB_USERNAME`: Your GitHub username
- `NOTION_TOKEN`: Your Notion integration token (required for writing assignment routing)
- `NOTION_PARENT_PAGE_ID`: Parent page ID where writing assignment pages are created
- `OPENAI_API_KEY`: Your OpenAI API key (for CrewAI)

### Deployment Reliability Note

In remote VM deployments, browser OAuth callbacks for Canvas MCP can be brittle.
If you want a non-interactive setup, set:

```env
CANVAS_USE_MCP=false
```

When disabled, the app reads courses and assignments directly from Canvas REST using `CANVAS_API_URL` and `CANVAS_API_TOKEN`.

### Getting Canvas API Token

1. Log into your Canvas account.
1. Go to Account → Settings.
1. Scroll down to "Approved Integrations."
1. Click "+ New Access Token."
1. Give it a purpose and generate the token.
1. Copy the token to your `.env` file.

### Getting GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens.
1. Generate a new token (classic).
1. Select scopes: `repo`, `workflow`.
1. Copy the token to your `.env` file.

## Project Structure

```text
canvas-github-agent/
├── LICENSE              # Project license
├── README.md            # Project documentation
├── app/                  # Core agent workflows, reasoning, and CLI
├── examples/             # Example scripts and usage flows
├── requirements.txt      # Runtime dependency list
├── scaffolding/          # Starter-file generation and templates
├── tests/                # Test suite
├── tools/                # Canvas, GitHub, and Notion integrations
└── pyproject.toml        # Packaging and tool configuration
```

Inside `app/`, the main workflow now lives in `agent.py` and the interactive
CLI lives in `cli.py`.

The application logic lives under `app/`, integrations live under `tools/`, and
project scaffolding lives under `scaffolding/`.

## Install And Run

If you want the packaged commands available in your shell, install the project in editable mode:

```bash
pip install -e .
```

That provides these commands:

- `canvas-github-agent-cli` for the interactive workflow
- `canvas-github-agent` for direct command-line operations

You can then run:

```bash
canvas-github-agent-cli
canvas-github-agent --help
```

## Usage

### Interactive Mode (Easiest)

For the simplest experience, use the interactive CLI:

```bash
canvas-github-agent-cli
```

This will guide you through:

1. Selecting a course
2. Choosing an assignment
3. Picking a programming language
4. Confirming assignment type (coding/writing)
5. Creating a GitHub repo (coding) or Notion page (writing)

### Command-Line Mode

### List Your Canvas Courses

```bash
canvas-github-agent list-courses
```

This will display all your Canvas courses with their IDs.

### List Assignments for a Course

```bash
canvas-github-agent list-assignments --course-id 12345
```

Replace `12345` with your actual course ID.

### Create a Destination for an Assignment

Create a destination for the next upcoming assignment:

```bash
canvas-github-agent create-repo --course-id 12345
```

Create a destination for a specific assignment:

```bash
canvas-github-agent create-repo --course-id 12345 --assignment-id 67890
```

Specify the programming language:

```bash
canvas-github-agent create-repo --course-id 12345 --language python
```

Available languages:

- `python` (default)
- `java`
- `javascript`
- `cpp`

Override routing explicitly:

```bash
canvas-github-agent create-repo --course-id 12345 --assignment-type writing
```

Prompt to confirm inferred assignment type before creating destination:

```bash
canvas-github-agent create-repo --course-id 12345 --confirm-type
```

## Generated Repository Structure

### Python Projects

```text
assignment-name/
├── README.md           # Assignment details and instructions
├── requirements.txt    # Python dependencies
├── main.py            # Main implementation file
├── tests/
│   └── test_main.py   # Test file
└── .gitignore         # Python-specific gitignore
```

### Java Projects

```text
assignment-name/
├── README.md          # Assignment details and instructions
├── Main.java         # Main implementation file
├── Test.java         # Test file
└── .gitignore        # Java-specific gitignore
```

### JavaScript Projects

```text
assignment-name/
├── README.md          # Assignment details and instructions
├── package.json       # Node.js dependencies and scripts
├── index.js          # Main implementation file
├── index.test.js     # Test file
└── .gitignore        # Node-specific gitignore
```

### C++ Projects

```text
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

Core code now lives under `app/`, `tools/`, and `scaffolding/`, with tests in
`tests/` and usage demos in `examples/`.

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
