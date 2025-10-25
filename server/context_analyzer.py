"""
Context Analyzer for extracting structured knowledge from conversations.
Uses LLM to analyze successful SQL conversations and extract reusable context.
"""

from typing import Dict, Any, List, Optional
from llm_interface import LLMInterface, LLMError
import logging
import json

logger = logging.getLogger(__name__)


class ContextAnalyzer:
    """
    Analyzes conversations to extract structured context for future queries.
    Context includes table relationships, typecast requirements, and business rules.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the context analyzer.

        Args:
            api_key: OpenAI API key
            model: OpenAI model to use
        """
        self.llm = LLMInterface(api_key=api_key, model=model)

        self.analysis_prompt = """You are a database context analyzer. Your job is to analyze a successful SQL conversation and extract reusable knowledge.

Given a conversation between a user and a SQL assistant, extract the following structured information:

1. **Tables Used**: List all tables that were referenced in the conversation
2. **Relationships**: Identify foreign key relationships discovered during the conversation
3. **Column Typecast Hints**: Note any columns that required type casting or special handling
4. **Business Context**: Extract business rules or domain knowledge mentioned by the user
5. **SQL Patterns**: Common query patterns that were useful

CRITICAL: Your response MUST be valid JSON matching this exact schema:
{
    "tables_used": ["table1", "table2"],
    "relationships": [
        {
            "from_table": "orders",
            "from_column": "user_id",
            "to_table": "users",
            "to_column": "id",
            "type": "foreign_key"
        }
    ],
    "column_typecast_hints": [
        {
            "table": "orders",
            "column": "created_at",
            "hint": "Cast to date for date-only comparisons",
            "example": "created_at::date"
        }
    ],
    "business_context": [
        "Active users are defined as users who logged in within the last 30 days",
        "Premium tier users have tier='premium' in the users table"
    ],
    "sql_patterns": [
        {
            "pattern": "Recent activity filtering",
            "example": "WHERE created_at >= NOW() - INTERVAL '30 days'"
        }
    ]
}

RULES:
- Only include information that was explicitly discussed or used in the conversation
- Be concise but specific
- If a section has no relevant information, use an empty array []
- Ensure all JSON is properly formatted
- Focus on reusable knowledge that would help future queries"""

    def analyze_conversation(
        self,
        conversation_messages: List[Dict[str, str]],
        user_notes: Optional[str] = None,
        metadata_used: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a conversation and extract structured context.

        Args:
            conversation_messages: List of conversation messages (role, content)
            user_notes: Optional additional context provided by the user
            metadata_used: Metadata that was used during the conversation

        Returns:
            Structured context dictionary

        Raises:
            LLMError: If LLM fails to analyze the conversation
        """
        try:
            logger.info("Starting conversation context analysis")

            # Build the conversation summary for analysis
            conversation_summary = self._format_conversation(conversation_messages)

            # Build the analysis request
            analysis_request = f"""Analyze this SQL conversation and extract structured context:

CONVERSATION:
{conversation_summary}"""

            if user_notes:
                analysis_request += f"""

USER NOTES:
{user_notes}"""

            if metadata_used:
                analysis_request += f"""

METADATA AVAILABLE DURING CONVERSATION:
{json.dumps(metadata_used, indent=2)}"""

            analysis_request += """

Provide your analysis as a JSON object following the exact schema specified in the system prompt."""

            # Call LLM for analysis
            messages = [
                {"role": "system", "content": self.analysis_prompt},
                {"role": "user", "content": analysis_request}
            ]

            response = self.llm.chat_completion(
                messages=messages,
                temperature=0.1,  # Low temperature for consistent structured output
            )

            # Parse the response
            content = response.get("content", "")

            # Try to extract JSON from the response
            context_data = self._parse_json_response(content)

            # Validate the structure
            context_data = self._validate_context_structure(context_data)

            logger.info(f"Successfully analyzed conversation - extracted {len(context_data.get('tables_used', []))} tables, "
                       f"{len(context_data.get('relationships', []))} relationships, "
                       f"{len(context_data.get('business_context', []))} business rules")

            return context_data

        except LLMError as e:
            logger.error(f"LLM error during context analysis: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during context analysis: {e}")
            # Return minimal valid context instead of failing
            return self._get_empty_context()

    def generate_title(
        self,
        conversation_messages: List[Dict[str, str]],
        max_words: int = 5,
    ) -> str:
        """
        Generate a concise title for a conversation.

        Args:
            conversation_messages: List of conversation messages (role, content)
            max_words: Maximum number of words in the title

        Returns:
            Generated title string

        Raises:
            LLMError: If LLM fails to generate title
        """
        try:
            logger.info("Generating conversation title")

            # Get the first user message (the original query)
            user_messages = [msg for msg in conversation_messages if msg.get("role") == "user"]

            if not user_messages:
                return "Untitled Conversation"

            first_query = user_messages[0].get("content", "")

            # Build title generation prompt
            title_prompt = f"""Generate a concise, descriptive title for this SQL query conversation.

ORIGINAL QUERY:
{first_query}

RULES:
- Maximum {max_words} words
- Be specific about what data is being queried
- Use action verbs (e.g., "Find", "List", "Count", "Analyze")
- No quotes or special formatting
- Title case

RESPOND WITH ONLY THE TITLE, NOTHING ELSE."""

            messages = [
                {"role": "user", "content": title_prompt}
            ]

            response = self.llm.chat_completion(
                messages=messages,
                temperature=0.3,  # Some creativity but still focused
                max_tokens=50,  # Short response
            )

            title = response.get("content", "").strip()

            # Clean up the title
            title = title.strip('"\'')  # Remove quotes
            title = title[:100]  # Max 100 chars

            if not title or len(title) < 3:
                title = "Untitled Conversation"

            logger.info(f"Generated title: {title}")
            return title

        except Exception as e:
            logger.error(f"Error generating title: {e}")
            return "Untitled Conversation"

    def _format_conversation(self, messages: List[Dict[str, str]]) -> str:
        """Format conversation messages for analysis."""
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")
        return "\n\n".join(formatted)

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling various formats."""
        # Try to find JSON in the response
        content = content.strip()

        # If wrapped in code blocks, extract
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Content was: {content[:500]}")
            return self._get_empty_context()

    def _validate_context_structure(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure context has the expected structure."""
        template = self._get_empty_context()

        # Merge with template to ensure all keys exist
        for key in template:
            if key not in context:
                context[key] = template[key]

        return context

    def _get_empty_context(self) -> Dict[str, Any]:
        """Get an empty context structure."""
        return {
            "tables_used": [],
            "relationships": [],
            "column_typecast_hints": [],
            "business_context": [],
            "sql_patterns": []
        }
