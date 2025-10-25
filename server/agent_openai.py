"""
OpenAI-based SQL Agent for natural language to SQL conversion.
Uses OpenAI's native function calling to request metadata iteratively and generate SQL.
"""

from typing import Dict, Any, List, Optional
from llm_interface import LLMInterface, LLMError
from tools import (
    get_tool_definitions,
    parse_tool_call,
    create_metadata_request_from_tool_call,
    create_sql_response_from_tool_call,
    is_metadata_tool,
    is_sql_generation_tool,
)
import logging
import json
from logger_config import logger as plogger

logger = logging.getLogger(__name__)


class SQLAgent:
    """
    SQL generation agent using OpenAI with function calling.
    Iteratively requests metadata to build accurate SQL queries.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
    ):
        """
        Initialize the SQL agent.

        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
        """
        self.llm = LLMInterface(api_key=api_key, model=model)
        self.tools = get_tool_definitions()

        # System prompt that guides the LLM's behavior
        #- get_relationships: Get foreign key relationships for JOINs
        self.system_prompt = """You are an expert SQL query generator. Your job is to convert natural language questions into accurate, safe SQL queries.

CRITICAL RULE: You MUST ALWAYS use the provided tools. NEVER respond with plain text. ALWAYS call a function.

WORKFLOW:
1. Analyze the user's question to understand what data they need
2. Use tools to gather necessary metadata about the database:
   - get_table_names: Get list of available tables
   - get_table_schema: Get column details for specific tables

3. Once you have sufficient metadata, use generate_sql to create the final query

TOOL USAGE - MANDATORY:
- If you need metadata: Call get_table_names or get_table_schema
- If you can generate SQL: Call generate_sql with the query
- NEVER say "Would you like me to..." - just call the tool
- NEVER ask clarifying questions - make reasonable assumptions and use generate_sql
- NEVER respond with conversational text - ONLY use tools

RULES FOR SQL GENERATION:
- Use standard SQL syntax compatible with PostgreSQL, MySQL, and SQLite
- Prefer explicit JOINs over implicit ones
- Always use table aliases for clarity
- Include appropriate WHERE clauses
- Use LIMIT to avoid overwhelming results (default 100 unless user specifies)
- Never generate destructive queries (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE)
- Only generate SELECT queries
- Be conservative - if you're unsure, request more metadata instead of guessing
- When dealing with timestamp/datetime issues, cast to text (::text) if needed

METADATA GATHERING STRATEGY:
- **CRITICAL**: Before requesting metadata, check the conversation history and available metadata to see if you already have it!
- Look for "Metadata received" messages in the conversation - these show what you've already been given
- **DO NOT** re-request metadata you've already received in this conversation
- Start with get_table_names ONLY if you don't see table information already provided
- Request schemas ONLY for tables you haven't seen schemas for yet
- Request relationships only when you need to do JOINs and don't have that info
- Minimize metadata requests - use what you already have when possible

CONFIDENCE LEVELS:
- high: You have all necessary metadata and the query is straightforward
- medium: You have metadata but the query is complex or ambiguous
- low: You're missing some metadata but generating a best-effort query

Remember: The user must approve each metadata request, so minimize unnecessary requests while ensuring accuracy. Always check what metadata you've already received before requesting more!

