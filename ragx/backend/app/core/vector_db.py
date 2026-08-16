import chromadb
from chromadb.config import Settings as ChromaSettings
from app.core.config import settings
from sentence_transformers import SentenceTransformer
import logging
import re

logger = logging.getLogger("ragx.vector_db")

DEFAULT_STOPWORDS = {
    "who", "is", "a", "an", "the", "what", "where", "when", "why", "how", 
    "are", "was", "were", "of", "in", "for", "to", "on", "with", "at", 
    "by", "from", "about", "regarding", "tell", "me", "show", "give", "list", "does", "do"
}

class VectorDBManager:
    def __init__(self):
        logger.info(f"Initializing ChromaDB client at {settings.CHROMA_DIR}")
        self.client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        self.collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    def get_embedding(self, text: str) -> list[float]:
        return self.embedding_model.encode(text).tolist()

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        return self.embedding_model.encode(texts).tolist()

    def add_chunks(self, ids: list[str], documents: list[str], metadatas: list[dict]):
        if not ids:
            return
        embeddings = self.get_embeddings(documents)
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )

    @staticmethod
    def _compute_hybrid_score(query_text: str, chunk_text: str, vector_similarity: float) -> float:
        """
        Computes case-insensitive continuous hybrid similarity combining vector cosine similarity
        and case-normalized lexical entity overlap.
        Preserves original document content completely while guaranteeing precise source attribution.
        """
        q_tokens = [
            w.lower() for w in re.findall(r'\w+', query_text)
            if w.lower() not in DEFAULT_STOPWORDS and len(w) > 1
        ]
        
        if not q_tokens:
            return vector_similarity

        c_tokens_set = set(w.lower() for w in re.findall(r'\w+', chunk_text))
        matched = [t for t in q_tokens if t in c_tokens_set]
        lexical_ratio = len(matched) / len(q_tokens) if q_tokens else 0.0

        # Exact contiguous phrase match check (case-insensitive)
        phrase = " ".join(q_tokens)
        has_phrase_match = bool(re.search(r'\b' + re.escape(phrase) + r'\b', chunk_text.lower())) if len(q_tokens) > 1 else False

        if has_phrase_match:
            lexical_ratio = max(lexical_ratio, 0.95)

        # Smooth continuous hybrid score combining vector similarity and lexical match
        hybrid_sim = round(0.50 * vector_similarity + 0.50 * lexical_ratio, 4)
        return hybrid_sim


    def query_similar(self, query_text: str, top_k: int = None, min_similarity: float = 0.35) -> list[dict]:
        if top_k is None:
            top_k = settings.TOP_K_RETRIEVAL

        # 1. Vector Search Query
        query_embedding = self.get_embedding(query_text)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        candidate_chunks = {}

        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]

            for doc, meta, dist in zip(docs, metas, dists):
                v_sim = round(max(0.0, 1.0 - dist), 4)
                h_sim = self._compute_hybrid_score(query_text, doc, v_sim)
                c_id = meta.get("chunk_id", f"chunk_{len(candidate_chunks)}")
                
                candidate_chunks[c_id] = {
                    "text": doc,
                    "document_name": meta.get("document_name", "Unknown"),
                    "page_number": meta.get("page_number", 1),
                    "chunk_id": c_id,
                    "similarity_score": h_sim
                }

        # 2. Case-Insensitive Full KB Scan for entity/phrase query candidates
        try:
            all_db = self.get_all_chunks()
            if all_db and all_db.get("documents"):
                all_docs = all_db["documents"]
                all_metas = all_db["metadatas"]
                
                for a_doc, a_meta in zip(all_docs, all_metas):
                    c_id = a_meta.get("chunk_id", "")
                    if c_id not in candidate_chunks:
                        h_sim = self._compute_hybrid_score(query_text, a_doc, 0.0)
                        if h_sim >= min_similarity:
                            candidate_chunks[c_id] = {
                                "text": a_doc,
                                "document_name": a_meta.get("document_name", "Unknown"),
                                "page_number": a_meta.get("page_number", 1),
                                "chunk_id": c_id,
                                "similarity_score": h_sim
                            }
        except Exception as e:
            logger.warning(f"Full-KB lexical scan fallback warning: {e}")

        # 3. Filter & Sort by Hybrid Similarity Score
        filtered = [c for c in candidate_chunks.values() if c["similarity_score"] >= min_similarity]
        sorted_chunks = sorted(filtered, key=lambda x: x["similarity_score"], reverse=True)

        return sorted_chunks[:top_k]

    def get_all_chunks(self) -> dict:
        results = self.collection.get(include=["documents", "metadatas", "embeddings"])
        return results

    def delete_document_chunks_by_id(self, document_id: str) -> int:
        """
        Deletes all vector chunks from ChromaDB collection matching document_id (or fallback document_name).
        Returns the count of deleted chunks.
        """
        try:
            results = self.collection.get(where={"document_id": document_id})
            if not results or not results.get("ids"):
                results = self.collection.get(where={"document_name": document_id})
                if not results or not results.get("ids"):
                    return 0

            chunk_ids = results["ids"]
            if chunk_ids:
                self.collection.delete(ids=chunk_ids)
                logger.info(f"Deleted {len(chunk_ids)} vector chunks for document_id '{document_id}' from ChromaDB.")
            return len(chunk_ids)
        except Exception as e:
            logger.error(f"Error deleting vector chunks for document_id '{document_id}': {e}")
            return 0

    def delete_document_chunks(self, document_name: str) -> int:
        return self.delete_document_chunks_by_id(document_name)


    def reset_collection(self):
        self.client.delete_collection(name=settings.COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )


vector_db = VectorDBManager()
