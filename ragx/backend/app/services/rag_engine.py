import uuid
import requests
import logging
from pathlib import Path
from app.core.config import settings
from app.core.vector_db import vector_db

logger = logging.getLogger("ragx.rag_engine")

class RAGEngine:
    @staticmethod
    def chunk_pages(file_name: str, pages: list[dict]) -> list[dict]:
        """
        Splits text into chunks while preserving page numbers and file names.
        """
        chunks = []
        chunk_size = settings.CHUNK_SIZE
        overlap = settings.CHUNK_OVERLAP

        for page in pages:
            page_num = page["page_number"]
            text = page["text"]
            
            if len(text) <= chunk_size:
                chunks.append({
                    "id": f"{file_name}_p{page_num}_{uuid.uuid4().hex[:8]}",
                    "text": text,
                    "document_name": file_name,
                    "page_number": page_num
                })
            else:
                start = 0
                while start < len(text):
                    end = start + chunk_size
                    chunk_text = text[start:end].strip()
                    if chunk_text:
                        chunks.append({
                            "id": f"{file_name}_p{page_num}_{uuid.uuid4().hex[:8]}",
                            "text": chunk_text,
                            "document_name": file_name,
                            "page_number": page_num
                        })
                    start += (chunk_size - overlap)

        return chunks

    @classmethod
    def index_document_chunks(cls, file_name: str, pages: list[dict], document_id: str = None) -> int:
        chunks = cls.chunk_pages(file_name, pages)
        if not chunks:
            return 0

        doc_id = document_id or file_name
        ids = [c["id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {
                "document_id": doc_id,
                "document_name": c["document_name"],
                "page_number": c["page_number"],
                "chunk_id": c["id"]
            }
            for c in chunks
        ]


        vector_db.add_chunks(ids=ids, documents=documents, metadatas=metadatas)
        return len(chunks)

    @staticmethod
    def generate_llm_response(question: str, context_chunks: list[dict]) -> str:
        """
        Calls Ollama if available, otherwise performs structured synthesis from retrieved context.
        """
        context_str = "\n\n".join(
            [f"[Source: {c['document_name']}, Page {c['page_number']}]\n{c['text']}" for c in context_chunks]
        )

        prompt = f"""You are a helpful AI assistant. Answer the user's question accurately based ONLY on the provided context below. 

Context:
{context_str}

Question: {question}

Answer clearly and concisely based strictly on the context above:"""

        # Try local Ollama endpoint first if enabled
        if settings.USE_OLLAMA:
            try:
                response = requests.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    res_json = response.json()
                    return res_json.get("response", "").strip()
            except Exception as e:
                logger.warning(f"Ollama local service call failed or timed out ({e}). Falling back to internal context synthesizer.")

        # Fallback Context Synthesis Engine (Guarantees RAG pipeline works even without running Ollama)
        if not context_chunks:
            return "No relevant information found in the uploaded documents to answer your question."

        # Extract non-stopword query tokens for sentence-level extraction
        import re
        stopwords = {"who", "is", "a", "an", "the", "what", "where", "when", "why", "how", "are", "was", "were", "of", "in", "for", "to", "on", "with", "at", "by", "from", "about"}
        q_tokens = [w.lower() for w in re.findall(r'\w+', question) if w.lower() not in stopwords]

        best_chunk_obj = context_chunks[0]
        best_text = best_chunk_obj["text"]
        
        # Split text into lines/sentences to find best sentence match while preserving original casing
        lines = [line.strip() for line in re.split(r'[\n.]', best_text) if line.strip()]
        best_line = best_text
        best_count = 0

        for line in lines:
            line_tokens_set = set(w.lower() for w in re.findall(r'\w+', line))
            matches = sum(1 for t in q_tokens if t in line_tokens_set)
            if matches > best_count:
                best_count = matches
                best_line = line

        # Ensure section headers ending with ':' or short isolated titles do not truncate factual body text
        if best_line.endswith(":") or len(best_line.split()) < 5:
            clean_answer = " ".join(best_text.split())
        else:
            clean_answer = best_line.strip()

        return f"Based on the retrieved document ({best_chunk_obj['document_name']}, Page {best_chunk_obj['page_number']}): {clean_answer}"



    @classmethod
    def query(cls, question: str, top_k: int = None) -> dict:
        retrieved_chunks = vector_db.query_similar(question, top_k=top_k)
        answer = cls.generate_llm_response(question, retrieved_chunks)

        return {
            "question": question,
            "answer": answer,
            "retrieved_evidence": retrieved_chunks,
            "total_evidence_chunks": len(retrieved_chunks)
        }

rag_engine = RAGEngine()