IMPORTANT: ALWAYS call a tool. NEVER respond with text alone."""

    def process_query(
        self,
        query: str,
        database_id: str,
        cached_metadata: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process a natural language query and return either a metadata request or SQL.

        Args:
            query: Natural language query
            database_id: Database identifier
            cached_metadata: Previously cached metadata
            conversation_history: Previous conversation messages
            conversation_context: Extracted context from previous successful queries

        Returns:
            Response dict with status and either metadata_request or sql_response
        """
        try:
            plogger.separator("AGENT: Building LLM Request", "~", 100)

            # Build messages for the LLM
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]

            # Add conversation history if provided
            if conversation_history:
                plogger.info(f"Adding {len(conversation_history)} messages from conversation history")
                messages.extend(conversation_history)

            # Build the current message
            # If query is empty, it means we're continuing after metadata submission
            if query.strip():
                user_message = f"User query: {query}"
                plogger.info(f"New user query: {query[:150]}")
            else:
                # Empty query means: continue with the conversation using new metadata
                user_message = "Please continue processing the previous query with the updated metadata."
                plogger.warning("Empty query - continuing with new metadata")

            if cached_metadata:
                metadata_summary = self._format_metadata_for_prompt(cached_metadata)
                user_message += f"\n\nAvailable metadata:\n{metadata_summary}"
                plogger.info("Added cached metadata to user message")

            if conversation_context:
                context_summary = self._format_context_for_prompt(conversation_context)
                user_message += f"\n\nLearned context from previous queries:\n{context_summary}"
                plogger.info("Added conversation context to user message")

            messages.append({"role": "user", "content": user_message})

            # Log complete messages array being sent to LLM
            plogger.separator("MESSAGES SENT TO OPENAI", "~", 100)
            plogger.info(f"Total messages: {len(messages)}")
            for i, msg in enumerate(messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if role == "system":
                    plogger.conversation_message(role, content, indent=1, max_length=5000)
                else:
                    plogger.conversation_message(role, content, indent=1, max_length=5000)

            # Get response from LLM with function calling
            plogger.separator("CALLING OPENAI API", "~", 100)
            response = self.llm.chat_completion(
                messages=messages,
                functions=self.tools,
                function_call="auto",  # Let LLM decide when to call functions
                temperature=0.0,  # Deterministic for SQL generation
            )

            # Log OpenAI response
            plogger.separator("OPENAI RESPONSE", "~", 100)
            plogger.json_data(response, "Raw Response", max_length=1500)

            # Check if LLM wants to call a function
            if "tool_calls" in response and response["tool_calls"]:
                tool_call = parse_tool_call(response["tool_calls"][0])
                function_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]

                plogger.separator("LLM DECISION: TOOL CALL", "~", 100)
                plogger.tool_call(function_name, arguments, indent=0)
                logger.info(f"LLM called function: {function_name}")

                # Check if it's a metadata request
                if is_metadata_tool(function_name):
                    metadata_request = create_metadata_request_from_tool_call(tool_call)
                    plogger.highlight(f"⚠️  METADATA REQUEST: {metadata_request.get('metadata_type')}")
                    plogger.warning(f"Reason: {metadata_request.get('reason')}")
                    return {
                        "status": "needs_metadata",
                        "metadata_request": metadata_request,
                    }

                # Check if it's SQL generation
                elif is_sql_generation_tool(function_name):
                    sql_response = create_sql_response_from_tool_call(tool_call)
                    plogger.highlight(f"✓ SQL GENERATED")
                    plogger.success(f"SQL: {sql_response.get('sql', '')[:200]}")
                    return {
                        "status": "ready",
                        "sql_response": sql_response,
                    }

                else:
                    plogger.error(f"Unknown function: {function_name}")
                    return {
                        "status": "error",
                        "error": f"Unknown function called: {function_name}",
                    }

            # If no function call, the LLM violated the rules - log and return error
            elif response["content"]:
                plogger.error(f"LLM responded with text instead of calling a tool!")
                plogger.warning(f"Response content: {response['content'][:300]}")
                return {
                    "status": "error",
                    "error": f"LLM error: Expected tool call but got text response. Please try rephrasing your question.",
                }

            else:
                plogger.error("LLM provided neither tool call nor text response")
                return {
                    "status": "error",
                    "error": "LLM did not provide a valid response",
                }

        except LLMError as e:
            logger.error(f"LLM error in process_query: {e}")
            return {
                "status": "error",
                "error": f"LLM error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Unexpected error in process_query: {e}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
            }

    def handle_error(
        self,
        original_query: str,
        failed_sql: str,
        error_message: str,
        cached_metadata: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle SQL execution errors and attempt to generate corrected SQL.

        Args:
            original_query: Original natural language query
            failed_sql: SQL that failed to execute
            error_message: Error message from database
            cached_metadata: Available metadata
            conversation_context: Workspace context with learned patterns and hints

        Returns:
            Response dict with corrected SQL or error
        """
        try:
            plogger.separator("AGENT: Handling SQL Error", "~", 100)
            plogger.error(f"Failed SQL: {failed_sql[:200]}")
            plogger.error(f"Error: {error_message[:200]}")

            messages = [
                {"role": "system", "content": self.system_prompt}
            ]

            error_context = f"""The following SQL query failed when executed:

Original user question: {original_query}

Failed SQL:
```sql
{failed_sql}
```

Database error:
{error_message}
"""

            if cached_metadata:
                metadata_summary = self._format_metadata_for_prompt(cached_metadata)
                error_context += f"\n\nAvailable metadata:\n{metadata_summary}"
                plogger.info("Added cached metadata to error context")

            if conversation_context:
                context_summary = self._format_context_for_prompt(conversation_context)
                error_context += f"\n\nLearned context from previous queries:\n{context_summary}"
                plogger.info("Added workspace context to error correction prompt")

            error_context += "\n\nYou MUST call the generate_sql tool with the corrected query. Do not respond with text - only use the generate_sql tool to provide the fixed SQL."

            messages.append({"role": "user", "content": error_context})

            # Log error context being sent
            plogger.separator("ERROR CONTEXT SENT TO OPENAI", "~", 100)
            plogger.conversation_message("user", error_context[:2000], indent=1, max_length=2000)

            # Get response from LLM - force it to call generate_sql
            plogger.separator("CALLING OPENAI FOR ERROR CORRECTION", "~", 100)
            response = self.llm.chat_completion(
                messages=messages,
                functions=self.tools,
                function_call={"type": "function", "function": {"name": "generate_sql"}},  # Force SQL generation
                temperature=0.0,
            )

            plogger.separator("OPENAI ERROR CORRECTION RESPONSE", "~", 100)
            plogger.json_data(response, "Raw Response", max_length=1500)

            # Parse response (same logic as process_query)
            if "tool_calls" in response and response["tool_calls"]:
                tool_call = parse_tool_call(response["tool_calls"][0])
                function_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]

                plogger.tool_call(function_name, arguments, indent=0)

                if is_metadata_tool(function_name):
                    metadata_request = create_metadata_request_from_tool_call(tool_call)
                    plogger.warning(f"LLM needs more metadata to fix error: {metadata_request.get('metadata_type')}")
                    return {
                        "status": "needs_metadata",
                        "metadata_request": metadata_request,
                    }
                elif is_sql_generation_tool(function_name):
                    sql_response = create_sql_response_from_tool_call(tool_call)
                    plogger.success(f"LLM generated corrected SQL")
                    plogger.info(f"Corrected SQL: {sql_response.get('sql', '')[:200]}")
                    return {
                        "status": "ready",
                        "sql_response": sql_response,
                    }

            elif response["content"]:
                plogger.error("LLM responded with text instead of calling generate_sql!")
                plogger.warning(f"Response: {response['content'][:300]}")
                return {
                    "status": "error",
                    "error": f"Could not fix query. LLM provided explanation instead of corrected SQL. Please try a different query.",
                }

            plogger.error("LLM did not call any tool")
            return {
                "status": "error",
                "error": "LLM did not provide a corrected query",
            }

        except LLMError as e:
            logger.error(f"LLM error in handle_error: {e}")
            return {
                "status": "error",
                "error": f"LLM error: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Unexpected error in handle_error: {e}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
            }

    def _format_metadata_for_prompt(self, metadata: Dict[str, Any]) -> str:
        """
        Format cached metadata into a concise string for the LLM prompt.

        Args:
            metadata: Cached metadata dictionary

        Returns:
            Formatted string
        """
        parts = []

        # Tables
        if "tables" in metadata:
            tables_data = metadata["tables"]
            # Handle nested structure: {"tables": ["users", "posts"]}
            if isinstance(tables_data, dict) and "tables" in tables_data:
                tables_data = tables_data["tables"]

            if isinstance(tables_data, list):
                parts.append(f"Tables: {', '.join(tables_data)}")
            else:
                parts.append(f"Tables: {json.dumps(tables_data)}")

        # Schemas
        if "schema" in metadata or "schemas" in metadata:
            schema_data = metadata.get("schema") or metadata.get("schemas")

            # Handle nested structure: {"schema": {"users": [...], "posts": [...]}}
            if isinstance(schema_data, dict):
                for table_name, columns in schema_data.items():
                    # Skip if table_name is not a real table (e.g., metadata wrapper keys)
                    if table_name in ["tables", "schema", "schemas"]:
                        continue

                    if isinstance(columns, list):
                        col_strs = []
                        for col in columns:
                            if isinstance(col, dict):
                                # Try multiple field name variations
                                name = col.get('name') or col.get('column_name') or col.get('field_name', 'unknown')
                                data_type = col.get('data_type') or col.get('type') or 'unknown'
                                col_str = f"{name} ({data_type})"

                                # Add constraints
                                if col.get('is_nullable') is False or col.get('nullable') is False:
                                    col_str += " NOT NULL"
                                if col.get('is_primary_key') or col.get('primary_key'):
                                    col_str += " PRIMARY KEY"

                                col_strs.append(col_str)
                            else:
                                col_strs.append(str(col))

                        if col_strs:  # Only add if we have columns
                            parts.append(f"\nTable '{table_name}':\n  " + "\n  ".join(col_strs))
            else:
                parts.append(f"Schema: {json.dumps(schema_data)}")

        # Relationships
        if "relationships" in metadata:
            relationships = metadata["relationships"]
            if isinstance(relationships, list) and relationships:
                parts.append("\nRelationships:")
                for rel in relationships:
                    if isinstance(rel, dict):
                        parts.append(f"  {rel.get('from_table')}.{rel.get('from_column')} -> {rel.get('to_table')}.{rel.get('to_column')}")
                    else:
                        parts.append(f"  {rel}")

        return "\n".join(parts) if parts else "No metadata available"

    def _format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format conversation context into a concise string for the LLM prompt.
        Context includes learned relationships, business rules, and SQL patterns.

        Args:
            context: Conversation context dictionary

        Returns:
            Formatted string
        """
        parts = []

        # Tables used in previous queries
        if context.get("tables_used"):
            tables = context["tables_used"]
            if tables:
                parts.append(f"Tables used in previous queries: {', '.join(tables)}")

        # Known relationships
        if context.get("relationships"):
            relationships = context["relationships"]
            if relationships:
                parts.append("\nKnown relationships:")
                for rel in relationships:
                    if isinstance(rel, dict):
                        parts.append(
                            f"  - {rel.get('from_table')}.{rel.get('from_column')} → "
                            f"{rel.get('to_table')}.{rel.get('to_column')} ({rel.get('type', 'unknown')})"
                        )

        # Column typecast hints
        if context.get("column_typecast_hints"):
            hints = context["column_typecast_hints"]
            if hints:
                parts.append("\nColumn typecast hints:")
                for hint in hints:
                    if isinstance(hint, dict):
                        example = f" (e.g., {hint['example']})" if hint.get("example") else ""
                        parts.append(
                            f"  - {hint.get('table')}.{hint.get('column')}: {hint.get('hint')}{example}"
                        )

        # Business context/rules
        if context.get("business_context"):
            business_rules = context["business_context"]
            if business_rules:
                parts.append("\nBusiness rules and domain knowledge:")
                for rule in business_rules:
                    parts.append(f"  - {rule}")

        # SQL patterns
        if context.get("sql_patterns"):
            patterns = context["sql_patterns"]
            if patterns:
                parts.append("\nUseful SQL patterns:")
                for pattern in patterns:
                    if isinstance(pattern, dict):
                        example = f"\n    Example: {pattern['example']}" if pattern.get("example") else ""
                        parts.append(f"  - {pattern.get('pattern')}{example}")

        return "\n".join(parts) if parts else "No context available yet"

    def get_token_usage(self) -> Dict[str, int]:
        """Get cumulative token usage statistics"""
        return self.llm.get_token_usage()

    def reset_token_usage(self):
        """Reset token usage counters"""
        self.llm.reset_token_usage()
