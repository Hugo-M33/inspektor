"""
Tool definitions for OpenAI function calling.
Defines available tools that the LLM can use to request metadata from the client.
"""

from typing import List, Dict, Any


# Tool definitions in OpenAI function calling format
def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Get all available tool definitions for OpenAI function calling.

    Returns:
        List of tool definition dictionaries
    """
    return [
        {
            "name": "get_table_names",
            "description": "Request the list of all table names in the database. Use this when you need to know what tables exist before generating SQL queries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Brief explanation of why you need the table list (shown to user for approval)",
                    }
                },
                "required": ["reason"],
            },
        },
        {
            "name": "get_table_schema",
            "description": "Request detailed schema information for specific tables (columns, types, constraints). Use this when you know which tables are relevant but need their structure.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of table names to get schema for",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Brief explanation of why you need these schemas (shown to user for approval)",
                    },
                },
                "required": ["table_names", "reason"],
            },
        },
        #{
        #    "name": "get_relationships",
        #    "description": "Request foreign key relationships between tables. Use this when you need to perform JOINs and need to know how tables are related.",
        #    "parameters": {
        #        "type": "object",
        #        "properties": {
        #            "reason": {
        #                "type": "string",
        #                "description": "Brief explanation of why you need relationship information (shown to user for approval)",
        #            }
        #        },
        #        "required": ["reason"],
        #    },
        #},
        {
            "name": "generate_sql",
            "description": "Generate the final SQL query when you have enough metadata. This is the final step after gathering necessary information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "The complete SQL query to execute",
                    },
                    "explanation": {
                        "type": "string",
                        "description": "Clear explanation of what the query does and why it answers the user's question",
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Your confidence level in this query being correct",
                    },
                },
                "required": ["sql", "explanation", "confidence"],
            },
        },
    ]


def parse_tool_call(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a tool call from OpenAI response into a standardized format.

    Args:
        tool_call: Tool call dict from OpenAI response

    Returns:
        Parsed tool call with function name and arguments
    """
    import json

    function_name = tool_call["function"]["name"]
    arguments_str = tool_call["function"]["arguments"]

    # Parse arguments JSON string
    try:
        arguments = json.loads(arguments_str)
    except json.JSONDecodeError:
        arguments = {}

    return {
        "id": tool_call.get("id"),
        "type": tool_call.get("type", "function"),
        "function": {
            "name": function_name,
            "arguments": arguments,
        },
    }


def create_metadata_request_from_tool_call(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a tool call into a metadata request for the client.

    Args:
        tool_call: Parsed tool call dictionary

    Returns:
        Metadata request dictionary
    """
    function_name = tool_call["function"]["name"]
    arguments = tool_call["function"]["arguments"]

    if function_name == "get_table_names":
        return {
            "metadata_type": "tables",
            "params": {},
            "reason": arguments.get("reason", "Need to see available tables"),
        }

    elif function_name == "get_table_schema":
        return {
            "metadata_type": "schema",
            "params": {
                "tables": arguments.get("table_names", []),
            },
            "reason": arguments.get("reason", "Need table schema details"),
        }

    elif function_name == "get_relationships":
        return {
            "metadata_type": "relationships",
            "params": {},
            "reason": arguments.get("reason", "Need to know table relationships for JOINs"),
        }

    else:
        raise ValueError(f"Unknown tool: {function_name}")


def create_sql_response_from_tool_call(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a generate_sql tool call into a SQL response for the client.

    Args:
        tool_call: Parsed tool call dictionary

    Returns:
        SQL response dictionary
    """
    arguments = tool_call["function"]["arguments"]

    return {
        "sql": arguments.get("sql", ""),
        "explanation": arguments.get("explanation", ""),
        "confidence": arguments.get("confidence", "medium"),
    }


def is_metadata_tool(function_name: str) -> bool:
    """
    Check if a tool is a metadata request tool.

    Args:
        function_name: Name of the function

    Returns:
        True if it's a metadata tool, False otherwise
    """
    return function_name in ["get_table_names", "get_table_schema", "get_relationships"]


def is_sql_generation_tool(function_name: str) -> bool:
    """
    Check if a tool is the SQL generation tool.

    Args:
        function_name: Name of the function

    Returns:
        True if it's the generate_sql tool, False otherwise
    """
    return function_name == "generate_sql"
