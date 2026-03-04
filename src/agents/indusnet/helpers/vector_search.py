import json
from typing import Optional

from src.agents.indusnet.constants import SKIPPED_METADATA_KEYS


class VectorSearchHelperMixin:
    """Helpers for querying the vector store and formatting results as Markdown."""

    def _format_metadata_value(self, key: str, val: str) -> Optional[str]:
        """Format a single metadata value, handling JSON strings."""
        human_key = key.replace("_", " ").title()

        # Check if it's a JSON string (list or dict)
        if isinstance(val, str) and val.strip().startswith(("[", "{")):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    formatted_val = ", ".join(map(str, parsed))
                elif isinstance(parsed, dict):
                    formatted_val = ", ".join(
                        [
                            f"{k.replace('_', ' ').title()}: {v}"
                            for k, v in parsed.items()
                        ]
                    )
                else:
                    formatted_val = str(parsed)
                return f"**{human_key}:** {formatted_val}"
            except json.JSONDecodeError:
                # Fallback for invalid JSON
                return f"**{human_key}:** {val}"

        # Regular value
        return f"**{human_key}:** {val}"

    def _format_metadata(self, metadata: dict) -> list[str]:
        """Extract and format all metadata dynamically."""
        details = []
        for key, val in metadata.items():
            # Skip internal/empty keys
            if not val or key in SKIPPED_METADATA_KEYS:
                continue

            formatted = self._format_metadata_value(key, val)
            if formatted:
                details.append(formatted)

        return details

    async def _vector_db_search(self, query: str) -> str:
        """Search the vector database for relevant information."""
        results = await self.vector_store.search(query, k=self.db_fetch_size)

        formatted_results = []
        for i, doc in enumerate(results):
            content = doc.page_content.strip()
            md_chunk = f"### Result {i + 1}\n\n{content}\n"

            # Format metadata
            details = self._format_metadata(doc.metadata)
            if details:
                md_chunk += "\n" + "\n".join([f"- {d}" for d in details])

            formatted_results.append(md_chunk)

        self.db_results = "\n\n---\n\n".join(formatted_results)
        self.logger.info(f"✅ DB results converted to markdown")
        return self.db_results
