"""
Pretty colored logging utilities for debugging Inspektor.
Provides formatted, colored console output for better debugging.
"""

import json
from typing import Any, Dict, List
from colorama import Fore, Back, Style, init

# Initialize colorama for cross-platform colored output
init(autoreset=True)


class PrettyLogger:
    """Pretty logging with colors and formatting"""

    @staticmethod
    def separator(title: str = "", char: str = "=", length: int = 80):
        """Print a separator line with optional title"""
        if title:
            title_str = f" {title} "
            padding = (length - len(title_str)) // 2
            line = char * padding + title_str + char * padding
            if len(line) < length:
                line += char * (length - len(line))
            print(f"\n{Fore.CYAN}{Style.BRIGHT}{line}{Style.RESET_ALL}")
        else:
            print(f"{Fore.CYAN}{char * length}{Style.RESET_ALL}")

    @staticmethod
    def info(message: str, indent: int = 0):
        """Print info message in blue"""
        prefix = "  " * indent
        print(f"{prefix}{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")

    @staticmethod
    def success(message: str, indent: int = 0):
        """Print success message in green"""
        prefix = "  " * indent
        print(f"{prefix}{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

    @staticmethod
    def warning(message: str, indent: int = 0):
        """Print warning message in yellow"""
        prefix = "  " * indent
        print(f"{prefix}{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")

    @staticmethod
    def error(message: str, indent: int = 0):
        """Print error message in red"""
        prefix = "  " * indent
        print(f"{prefix}{Fore.RED}✗ {message}{Style.RESET_ALL}")

    @staticmethod
    def metadata_request(message: str, indent: int = 0):
        """Print metadata request in magenta"""
        prefix = "  " * indent
        print(f"{prefix}{Fore.MAGENTA}🔍 {message}{Style.RESET_ALL}")

    @staticmethod
    def json_data(data: Any, title: str = None, indent: int = 0, max_length: int = 1000):
        """Print JSON data with formatting"""
        prefix = "  " * indent
        if title:
            print(f"{prefix}{Fore.CYAN}{title}:{Style.RESET_ALL}")

        try:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            if len(json_str) > max_length:
                json_str = json_str[:max_length] + f"\n... (truncated, {len(json_str)} total chars)"

            for line in json_str.split('\n'):
                print(f"{prefix}  {Fore.WHITE}{line}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{prefix}  {Fore.RED}Error formatting JSON: {e}{Style.RESET_ALL}")
            print(f"{prefix}  {Fore.WHITE}{str(data)[:max_length]}{Style.RESET_ALL}")

    @staticmethod
    def conversation_message(role: str, content: str, indent: int = 0, max_length: int = 500):
        """Print a conversation message with role-based coloring"""
        prefix = "  " * indent

        # Color code by role
        if role == "system":
            color = Fore.CYAN
            icon = "⚙"
        elif role == "user":
            color = Fore.GREEN
            icon = "👤"
        elif role == "assistant":
            color = Fore.YELLOW
            icon = "🤖"
        else:
            color = Fore.WHITE
            icon = "💬"

        # Truncate long content
        display_content = content if len(content) <= max_length else content[:max_length] + "..."

        print(f"{prefix}{color}{Style.BRIGHT}{icon} {role.upper()}:{Style.RESET_ALL}")
        for line in display_content.split('\n'):
            print(f"{prefix}  {color}{line}{Style.RESET_ALL}")

    @staticmethod
    def tool_call(function_name: str, arguments: Dict[str, Any], indent: int = 0):
        """Print a tool/function call"""
        prefix = "  " * indent
        print(f"{prefix}{Fore.MAGENTA}{Style.BRIGHT}🔧 TOOL CALL: {function_name}{Style.RESET_ALL}")

        for key, value in arguments.items():
            if isinstance(value, (list, dict)):
                value_str = json.dumps(value, indent=2)[:200]
            else:
                value_str = str(value)[:200]
            print(f"{prefix}  {Fore.WHITE}{key}: {value_str}{Style.RESET_ALL}")

    @staticmethod
    def highlight(message: str, indent: int = 0):
        """Print highlighted message with background"""
        prefix = "  " * indent
        print(f"{prefix}{Back.YELLOW}{Fore.BLACK}{Style.BRIGHT} {message} {Style.RESET_ALL}")

    @staticmethod
    def metadata_summary(metadata: Dict[str, Any], indent: int = 0):
        """Print metadata summary in a readable format"""
        prefix = "  " * indent
        print(f"{prefix}{Fore.CYAN}{Style.BRIGHT}📊 CACHED METADATA:{Style.RESET_ALL}")

        if not metadata:
            print(f"{prefix}  {Fore.RED}(empty){Style.RESET_ALL}")
            return

        for metadata_type, data in metadata.items():
            print(f"{prefix}  {Fore.YELLOW}• {metadata_type}:{Style.RESET_ALL}")

            if metadata_type == "tables" and isinstance(data, dict) and "tables" in data:
                tables = data["tables"]
                if isinstance(tables, list):
                    print(f"{prefix}    {Fore.WHITE}{', '.join(tables)}{Style.RESET_ALL}")
                else:
                    print(f"{prefix}    {Fore.WHITE}{tables}{Style.RESET_ALL}")

            elif metadata_type == "schema" and isinstance(data, dict):
                for table_name in data.keys():
                    print(f"{prefix}    {Fore.WHITE}• {table_name}{Style.RESET_ALL}")

            else:
                data_str = str(data)[:150]
                print(f"{prefix}    {Fore.WHITE}{data_str}{Style.RESET_ALL}")


# Singleton instance
logger = PrettyLogger()
