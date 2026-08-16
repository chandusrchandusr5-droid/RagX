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
        Calls Ollama if available, otherwise performs query-aware structured synthesis from retrieved context.
        """
        context_str = "\n\n".join(
            [f"[Source: {c['document_name']}, Page {c['page_number']}]\n{c['text']}" for c in context_chunks]
        )

        prompt = f"""You are a helpful and concise AI assistant. Answer the user's question accurately and concisely based ONLY on the provided context below.

CRITICAL INSTRUCTIONS:
1. Answer ONLY what the user explicitly asked in the Question.
2. Use ONLY facts directly stated in the Context below. Do NOT assume, extrapolate, or invent information.
3. If the question asks about a specific subject, field, item, or score, return ONLY that specific item. Do NOT list unrelated subjects, rows, or document summaries unless explicitly asked.
4. If the requested information is not present in the context, clearly state "The requested information could not be found in the provided document context."
5. Preserve exact numbers, percentages, and marks as stated in the source text.
6. Keep the response concise when the question is narrow.

Context:
{context_str}

Question: {question}

Answer clearly, concisely, and specifically based strictly on the context above:"""

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
                    res_text = res_json.get("response", "").strip()
                    if res_text:
                        return res_text
            except Exception as e:
                logger.warning(f"Ollama local service call failed or timed out ({e}). Falling back to query-aware internal context synthesizer.")

        # Fallback Query-Aware Context Synthesis Engine
        if not context_chunks:
            return "The requested information could not be found in the provided document context."

        import re
        stopwords = {"who", "is", "a", "an", "the", "what", "where", "when", "why", "how", "are", "was", "were", "of", "in", "for", "to", "on", "with", "at", "by", "from", "about", "obtained", "marks", "score", "total"}
        q_tokens = [w.lower() for w in re.findall(r'\w+', question) if w.lower() not in stopwords]

        # Check if the question is a broad/summary query (e.g. "complete result", "all marks", "summary")
        is_broad_query = any(k in question.lower() for k in ["complete", "all", "entire", "summary", "everything", "full result"])

        # Collect candidate entries across retrieved context chunks
        candidate_entries = []
        for chunk_obj in context_chunks:
            chunk_text = chunk_obj["text"]
            
            # Reconstitute vertical PDF table lines into logical entries/records
            raw_lines = [l.strip() for l in chunk_text.splitlines() if l.strip()]
            records = []
            current_rec = []
            
            for line in raw_lines:
                # Flush record on subject code boundaries (e.g. BMATS201, BCHES202)
                if re.match(r'^[A-Z]{2,5}\d{3}', line) and current_rec:
                    records.append(" ".join(current_rec))
                    current_rec = [line]
                else:
                    current_rec.append(line)
            if current_rec:
                records.append(" ".join(current_rec))

            for rec_text in records:
                rec_tokens_set = set(w.lower() for w in re.findall(r'\w+', rec_text))
                matches = sum(1 for t in q_tokens if t in rec_tokens_set)
                if matches > 0:
                    candidate_entries.append({
                        "matches": matches,
                        "text": rec_text,
                        "doc_name": chunk_obj["document_name"],
                        "page_number": chunk_obj["page_number"]
                    })

        if not candidate_entries:
            return "The requested information could not be found in the provided document context."

        # Sort candidates by query token match count descending
        candidate_entries.sort(key=lambda x: x["matches"], reverse=True)
        top_match_count = candidate_entries[0]["matches"]

        if top_match_count == 0:
            return "The requested information could not be found in the provided document context."

        # Filter entries with top match count
        top_entries = [e for e in candidate_entries if e["matches"] == top_match_count]
        best_entry = top_entries[0]

        if is_broad_query:
            # For broad queries, combine unique top matching entries
            unique_lines = list(dict.fromkeys([e["text"] for e in candidate_entries if e["matches"] >= max(1, top_match_count - 1)]))
            clean_answer = "; ".join(unique_lines)
        else:
            # For specific lookup queries, return only the targeted matching record
            clean_answer = best_entry["text"]

        return f"Based on the retrieved document ({best_entry['doc_name']}, Page {best_entry['page_number']}): {clean_answer}"





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
