from livekit.agents import function_tool, RunContext


class KnowledgeToolsMixin:
    """Tool: search the company knowledge base via the vector store."""

    @function_tool
    async def search_indus_net_knowledge_base(self, context: RunContext, question: str):
        """Search the official Indus Net Knowledge Base for information about the company."""
        self.logger.info(f"Searching knowledge base for: {question}")
        # Await the search to ensure db_results is populated before returning
        await self._vector_db_search(question)
        return self.db_results
