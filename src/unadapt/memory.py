from datetime import datetime

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings


class SemanticMemory:
    def __init__(self, config):
        self.config = config
        self.enabled = config.memory.enabled

        if not self.enabled:
            self.vector_store = None
            return

        self.embeddings = OpenAIEmbeddings(
            model=config.memory.model,
            base_url=config.memory.base_url,
            api_key=config.memory.api_key,
            check_embedding_ctx_length=False,
        )

        self.vector_store = Chroma(
            collection_name=config.memory.collection_name,
            embedding_function=self.embeddings,
            persist_directory=config.memory.persist_directory,
        )

    def append(
        self,
        category: str,
        content: str,
    ) -> str:
        if not self.enabled:
            return "Memory is disabled in config."

        content = content.strip()

        if not content:
            return "Memory content was empty."

        document = Document(
            page_content=content,
            metadata={
                "category": category,
                "created_at": datetime.now().isoformat(
                    timespec="seconds"
                ),
            },
        )

        self.vector_store.add_documents([document])

        return (
            f"Memory saved successfully "
            f"under category '{category}'."
        )

    def read(
        self,
        query: str,
        limit: int = 5,
    ) -> str:
        if not self.enabled:
            return "Memory is disabled in config."

        query = query.strip()

        if not query:
            return "Memory query was empty."

        # Keep the model from asking for something ridiculous.
        limit = max(1, min(limit, 20))

        results = self.vector_store.similarity_search(
            query,
            k=limit,
        )

        if not results:
            return "No relevant memory found."

        memories = []

        for index, document in enumerate(results, start=1):
            category = document.metadata.get(
                "category",
                "Uncategorized",
            )

            created_at = document.metadata.get(
                "created_at",
                "unknown",
            )

            memories.append(
                f"{index}. [{category}] [{created_at}]\n"
                f"{document.page_content}"
            )

        return "\n\n".join(memories)
