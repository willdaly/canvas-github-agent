#!/usr/bin/env python3
"""Compatibility wrapper for the organized interactive CLI."""
import sys

from app.cli import interactive_mode, print_usage
import asyncio

__all__ = ["interactive_mode", "print_usage"]


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h", "help"]:
        print_usage()
    else:
        try:
            asyncio.run(interactive_mode())
        except KeyboardInterrupt:
            print("\n\nInterrupted by user. Goodbye!")
        except Exception as error:
            print(f"\n❌ Error: {error}")
            print("\nMake sure you have:")
            print("  1. Created a .env file with your API tokens")
            print("  2. Installed dependencies: pip install -r requirements.txt")
            print("\nFor more help, run: python cli.py --help")
