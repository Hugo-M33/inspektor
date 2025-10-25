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
        self.system_prompt = """You are an expert SQL query generator. Your job is to convert natural language questions into accurate, safe SQL queries.

CRITICAL RULE: You MUST ALWAYS use the provided tools. NEVER respond with plain text. ALWAYS call a function.

WORKFLOW:
1. Analyze the user's question to understand what data they need
2. Use tools to gather necessary metadata about the database:
   - get_table_names: Get list of available tables
   - get_table_schema: Get column details for specific tables
   - get_relationships: Get table relationships (both explicit foreign keys and inferred relationships)

3. Once you have sufficient metadata, use generate_sql to create the final query

QUERY PLANNING STRATEGY - READ THIS CAREFULLY:
Before requesting ANY metadata, plan what you actually need:

1. **Identify the Query Type:**
   - Single table query (e.g., "List all users")? → Need: schema for that one table
   - Multi-table query with JOINs (e.g., "Users and their orders")? → Need: schemas for relevant tables + relationships
   - Exploratory/broad query (e.g., "Summary across all tables")? → Need: table list first, then schemas for tables that seem relevant
   - Aggregation query (e.g., "Count of...")? → Need: schema for the table being counted

2. **Check What You Already Have:**
   - Look at the "Available metadata" section in the user message
   - Do you already have table list? Schemas? Relationships?
   - Don't request metadata you already have!

3. **Request ONLY Missing Critical Metadata:**
   - Be strategic: minimize metadata requests
   - Typical flow: get_table_names → get_table_schema for 1-3 relevant tables → generate_sql
   - Only request relationships if you need to JOIN and the relationship isn't obvious from column names

4. **Examples of Good Planning:**
   - Query: "Show me all active users"
     → If you have users schema: generate_sql immediately
     → If not: get_table_schema(['users']) → generate_sql

   - Query: "List users and their files"
     → If you have users + files schemas: check if relationship is obvious (user_id column) → generate_sql
     → If relationship unclear: get_relationships → generate_sql

   - Query: "Give me a summary across all tables"
     → If you have table list but no schemas: get_table_schema for all/key tables → generate_sql
     → If you have table list AND schemas: generate_sql immediately with multi-table query

METADATA SUFFICIENCY CHECK - CRITICAL:
Before requesting MORE metadata, ask yourself:
- "Can I write a SQL query that answers the user's question with what I currently have?"
- If YES → Call generate_sql immediately
- If NO → Request ONE specific metadata type that's blocking you

Common signs you have ENOUGH metadata:
✓ You have table schemas for all tables mentioned in the query
✓ Column names make relationships obvious (user_id, order_id, etc.)
✓ You have a table list and the query is exploratory (can query multiple tables)
✓ The query is simple and you have the relevant table schema

STOP OVER-REQUESTING: After 2 metadata requests, you should STRONGLY favor generating SQL unless truly blocked.

TOOL USAGE - MANDATORY:
- If you need metadata: Call get_table_names or get_table_schema or get_relationships
- If you can generate SQL: Call generate_sql with the query
- NEVER say "Would you like me to..." - just call the tool
- NEVER ask clarifying questions - make reasonable assumptions and use generate_sql
- NEVER respond with conversational text - ONLY use tools

RULES FOR SQL GENERATION:
- CRITICAL: Check the metadata to determine the database type (PostgreSQL, MySQL, or SQLite)
- Use syntax appropriate for the specific database type:
  * PostgreSQL: Supports `::type` casting, LIMIT/OFFSET, advanced features
  * MySQL: Uses CAST() function, LIMIT syntax, different string functions
  * SQLite: Simpler syntax, limited type system, no schema prefixes
- Prefer explicit JOINs over implicit ones
- Always use table aliases for clarity
- Include appropriate WHERE clauses
- Use LIMIT to avoid overwhelming results (default 100 unless user specifies)
- Never generate destructive queries (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE)
- Only generate SELECT queries
- Be conservative - if you're unsure, request more metadata instead of guessing

TYPE CASTING FOR SQLX COMPATIBILITY (CRITICAL):
- ALWAYS cast problematic types to TEXT for proper serialization by sqlx
- Required casts (use PostgreSQL ::text syntax, or CAST(col AS TEXT) for MySQL/SQLite):
  * TIMESTAMP/DATETIME columns → ::text (e.g., created_at::text)
  * NUMERIC/DECIMAL columns → ::text (e.g., price::numeric::text or price::text)
  * DATE columns → ::text (e.g., birth_date::text)
  * TIME columns → ::text (e.g., start_time::text)
  * INTERVAL columns → ::text (PostgreSQL specific)
  * UUID columns → ::text (e.g., id::text)
  * JSON/JSONB columns → ::text (if needed for display)
  * BYTEA/BLOB columns → encode(col, 'hex')::text or similar
- Only exception: If the column is used in WHERE/HAVING/ORDER BY/GROUP BY, keep original type
- Example: SELECT id::text, created_at::text, price::text, status FROM orders WHERE created_at > '2024-01-01'
- For MySQL: Use CAST(column AS CHAR) instead of ::text
- For SQLite: Use CAST(column AS TEXT) or just the column (SQLite is more flexible)

HANDLING RELATIONSHIPS:
- Relationships include both explicit foreign keys AND inferred relationships based on naming patterns
- INFERRED relationships are detected from column names like 'user_id', 'order_id' but may not have database constraints
- Always check the relationship_type field: 'foreign_key' (guaranteed) vs 'inferred' (likely but not guaranteed)
- For inferred relationships with 'high' confidence, you can use them directly in JOINs
- For 'medium' or 'low' confidence inferred relationships, validate against schema before use
- When in doubt, request schema to verify that the columns exist and have compatible types

METADATA GATHERING STRATEGY:
- **CRITICAL ASSUMPTION**: You likely DO NOT know about all tables in the database!
  * Cached metadata often contains only a SUBSET of tables that were previously queried
  * If the user asks about "all tables", "entire database", or mentions tables you haven't seen, you MUST call get_table_names first
  * Never assume the tables in your cached metadata represent the complete database schema

- **CRITICAL**: Before requesting metadata, check the conversation history and available metadata to see if you already have it!
- Look for "Metadata received" messages in the conversation - these show what you've already been given
- **DO NOT** re-request metadata you've already received in this conversation
- Start with get_table_names when:
  * User asks about "all tables", "entire database", "database-wide", or similar
  * User mentions a table name you haven't seen in cached metadata
  * You're unsure if you have a complete view of available tables
- Request schemas ONLY for tables you haven't seen schemas for yet
- Request relationships only when you need to do JOINs and don't have that info
- Minimize metadata requests - use what you already have when possible, but don't skip get_table_names when you need the full picture

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
                # Build a contextual continuation prompt
                user_message = self._build_continuation_prompt(
                    cached_metadata, conversation_history
                )
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

CRITICAL ERROR HANDLING RULES:
- If the error mentions a column that doesn't exist (e.g., "column does not exist", "unknown column", "no such column"):
  * Your cached metadata may be outdated or incomplete
  * You MUST call get_table_schema to refresh the schema for the affected table(s)
  * DO NOT guess - get the actual current schema before generating a fix

- If the error mentions a table that doesn't exist:
  * Call get_table_names to see what tables are actually available
  * The table name might have changed or you may have used the wrong name

- For other errors (syntax, type mismatches, etc.):
  * You can call generate_sql directly with the corrected query
"""

            if cached_metadata:
                metadata_summary = self._format_metadata_for_prompt(cached_metadata)
                error_context += f"\n\nAvailable metadata (may be outdated):\n{metadata_summary}"
                plogger.info("Added cached metadata to error context")

            if conversation_context:
                context_summary = self._format_context_for_prompt(conversation_context)
                error_context += f"\n\nLearned context from previous queries:\n{context_summary}"
                plogger.info("Added workspace context to error correction prompt")

            error_context += "\n\nDecide whether you need to request fresh metadata (for column/table existence errors) or can directly fix the SQL (for other errors)."

            messages.append({"role": "user", "content": error_context})

            # Log error context being sent
            plogger.separator("ERROR CONTEXT SENT TO OPENAI", "~", 100)
            plogger.conversation_message("user", error_context[:2000], indent=1, max_length=2000)

            # Get response from LLM - let it decide if it needs metadata or can fix directly
            plogger.separator("CALLING OPENAI FOR ERROR CORRECTION", "~", 100)
            response = self.llm.chat_completion(
                messages=messages,
                functions=self.tools,
                function_call="auto",  # Let LLM choose - it may need to request updated metadata
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
                    "failed_sql": failed_sql,  # Include the SQL that originally failed
                }

            plogger.error("LLM did not call any tool")
            return {
                "status": "error",
                "error": "LLM did not provide a corrected query",
                "failed_sql": failed_sql,  # Include the SQL that originally failed
            }

        except LLMError as e:
            logger.error(f"LLM error in handle_error: {e}")
            return {
                "status": "error",
                "error": f"LLM error: {str(e)}",
                "failed_sql": failed_sql,  # Include the SQL that originally failed
            }
        except Exception as e:
            logger.error(f"Unexpected error in handle_error: {e}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "failed_sql": failed_sql,  # Include the SQL that originally failed
            }

    def _build_continuation_prompt(
        self,
        cached_metadata: Optional[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> str:
        """
        Build a contextual continuation prompt after metadata is submitted.

        Args:
            cached_metadata: Current cached metadata
            conversation_history: Conversation history for context

        Returns:
            Contextual continuation prompt
        """
        # Extract the original user query from history
        original_query = None
        if conversation_history:
            for msg in conversation_history:
                if msg.get("role") == "user" and "User query:" in msg.get("content", ""):
                    # Extract query from "User query: {query}" format
                    content = msg.get("content", "")
                    if content.startswith("User query:"):
                        original_query = content[11:].split("\n")[0].strip()
                        break

        # Count metadata requests made so far and track what was requested
        metadata_request_count = 0
        requested_metadata_types = []
        if conversation_history:
            for msg in conversation_history:
                # Check if this is an assistant message with metadata request in content
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    # Look for metadata request patterns
                    if "get_table_names" in content or "tables" in content.lower():
                        if "table" not in [t for t in requested_metadata_types]:
                            metadata_request_count += 1
                            requested_metadata_types.append("tables")
                    if "get_table_schema" in content or "schema" in content.lower():
                        if "schema" not in requested_metadata_types:
                            metadata_request_count += 1
                            requested_metadata_types.append("schema")
                    if "get_relationships" in content or "relationship" in content.lower():
                        if "relationships" not in requested_metadata_types:
                            metadata_request_count += 1
                            requested_metadata_types.append("relationships")

        # Build the prompt
        prompt_parts = []

        prompt_parts.append("You have received the requested metadata. Here's your current status:")
        prompt_parts.append("")

        if original_query:
            prompt_parts.append(f"📋 Original user query: \"{original_query}\"")
            prompt_parts.append("")

        # Summary of what metadata is now available
        if cached_metadata:
            metadata_items = []
            if "tables" in cached_metadata:
                tables_data = cached_metadata["tables"]
                if isinstance(tables_data, dict) and "tables" in tables_data:
                    tables_data = tables_data["tables"]
                if isinstance(tables_data, list):
                    metadata_items.append(f"✓ Table list: {len(tables_data)} tables")

            if "schema" in cached_metadata or "schemas" in cached_metadata:
                schema_data = cached_metadata.get("schema") or cached_metadata.get("schemas")
                if isinstance(schema_data, dict):
                    table_count = sum(1 for k in schema_data.keys() if k not in ["tables", "schema", "schemas", "db_type"])
                    metadata_items.append(f"✓ Schemas loaded: {table_count} tables")

            if "relationships" in cached_metadata:
                rel_data = cached_metadata["relationships"]
                if isinstance(rel_data, list):
                    metadata_items.append(f"✓ Relationships: {len(rel_data)} found")

            if metadata_items:
                prompt_parts.append("Current metadata:")
                for item in metadata_items:
                    prompt_parts.append(f"  {item}")
                prompt_parts.append("")

        # Show what metadata has already been requested
        if requested_metadata_types:
            prompt_parts.append(f"📊 Metadata already requested: {', '.join(requested_metadata_types)}")
            prompt_parts.append("")

        # Guidance based on request count
        if metadata_request_count >= 2:
            prompt_parts.append("⚠️ You have made multiple metadata requests. You should now have sufficient information.")
            prompt_parts.append("")
            prompt_parts.append("DECISION POINT: Can you generate SQL that answers the user's query with the available metadata?")
            prompt_parts.append("- If YES → Call generate_sql immediately")
            prompt_parts.append("- If NO → Explain what CRITICAL information is still missing, then request it")
            prompt_parts.append("")
            prompt_parts.append("REMINDER: Minimize metadata requests. If you have table list + schemas, that's usually enough!")
        else:
            prompt_parts.append("DECISION POINT: Do you have sufficient metadata to generate SQL?")
            prompt_parts.append("- Review the available metadata below")
            prompt_parts.append("- If you can answer the query → Call generate_sql")
            prompt_parts.append("- If you need more metadata → Request ONE specific type")

        return "\n".join(prompt_parts)

    def _format_metadata_for_prompt(self, metadata: Dict[str, Any]) -> str:
        """
        Format cached metadata into a concise string for the LLM prompt.

        Args:
            metadata: Cached metadata dictionary

        Returns:
            Formatted string
        """
        parts = []

        # Database Type (CRITICAL - must be shown first)
        db_type = None
        if "tables" in metadata and isinstance(metadata["tables"], dict):
            db_type = metadata["tables"].get("db_type")
        elif "schema" in metadata and isinstance(metadata["schema"], dict):
            db_type = metadata["schema"].get("db_type")
        elif "schemas" in metadata and isinstance(metadata["schemas"], dict):
            db_type = metadata["schemas"].get("db_type")
        elif "relationships" in metadata and isinstance(metadata["relationships"], dict):
            db_type = metadata["relationships"].get("db_type")
        elif "db_type" in metadata:
            db_type = metadata.get("db_type")

        if db_type:
            db_name = {
                "postgres": "PostgreSQL",
                "mysql": "MySQL",
                "sqlite": "SQLite"
            }.get(db_type, db_type)
            parts.append(f"**DATABASE TYPE: {db_name}** ← Use {db_name}-specific syntax!")

        parts.append("")  # Empty line for readability
        parts.append("=" * 60)
        parts.append("METADATA INVENTORY")
        parts.append("=" * 60)

        # Tables
        has_complete_table_list = False
        if "tables" in metadata:
            tables_data = metadata["tables"]
            # Handle nested structure: {"tables": ["users", "posts"]}
            if isinstance(tables_data, dict) and "tables" in tables_data:
                tables_data = tables_data["tables"]

            if isinstance(tables_data, list):
                has_complete_table_list = True
                parts.append(f"✓ COMPLETE TABLE LIST ({len(tables_data)} tables)")
                parts.append(f"  Tables: {', '.join(tables_data)}")
            else:
                parts.append(f"Tables: {json.dumps(tables_data)}")
        else:
            parts.append("✗ NO TABLE LIST - Consider calling get_table_names if needed")

        # Schemas (with warning if incomplete)
        parts.append("")
        if "schema" in metadata or "schemas" in metadata:
            schema_data = metadata.get("schema") or metadata.get("schemas")

            # Handle nested structure: {"schema": {"users": [...], "posts": [...]}}
            if isinstance(schema_data, dict):
                schema_table_count = 0
                schema_tables = []
                for table_name, columns in schema_data.items():
                    # Skip if table_name is not a real table (e.g., metadata wrapper keys)
                    if table_name in ["tables", "schema", "schemas", "db_type"]:
                        continue

                    schema_table_count += 1
                    schema_tables.append(table_name)
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
                            parts.append(f"\nTable '{table_name}' ({len(col_strs)} columns):")
                            parts.append("  " + "\n  ".join(col_strs))

                # Summary at the top
                if schema_table_count > 0:
                    parts.insert(len(parts) - schema_table_count * 3, f"✓ TABLE SCHEMAS LOADED ({schema_table_count} tables: {', '.join(schema_tables)})")
                    # Warn if we have schemas but no table list (might be incomplete)
                    if not has_complete_table_list:
                        parts.insert(len(parts) - schema_table_count * 3 + 1, f"⚠️ WARNING: You have schemas for {schema_table_count} table(s) but no complete table list!")
                        parts.insert(len(parts) - schema_table_count * 3 + 2, f"   → This may be incomplete. Consider calling get_table_names to discover all tables.")
            else:
                parts.append(f"Schema: {json.dumps(schema_data)}")
        else:
            parts.append("✗ NO SCHEMAS LOADED - Consider calling get_table_schema for relevant tables")

        # Relationships
        parts.append("")
        if "relationships" in metadata:
            relationships = metadata["relationships"]
            if isinstance(relationships, list) and relationships:
                parts.append(f"✓ RELATIONSHIPS ({len(relationships)} found):")
                for rel in relationships:
                    if isinstance(rel, dict):
                        # Support both old format (from_table/from_column) and new format (table_name/column_name)
                        from_table = rel.get('from_table') or rel.get('table_name')
                        from_col = rel.get('from_column') or rel.get('column_name')
                        to_table = rel.get('to_table') or rel.get('foreign_table')
                        to_col = rel.get('to_column') or rel.get('foreign_column')
                        rel_type = rel.get('relationship_type', 'unknown')
                        confidence = rel.get('confidence', '')

                        # Format the relationship with type and confidence
                        rel_str = f"  {from_table}.{from_col} → {to_table}.{to_col}"
                        if rel_type == 'inferred':
                            rel_str += f" (INFERRED, confidence: {confidence})"
                        elif rel_type == 'foreign_key':
                            rel_str += " (FK constraint)"
                        elif rel_type == 'learned':
                            rel_str += " (learned from previous queries)"

                        parts.append(rel_str)
                    else:
                        parts.append(f"  {rel}")
            else:
                parts.append("✗ NO RELATIONSHIPS - Consider calling get_relationships if you need to JOIN tables")
        else:
            parts.append("✗ NO RELATIONSHIPS - Consider calling get_relationships if you need to JOIN tables")

        parts.append("")
        parts.append("=" * 60)
        parts.append("END OF METADATA INVENTORY")
        parts.append("=" * 60)

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
