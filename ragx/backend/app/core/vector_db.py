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

_shared_embedding_model = None
_TEXT_EMBEDDING_CACHE = {}

def get_shared_embedding_model():
    global _shared_embedding_model
    if _shared_embedding_model is None:
        logger.info(f"Lazy-loading SentenceTransformer model: {settings.EMBEDDING_MODEL_NAME}")
        from sentence_transformers import SentenceTransformer
        _shared_embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _shared_embedding_model

class VectorDBManager:
    def __init__(self):
        logger.info(f"Initializing ChromaDB client at {settings.CHROMA_DIR}")
        self.client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        self.collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

    @property
    def embedding_model(self):
        return get_shared_embedding_model()


    def get_embedding(self, text: str) -> list[float]:
        if text in _TEXT_EMBEDDING_CACHE:
            return _TEXT_EMBEDDING_CACHE[text]
        emb = self.embedding_model.encode(text).tolist()
        if len(_TEXT_EMBEDDING_CACHE) > 2000:
            _TEXT_EMBEDDING_CACHE.clear()
        _TEXT_EMBEDDING_CACHE[text] = emb
        return emb

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
    def _compute_hybrid_score(query_text: str, chunk_text: str, vector_similarity: float, document_name: str = "") -> float:
        """
        Computes case-insensitive continuous hybrid similarity combining vector cosine similarity,
        exact token/entity overlap, and document title matching.
        Guarantees that strong vector matches are never penalized by query length variations.
        """
        q_tokens = [
            w.lower() for w in re.findall(r'\w+', query_text)
            if w.lower() not in DEFAULT_STOPWORDS
        ]
        
        if not q_tokens:
            return vector_similarity

        c_tokens_set = set(w.lower() for w in re.findall(r'\w+', chunk_text))
        c_text_lower = chunk_text.lower()
        
        ACRONYM_MAP = {
            "usn": ["university seat number", "seat number", "usn"],
            "vtu": ["visvesvaraya technological university", "vtu"],
            "cgpa": ["cumulative grade point average", "cgpa"],
            "sgpa": ["semester grade point average", "sgpa"],
            "gpa": ["grade point average", "gpa"]
        }

        matched = []
        for t in q_tokens:
            if t in c_tokens_set:
                matched.append(t)
            elif t in ACRONYM_MAP and any(exp in c_text_lower for exp in ACRONYM_MAP[t]):
                matched.append(t)

        lexical_ratio = len(matched) / len(q_tokens) if q_tokens else 0.0

        # Exact contiguous phrase match check (case-insensitive)
        phrase = " ".join(q_tokens)
        has_phrase_match = bool(re.search(r'\b' + re.escape(phrase) + r'\b', chunk_text.lower())) if len(q_tokens) > 1 else False

        if has_phrase_match:
            lexical_ratio = max(lexical_ratio, 0.95)

        # Check if query specifically mentions terms in document_name
        if document_name:
            doc_name_clean = re.sub(r'[^a-zA-Z0-9]', ' ', document_name).lower()
            doc_tokens = [w for w in doc_name_clean.split() if w not in DEFAULT_STOPWORDS and len(w) > 1]
            if doc_tokens:
                doc_match_count = sum(1 for t in doc_tokens if t in q_tokens)
                doc_ratio = doc_match_count / len(doc_tokens)
                if doc_ratio >= 0.50:
                    lexical_ratio = max(lexical_ratio, 0.85)

        # Smooth continuous hybrid score that boosts vector similarity without penalizing strong vector matches
        hybrid_sim = round(max(vector_similarity, 0.50 * vector_similarity + 0.50 * lexical_ratio), 4)
        return hybrid_sim


    def query_similar(self, query_text: str, owner_id: str = None, top_k: int = None, min_similarity: float = 0.20) -> list[dict]:
        if top_k is None:
            top_k = settings.TOP_K_RETRIEVAL

        if owner_id and owner_id not in ("default_workspace", "legacy_dev_owner"):
            allowed_owners = {owner_id}
        else:
            allowed_owners = {"default_workspace", "legacy_dev_owner"}

        # 1. Vector Search Query with owner_id filter
        query_embedding = self.get_embedding(query_text)
        where_clause = {"owner_id": {"$in": list(allowed_owners)}}
        
        # Retrieve extra candidate slots to prevent HNSW top_k truncation
        n_fetch = max(top_k * 5, 25)

        query_kwargs = {
            "query_embeddings": [query_embedding],
            "n_results": n_fetch,
            "include": ["documents", "metadatas", "distances"]
        }
        if where_clause:
            query_kwargs["where"] = where_clause

        try:
            results = self.collection.query(**query_kwargs)
        except Exception as e:
            logger.warning(f"ChromaDB query with where_clause failed: {e}. Retrying without metadata filter.")
            query_kwargs.pop("where", None)
            results = self.collection.query(**query_kwargs)

        candidate_chunks = {}

        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]

            for doc, meta, dist in zip(docs, metas, dists):
                m_owner = meta.get("owner_id", "default_workspace")
                if m_owner not in allowed_owners:
                    continue

                v_sim = round(max(0.0, 1.0 - dist), 4)
                doc_name = meta.get("document_name", "Unknown")
                h_sim = self._compute_hybrid_score(query_text, doc, v_sim, document_name=doc_name)
                c_id = meta.get("chunk_id", f"chunk_{len(candidate_chunks)}")
                
                candidate_chunks[c_id] = {
                    "text": doc,
                    "document_name": doc_name,
                    "page_number": meta.get("page_number", 1),
                    "chunk_id": c_id,
                    "similarity_score": h_sim,
                    "owner_id": m_owner
                }

        # 2. Case-Insensitive Full KB Scan for entity/phrase query candidates (run only if vector search returned < top_k or low max score)
        max_v_score = max([c["similarity_score"] for c in candidate_chunks.values()]) if candidate_chunks else 0.0
        if len(candidate_chunks) < top_k or max_v_score < 0.40:
            try:
                all_db = self.get_all_chunks(owner_id=owner_id, include_embeddings=False)
                if all_db and all_db.get("documents"):
                    all_docs = all_db["documents"]
                    all_metas = all_db["metadatas"]
                    
                    for a_doc, a_meta in zip(all_docs, all_metas):
                        m_owner = a_meta.get("owner_id", "default_workspace")
                        if m_owner not in allowed_owners:
                            continue

                        c_id = a_meta.get("chunk_id", "")
                        if c_id not in candidate_chunks:
                            doc_name = a_meta.get("document_name", "Unknown")
                            h_sim = self._compute_hybrid_score(query_text, a_doc, 0.0, document_name=doc_name)
                            if h_sim >= min_similarity:
                                candidate_chunks[c_id] = {
                                    "text": a_doc,
                                    "document_name": doc_name,
                                    "page_number": a_meta.get("page_number", 1),
                                    "chunk_id": c_id,
                                    "similarity_score": h_sim,
                                    "owner_id": m_owner
                                }
            except Exception as e:
                logger.warning(f"Full-KB lexical scan fallback warning: {e}")

        # 3. Filter & Sort by Hybrid Similarity Score
        filtered = [c for c in candidate_chunks.values() if c["similarity_score"] >= min_similarity]
        sorted_chunks = sorted(filtered, key=lambda x: x["similarity_score"], reverse=True)

        return sorted_chunks[:top_k]

    def get_all_chunks(self, owner_id: str = None, include_embeddings: bool = False) -> dict:
        inc = ["documents", "metadatas", "embeddings"] if include_embeddings else ["documents", "metadatas"]
        try:
            results = self.collection.get(include=inc)
        except Exception:
            results = self.collection.get(include=["documents", "metadatas"])

        if results and results.get("metadatas"):
            if owner_id and owner_id not in ("default_workspace", "legacy_dev_owner"):
                allowed_owners = {owner_id}
            else:
                allowed_owners = {"default_workspace", "legacy_dev_owner"}
            docs, metas, ids, embs = [], [], [], []
            raw_embs = results.get("embeddings")
            for i, (doc, meta, cid) in enumerate(zip(results["documents"], results["metadatas"], results["ids"])):
                m_owner = meta.get("owner_id", "default_workspace")
                if m_owner in allowed_owners:
                    docs.append(doc)
                    metas.append(meta)
                    ids.append(cid)
                    if raw_embs is not None and len(raw_embs) > i:
                        embs.append(raw_embs[i])
            results = {"documents": docs, "metadatas": metas, "ids": ids, "embeddings": embs if embs else None}
        return results

    def delete_document_chunks_by_id(self, document_id: str, owner_id: str = None) -> int:
        """
        Deletes all vector chunks from ChromaDB collection matching document_id (or fallback document_name).
        Returns the count of deleted chunks.
        """
        try:
            where_clause = {"document_id": document_id}
            results = self.collection.get(where=where_clause)
            if not results or not results.get("ids"):
                results = self.collection.get(where={"document_name": document_id})
                if not results or not results.get("ids"):
                    return 0

            chunk_ids = []
            if results and results.get("ids"):
                for cid, meta in zip(results["ids"], results["metadatas"]):
                    m_owner = meta.get("owner_id", "legacy_dev_owner")
                    if owner_id is None or m_owner == owner_id:
                        chunk_ids.append(cid)

            if chunk_ids:
                self.collection.delete(ids=chunk_ids)
                logger.info(f"Deleted {len(chunk_ids)} vector chunks for document_id '{document_id}' (owner '{owner_id}') from ChromaDB.")
            return len(chunk_ids)
        except Exception as e:
            logger.error(f"Error deleting vector chunks for document_id '{document_id}': {e}")
            return 0

    def delete_document_chunks(self, document_name: str, owner_id: str = None) -> int:
        return self.delete_document_chunks_by_id(document_name, owner_id=owner_id)


    def reset_collection(self):
        self.client.delete_collection(name=settings.COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=settings.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )


vector_db = VectorDBManager()
