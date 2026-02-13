"""
GitHub MCP Tools for creating and managing repositories.
"""
import os
import json
from typing import Dict, List, Optional, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import asynccontextmanager


class GitHubTools:
    """Tools for interacting with GitHub via MCP."""
    
    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_username = os.getenv("GITHUB_USERNAME")
        self.github_org = os.getenv("GITHUB_ORG", "")
        
    @asynccontextmanager
    async def get_github_session(self):
        """Create a GitHub MCP session."""
        # GitHub MCP server is typically run via npx
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-github"],
            env={
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token,
            }
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    
    async def create_repository(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Create a new GitHub repository.
        
        Args:
            name: Repository name
            description: Repository description
            private: Whether the repo should be private
            auto_init: Whether to initialize with a README
            
        Returns:
            Repository details dictionary
        """
        async with self.get_github_session() as session:
            # List available tools to understand the API
            tools = await session.list_tools()
            
            # The actual tool name may vary, common ones are:
            # - create_repository
            # - github_create_repository
            # We'll try the most common pattern
            try:
                result = await session.call_tool(
                    "create_repository",
                    arguments={
                        "name": name,
                        "description": description,
                        "private": private,
                        "auto_init": auto_init,
                        "owner": self.github_org if self.github_org else self.github_username
                    }
                )
                if hasattr(result, 'content') and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, 'text'):
                        return json.loads(content.text)
            except Exception as e:
                print(f"Error creating repository: {e}")
            return None
    
    async def create_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str = "Add file",
        branch: str = "main"
    ) -> bool:
        """
        Create or update a file in a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path in the repository
            content: File content
            message: Commit message
            branch: Branch name
            
        Returns:
            True if successful, False otherwise
        """
        async with self.get_github_session() as session:
            try:
                result = await session.call_tool(
                    "create_or_update_file",
                    arguments={
                        "owner": owner,
                        "repo": repo,
                        "path": path,
                        "content": content,
                        "message": message,
                        "branch": branch
                    }
                )
                return True
            except Exception as e:
                print(f"Error creating file: {e}")
                return False
    
    async def create_directory_structure(
        self,
        owner: str,
        repo: str,
        files: Dict[str, str],
        branch: str = "main"
    ) -> bool:
        """
        Create multiple files in a repository to establish a directory structure.
        
        Args:
            owner: Repository owner
            repo: Repository name
            files: Dictionary mapping file paths to their content
            branch: Branch name
            
        Returns:
            True if all files created successfully
        """
        success = True
        for path, content in files.items():
            result = await self.create_file(
                owner=owner,
                repo=repo,
                path=path,
                content=content,
                message=f"Add {path}",
                branch=branch
            )
            success = success and result
        return success
