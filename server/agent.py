"""
LangChain-based SQL Agent for natural language to SQL conversion.
Uses tool calling to request metadata iteratively.
"""

from typing import Dict, Any, List, Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import json


class MetadataRequest(BaseModel):
    """Model for metadata requests"""
    metadata_type: str = Field(description="Type of metadata needed: 'tables', 'schema', or 'relationships'")
    params: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters for the request")
    reason: str = Field(description="Explanation for why this metadata is needed")


class SQLAgent:
    """
    SQL generation agent using LangChain and Ollama.
    Iteratively requests metadata to build accurate SQL queries.
    """

    def __init__(self, ollama_base_url: str, model_name: str):
        """
        Initialize the SQL agent.

        Args:
            ollama_base_url: Base URL for Ollama API
            model_name: Name of the LLM model to use
        """
        self.llm = ChatOllama(
            base_url=ollama_base_url,
            model=model_name,
            temperature=0.1,  # Lower temperature for more deterministic SQL
        )

        self.system_prompt = """You are an expert SQL query generator. Your job is to convert natural language questions into accurate SQL queries.

You have access to metadata request tools to gather information about the database schema. You should:

1. Start by requesting the list of tables if you don't have it
2. Request schema information for relevant tables
3. Request relationship information if you need to do JOINs
4. Only generate SQL when you have sufficient information

Always explain your reasoning and be conservative - request metadata when unsure.

When generating SQL:
- Use standard SQL syntax
- Prefer explicit JOINs over implicit ones
- Always use table aliases for clarity
- Include appropriate WHERE clauses
- Use LIMIT when appropriate to avoid overwhelming results

Respond in JSON format with one of these structures:

For metadata requests:
{
  "status": "needs_metadata",
  "metadata_request": {
    "metadata_type": "tables|schema|relationships",
    "params": {},
    "reason": "explanation for the user"
  }
}

For final SQL:
{
  "status": "ready",
  "sql_response": {
    "sql": "SELECT ...",
    "explanation": "what this query does",
    "confidence": "high|medium|low"
  }
}

For errors:
{
  "status": "error",
  "error": "error message"
}
"""

    async def process_query(
        self,
        query: str,
        database_id: str,
        cached_metadata: Optional[Dict[str, Any]] = None,
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query and return either a metadata request or SQL.

        Args:
            query: Natural language query
            database_id: Database identifier
            cached_metadata: Previously cached metadata
            conversation_history: Previous conversation messages

        Returns:
            Response dict with status and either metadata_request or sql_response
        """
        # Build the conversation
        messages = [SystemMessage(content=self.system_prompt)]
         

        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    messages.append(AIMessage(content=msg["content"]))

        # Add current query with available metadata
        metadata_context = ""
        if cached_metadata:
            metadata_context = f"\n\nAvailable metadata:\n{json.dumps(cached_metadata, indent=2)}"

        user_message = f"User query: {query}{metadata_context}"
        messages.append(HumanMessage(content=user_message))

        try:
            # Get response from LLM
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Parse JSON response
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                # If not valid JSON, try to extract it
                # Sometimes LLMs wrap JSON in markdown code blocks
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    result = json.loads(response_text[json_start:json_end].strip())
                    return result
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    result = json.loads(response_text[json_start:json_end].strip())
                    return result
                else:
                    return {
                        "status": "error",
                        "error": f"Invalid JSON response from LLM: {response_text[:200]}"
                    }

        except Exception as e:
            return {
                "status": "error",
                "error": f"LLM error: {str(e)}"
            }

    async def handle_error(
        self,
        original_query: str,
        failed_sql: str,
        error_message: str,
        cached_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle SQL execution errors and attempt to generate corrected SQL.

        Args:
            original_query: Original natural language query
            failed_sql: SQL that failed to execute
            error_message: Error message from database
            cached_metadata: Available metadata

        Returns:
            Response dict with corrected SQL or error
        """
        messages = [SystemMessage(content=self.system_prompt)]

        metadata_context = ""
        if cached_metadata:
            metadata_context = f"\n\nAvailable metadata:\n{json.dumps(cached_metadata, indent=2)}"

        error_context = f"""The following SQL query failed:

Original query: {original_query}

Failed SQL:
{failed_sql}

Error message:
{error_message}

{metadata_context}

Please analyze the error and generate a corrected SQL query. If you need more metadata to fix the error, request it.
"""

        messages.append(HumanMessage(content=error_context))

        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Parse JSON response
            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError:
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    result = json.loads(response_text[json_start:json_end].strip())
                    return result
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    result = json.loads(response_text[json_start:json_end].strip())
                    return result
                else:
                    return {
                        "status": "error",
                        "error": f"Invalid JSON response from LLM: {response_text[:200]}"
                    }

        except Exception as e:
            return {
                "status": "error",
                "error": f"LLM error while handling error: {str(e)}"
            }
