"""
Improved SQL Agent using LangChain's SQL toolkit with schema persistence.
This version uses LangChain's built-in SQLDatabase wrapper and agent tools.
"""

from typing import Dict, Any, Optional
from langchain_ollama import ChatOllama
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain.agents import AgentExecutor
from langchain.agents.agent_types import AgentType
from sqlalchemy import create_engine, MetaData
from sqlalchemy.pool import NullPool
import json


class ImprovedSQLAgent:
    """
    SQL generation agent using LangChain's SQL toolkit.
    Uses SQLDatabase wrapper to automatically handle schema introspection and caching.
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
            temperature=0.1,
        )

        # Store database connections per database_id
        self.db_connections: Dict[str, SQLDatabase] = {}
        self.agents: Dict[str, AgentExecutor] = {}

    def _get_or_create_db_connection(
        self,
        database_id: str,
        connection_string: str,
        schema: Optional[str] = None
    ) -> SQLDatabase:
        """
        Get or create a SQLDatabase connection with schema caching.

        Args:
            database_id: Unique identifier for the database
            connection_string: SQLAlchemy connection string
            schema: Optional schema to focus on (for PostgreSQL)

        Returns:
            SQLDatabase instance with cached schema
        """
        if database_id in self.db_connections:
            return self.db_connections[database_id]

        # Create SQLAlchemy engine with connection pooling disabled
        # (since we're connecting to user databases on-demand)
        engine = create_engine(
            connection_string,
            poolclass=NullPool,
            echo=False
        )

        # Create LangChain SQLDatabase wrapper
        # This automatically handles schema introspection and caching
        db = SQLDatabase(
            engine=engine,
            schema=schema,
            include_tables=None,  # Include all tables
            sample_rows_in_table_info=3,  # Include sample rows for context
            max_string_length=300
        )

        # Cache the connection
        self.db_connections[database_id] = db

        return db

    def _get_or_create_agent(
        self,
        database_id: str,
        db: SQLDatabase
    ) -> AgentExecutor:
        """
        Get or create a SQL agent for a specific database.

        Args:
            database_id: Unique identifier for the database
            db: SQLDatabase instance

        Returns:
            AgentExecutor configured for SQL operations
        """
        if database_id in self.agents:
            return self.agents[database_id]

        # Create SQL agent using LangChain's toolkit
        # This provides tools for:
        # - Querying the database schema
        # - Getting table information
        # - Running SQL queries (read-only)
        # - Checking query correctness
        agent = create_sql_agent(
            llm=self.llm,
            db=db,
            agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5,
            max_execution_time=30,
            prefix="""You are an agent designed to interact with a SQL database.
Given an input question, create a syntactically correct SQL query to run, then look at the results of the query and return the answer.
Unless the user specifies a specific number of examples they wish to obtain, always limit your query to at most 100 results.
You can order the results by a relevant column to return the most interesting examples in the database.
Never query for all the columns from a specific table, only ask for the relevant columns given the question.
You have access to tools for interacting with the database.
Only use the given tools. Only use the information returned by the tools to construct your final answer.

IMPORTANT: DO NOT execute any queries that would modify the database (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, GRANT, REVOKE).
Only execute SELECT queries.

If you get an error, analyze it carefully and try to fix your query.
""",
            format_instructions="""Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of the available tools
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the SQL query that answers the question, along with a brief explanation
""",
        )

        # Cache the agent
        self.agents[database_id] = agent

        return agent

    async def process_query(
        self,
        query: str,
        database_id: str,
        connection_string: str,
        schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query using LangChain's SQL toolkit.

        The SQLDatabase wrapper automatically:
        - Caches the database schema
        - Provides tools to the agent for introspection
        - Handles read-only query execution

        Args:
            query: Natural language query
            database_id: Database identifier for caching
            connection_string: SQLAlchemy connection string
            schema: Optional schema name (for PostgreSQL)

        Returns:
            Response dict with status and SQL query
        """
        try:
            # Get or create database connection (schema is cached here)
            db = self._get_or_create_db_connection(database_id, connection_string, schema)

            # Get or create agent
            agent = self._get_or_create_agent(database_id, db)

            # Run the agent
            result = await agent.ainvoke({"input": query})

            # Extract the SQL query and explanation from the agent's output
            output = result.get("output", "")

            # Parse the output to extract SQL
            # The agent typically returns the SQL in its final answer
            return {
                "status": "ready",
                "sql_response": {
                    "sql": self._extract_sql(output),
                    "explanation": output,
                    "confidence": "high"
                }
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Agent error: {str(e)}"
            }

    def _extract_sql(self, agent_output: str) -> str:
        """
        Extract SQL query from agent output.

        Args:
            agent_output: The agent's final answer

        Returns:
            Extracted SQL query
        """
        # Try to find SQL query in the output
        # The agent usually includes it in code blocks or after "Final Answer:"

        if "```sql" in agent_output:
            start = agent_output.find("```sql") + 6
            end = agent_output.find("```", start)
            return agent_output[start:end].strip()
        elif "SELECT" in agent_output.upper():
            # Find the SELECT statement
            lines = agent_output.split('\n')
            sql_lines = []
            in_sql = False

            for line in lines:
                if 'SELECT' in line.upper():
                    in_sql = True
                if in_sql:
                    sql_lines.append(line)
                    if ';' in line:
                        break

            return '\n'.join(sql_lines).strip()

        return agent_output

    def clear_cache(self, database_id: Optional[str] = None):
        """
        Clear cached database connections and agents.

        Args:
            database_id: If provided, clear only this database. Otherwise, clear all.
        """
        if database_id:
            if database_id in self.db_connections:
                self.db_connections[database_id].engine.dispose()
                del self.db_connections[database_id]
            if database_id in self.agents:
                del self.agents[database_id]
        else:
            # Clear all
            for db in self.db_connections.values():
                db.engine.dispose()
            self.db_connections.clear()
            self.agents.clear()

    def get_schema_info(self, database_id: str) -> Dict[str, Any]:
        """
        Get cached schema information for a database.

        Args:
            database_id: Database identifier

        Returns:
            Schema information including tables and their details
        """
        if database_id not in self.db_connections:
            return {"error": "Database not connected"}

        db = self.db_connections[database_id]

        return {
            "dialect": db.dialect,
            "tables": db.get_usable_table_names(),
            "table_info": db.get_table_info(),
        }

    async def handle_error(
        self,
        original_query: str,
        failed_sql: str,
        error_message: str,
        database_id: str,
        connection_string: str,
        schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle SQL execution errors by asking the agent to fix the query.

        Args:
            original_query: Original natural language query
            failed_sql: SQL that failed to execute
            error_message: Error message from database
            database_id: Database identifier
            connection_string: SQLAlchemy connection string
            schema: Optional schema name

        Returns:
            Response dict with corrected SQL
        """
        error_prompt = f"""The following SQL query failed with an error:

Original question: {original_query}

Failed SQL:
{failed_sql}

Error message:
{error_message}

Please analyze the error and generate a corrected SQL query."""

        return await self.process_query(
            error_prompt,
            database_id,
            connection_string,
            schema
        )
