import os
import logging
from typing import List, Tuple
from langchain_community.vectorstores import Redis
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

class VectorDBManager:
    def __init__(self, redis_url: str = None, index_name: str = "slackbot_knowledge"):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.index_name = index_name
        
        # 한국어와 영어를 모두 잘 지원하는 경량 임베딩 모델
        model_name = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        logger.info(f"Initializing VectorDB with model: {model_name}")
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.vectorstore = None

    def add_texts(self, texts: List[str], metadatas: List[dict] = None) -> None:
        if not texts:
            return
        
        try:
            logger.info(f"Adding {len(texts)} chunks to Redis (index: {self.index_name})")
            self.vectorstore = Redis.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas,
                redis_url=self.redis_url,
                index_name=self.index_name
            )
        except Exception as e:
            logger.error(f"Failed to add texts to Redis: {e}")

    def search(self, query: str, top_k: int = 4) -> List[Tuple[str, dict]]:
        if not self.vectorstore:
            try:
                self.vectorstore = Redis.from_existing_index(
                    embedding=self.embeddings,
                    redis_url=self.redis_url,
                    index_name=self.index_name
                )
            except Exception as e:
                logger.warning(f"Could not connect to existing Redis index: {e}")
                return []
        
        try:
            docs = self.vectorstore.similarity_search(query, k=top_k)
            return [(doc.page_content, doc.metadata) for doc in docs]
        except Exception as e:
            logger.error(f"Redis similarity search error: {e}")
            return []
