import logging
import asyncio
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from src.core.config import settings

logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        # Knowledge base lives in the VAANI Library (knowledge/rich_chroma_db),
        # built from the intglobal.com scrape. A copy of the older, smaller base
        # added by the original dev is preserved at
        # src/services/vectordb/chroma_db_ORIGINAL.
        self.vectorstore = Chroma(
            persist_directory=settings.KNOWLEDGE_DIR,
            embedding_function=self.embeddings,
            collection_name="company_knowledge"
        )
        # Navigation index — one record per website page (built by ScrapNinja's
        # scrapninja/load/build_page_index.py). Used by the navigate_to_page tool
        # to resolve a free-text page request to a URL.
        self.page_index = Chroma(
            persist_directory=settings.KNOWLEDGE_DIR,
            embedding_function=self.embeddings,
            collection_name="page_index"
        )

    async def search(self, query: str, k: int = 5):
        # Run synchronous Chroma search in a thread
        results = await asyncio.to_thread(
            self.vectorstore.similarity_search,
            query=query,
            k=k
        )
        return results

    async def search_pages(self, query: str, k: int = 10):
        """Similarity search over the page navigation index.

        Returns a list of (Document, distance) tuples (lower distance = closer);
        each Document.metadata carries url, path, title, section, nav_priority.
        """
        return await asyncio.to_thread(
            self.page_index.similarity_search_with_score,
            query,
            k=k,
        )


# Remove the global instance to avoid issues during Docker build when API keys are not present
# vector_store = VectorStoreService()
