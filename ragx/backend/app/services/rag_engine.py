import uuid
import math
import re
import requests
import logging
from collections import Counter
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
    def index_document_chunks(cls, file_name: str, pages: list[dict], document_id: str = None, owner_id: str = "legacy_dev_owner") -> int:
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
                "chunk_id": c["id"],
                "owner_id": owner_id
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

        # Generic vector embedding semantic relevance pre-check
        try:
            from app.core.vector_db import get_shared_embedding_model
            import numpy as np
            model = get_shared_embedding_model()
            q_emb = model.encode(question, convert_to_numpy=True)
            q_norm = q_emb / (np.linalg.norm(q_emb) + 1e-9)

            c_texts = [c.get("text", "") for c in context_chunks]
            c_embs = model.encode(c_texts, convert_to_numpy=True)
            c_norms = c_embs / (np.linalg.norm(c_embs, axis=1, keepdims=True) + 1e-9)

            sims = np.dot(c_norms, q_norm)
            max_sim = float(np.max(sims)) if len(sims) > 0 else 0.0

            if max_sim < 0.28:
                return "The requested information could not be found in the provided document context."
        except Exception as e:
            logger.warning(f"Semantic relevance check warning: {e}")

        import re
        ENGLISH_STOPWORDS = {
            "a", "an", "the", "and", "or", "but", "if", "because", "as", "until", "while",
            "of", "at", "by", "for", "with", "about", "against", "between", "into", "through",
            "during", "before", "after", "above", "below", "to", "from", "up", "down", "in",
            "out", "on", "off", "over", "under", "again", "further", "then", "once", "here",
            "there", "when", "where", "why", "how", "all", "any", "both", "each", "few",
            "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own",
            "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don",
            "should", "now", "is", "am", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "having", "do", "does", "did", "doing"
        }
        q_tokens = [w.lower() for w in re.findall(r'\w+', question) if w.lower() not in ENGLISH_STOPWORDS and len(w) > 1]
        if not q_tokens:
            q_tokens = [w.lower() for w in re.findall(r'\w+', question)]

        # Build generic token frequency map across context chunks for IDF (token specificity) weighting
        all_context_text = " ".join([c["text"].lower() for c in context_chunks])
        all_context_tokens = re.findall(r'\w+', all_context_text)
        token_counts = Counter(all_context_tokens)

        # Calculate token weights: rare/specific tokens get higher weight, common words get lower weight
        token_weights = {}
        for t in q_tokens:
            count = token_counts.get(t, 1)
            token_weights[t] = 1.0 / math.log(1 + count)

        max_weight_possible = sum(token_weights.values()) or 1.0

        # Collect candidate entries across retrieved context chunks using generic TF-IDF token specificity scoring
        candidate_entries = []
        for chunk_obj in context_chunks:
            chunk_text = chunk_obj["text"]
            
            # Extract individual lines and sentence blocks generically
            raw_lines = [l.strip() for l in chunk_text.splitlines() if l.strip()]
            records = set(raw_lines)

            # Reconstitute column-aligned tabular records generically
            # Look for alphanumeric record identifiers (e.g. course/item codes)
            record_codes = list(dict.fromkeys(re.findall(r'\b[A-Z]{2,}\d+[A-Z0-9]*\b', chunk_text)))
            if len(record_codes) >= 2:
                for code in record_codes:
                    # Find all lines or segments associated with this item code
                    matching_lines = [l for l in raw_lines if code in l]
                    if matching_lines:
                        records.update(matching_lines)
                    else:
                        # Pair item code with matching title and data lines across the chunk
                        code_parts = [l for l in raw_lines if any(tok in l for tok in [code, code[:4]])]
                        if code_parts:
                            records.add(" ".join(code_parts))
                
                # Also reconstitute 2-line and 3-line combined entries for column-major tabular chunks
                for i in range(len(raw_lines) - 1):
                    records.add(raw_lines[i] + " " + raw_lines[i+1])
                for i in range(len(raw_lines) - 2):
                    records.add(raw_lines[i] + " " + raw_lines[i+1] + " " + raw_lines[i+2])


            # Reconstitute narrative prose paragraphs (only for narrative lines ending with punctuation)
            prose_buf = []
            for line in raw_lines:
                if not re.search(r'\b[A-Z0-9]{5,}\b', line):
                    prose_buf.append(line)
                    if line.endswith(('.', ':', '?', ';')):
                        records.add(" ".join(prose_buf))
                        prose_buf = []
            if prose_buf:
                records.add(" ".join(prose_buf))


            for rec_text in records:
                rec_tokens = set(w.lower() for w in re.findall(r'\w+', rec_text))
                matching_tokens = [t for t in q_tokens if t in rec_tokens]
                if matching_tokens:
                    weighted_coverage = sum(token_weights[t] for t in matching_tokens) / max_weight_possible
                    has_data = 1.0 if re.search(r'\d+', rec_text) else 0.0
                    match_density = len(matching_tokens) / max(len(rec_tokens), 1)
                    score = (4.0 * weighted_coverage) + (1.0 * has_data) + (0.5 * match_density)
                    candidate_entries.append({
                        "matches": len(matching_tokens),
                        "score": score,
                        "text": rec_text,
                        "doc_name": chunk_obj["document_name"],
                        "page_number": chunk_obj["page_number"]
                    })





        if not candidate_entries:
            return "The requested information could not be found in the provided document context."

        # Sort candidates by generic score descending
        candidate_entries.sort(key=lambda x: x["score"], reverse=True)
        best_entry = candidate_entries[0]

        # Determine if query is multi-aspect (complex multi-clause question requiring synthesis across sentences)
        is_multi_aspect = any(punct in question for punct in [",", ";", "?"]) and len(q_tokens) >= 8

        if is_multi_aspect:
            # Combine unique top matching entries across chunks that meet high relevance threshold
            high_cov_entries = [e for e in candidate_entries if e["matches"] >= 2 or e["score"] >= 2.5]
            if not high_cov_entries:
                high_cov_entries = candidate_entries[:3]
            unique_lines = list(dict.fromkeys([e["text"] for e in high_cov_entries]))
            clean_answer = " ".join(unique_lines[:4])
        else:
            clean_answer = best_entry["text"]

        return f"Based on the retrieved document ({best_entry['doc_name']}, Page {best_entry['page_number']}): {clean_answer}"











    @classmethod
    def query(cls, question: str, owner_id: str = None, top_k: int = None) -> dict:
        retrieved_chunks = vector_db.query_similar(question, owner_id=owner_id, top_k=top_k)
        answer = cls.generate_llm_response(question, retrieved_chunks)

        return {
            "question": question,
            "answer": answer,
            "retrieved_evidence": retrieved_chunks,
            "total_evidence_chunks": len(retrieved_chunks)
        }

rag_engine = RAGEngine()
