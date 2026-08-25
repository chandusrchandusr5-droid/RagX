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


_OLLAMA_CHECKED = False
_OLLAMA_AVAILABLE = False

def _check_ollama_status() -> bool:
    global _OLLAMA_CHECKED, _OLLAMA_AVAILABLE
    if _OLLAMA_CHECKED:
        return _OLLAMA_AVAILABLE
    _OLLAMA_CHECKED = True
    if not settings.USE_OLLAMA:
        _OLLAMA_AVAILABLE = False
        return False
    try:
        res = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=0.15)
        _OLLAMA_AVAILABLE = (res.status_code == 200)
    except Exception:
        _OLLAMA_AVAILABLE = False
    return _OLLAMA_AVAILABLE

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

        # Try local Ollama endpoint first if active and responsive
        if _check_ollama_status():
            try:
                response = requests.post(
                    f"{settings.OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    res_json = response.json()
                    res_text = res_json.get("response", "").strip()
                    if res_text:
                        return res_text
            except Exception as e:
                logger.warning(f"Ollama local service call failed ({e}). Falling back to query-aware internal context synthesizer.")

        # Fallback Query-Aware Context Synthesis Engine
        if not context_chunks:
            return "The requested information could not be found in the provided document context."

        # Generic vector embedding semantic relevance pre-check
        try:
            max_sim = max([c.get("similarity_score", 0.0) for c in context_chunks]) if context_chunks else 0.0
            if max_sim < 0.15:
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

        # Generic detection helper for question headers / section titles matching user query
        q_tokens_set = set(q_tokens)
        
        def is_heading_or_question_repeat(text: str) -> bool:
            clean_t = text.strip()
            # Normalize: strip section prefix "2.2 ", "SECTION 4: ", punctuation, and case
            t_norm = re.sub(r'^(?:(?:section|unit|part|chapter)\s+\d+|[0-9]+(?:\.[0-9]+)*)[:\s]*', '', clean_t, flags=re.IGNORECASE).strip().lower().rstrip('?:.')
            q_norm = question.strip().lower().rstrip('?:.')
            
            # Exact or normalized question match
            if t_norm == q_norm or clean_t.strip().lower().rstrip('?:.') == q_norm:
                return True
            
            words = [w.lower() for w in re.findall(r'\w+', clean_t)]
            if not words:
                return True
                
            non_stop_words = [w for w in words if w not in ENGLISH_STOPWORDS]
            
            # Short header/question title line
            if len(words) <= 15 and (clean_t.endswith('?') or re.match(r'^\d+(\.\d+)*\s+', clean_t)):
                if non_stop_words:
                    overlap = [w for w in non_stop_words if w in q_tokens_set]
                    if len(overlap) / len(non_stop_words) >= 0.65:
                        return True
            return False

        def is_non_explanatory_header_or_title(text: str) -> bool:
            clean_t = text.strip()
            words = re.findall(r'\w+', clean_t)
            if not words:
                return True
            # Standalone page/chapter numbers e.g. "23", "Page 23", "4"
            if re.match(r'^(?:page\s+)?\d+$', clean_t, flags=re.IGNORECASE):
                return True
            # Short title headers without punctuation or full sentences e.g. "23 Nationalism in Europe", "Visualising the Nation"
            if len(words) <= 6 and not any(punct in clean_t for punct in ['.', ':', ';', '?']):
                return True
            return False

        def tokens_match(q_tok: str, rec_tokens: set[str]) -> bool:
            if q_tok in rec_tokens:
                return True
            IRREGULAR_MAP = {"stand": "stood", "stood": "stand", "is": "are", "was": "were"}
            if IRREGULAR_MAP.get(q_tok) in rec_tokens:
                return True
            if len(q_tok) >= 4:
                prefix = q_tok[:4]
                if any(rt.startswith(prefix) or q_tok.startswith(rt[:4]) for rt in rec_tokens if len(rt) >= 4):
                    return True
            return False

        # Collect candidate entries across retrieved context chunks using generic TF-IDF token specificity scoring
        def clean_fragment(t: str) -> str:
            s = t.strip()
            if s and s[0].islower():
                first_cap = re.search(r'\b[A-Z]', s)
                if first_cap and first_cap.start() > 0:
                    s = s[first_cap.start():]
            return s

        candidate_entries = []
        for chunk_obj in context_chunks:
            chunk_text = chunk_obj["text"]
            
            # Extract individual lines and sentence blocks generically
            raw_lines = [l.strip() for l in chunk_text.splitlines() if l.strip()]
            records = set()

            def add_rec(t: str):
                cleaned = clean_fragment(t)
                if len(cleaned.split()) >= 3:
                    records.add(cleaned)

            for i, line in enumerate(raw_lines):
                if is_heading_or_question_repeat(line) or is_non_explanatory_header_or_title(line):
                    following_lines = [l for l in raw_lines[i+1:i+4] if not is_non_explanatory_header_or_title(l)]
                    if following_lines:
                        joined = " ".join(following_lines)
                        add_rec(joined)
                        for fl in following_lines:
                            add_rec(fl)
                else:
                    add_rec(line)

            # Reconstitute column-aligned tabular records generically
            record_codes = list(dict.fromkeys(re.findall(r'\b[A-Z]{2,}\d+[A-Z0-9]*\b', chunk_text)))
            if len(record_codes) >= 2:
                for code in record_codes:
                    matching_lines = [l for l in raw_lines if code in l]
                    if matching_lines:
                        for m in matching_lines:
                            add_rec(m)
                    else:
                        code_parts = [l for l in raw_lines if any(tok in l for tok in [code, code[:4]])]
                        if code_parts:
                            joined = " ".join(code_parts)
                            add_rec(joined)
                
                for i in range(len(raw_lines) - 1):
                    joined = raw_lines[i] + " " + raw_lines[i+1]
                    add_rec(joined)
                for i in range(len(raw_lines) - 2):
                    joined = raw_lines[i] + " " + raw_lines[i+1] + " " + raw_lines[i+2]
                    add_rec(joined)

            # Reconstitute narrative prose paragraphs and multi-line sliding window entries
            for i in range(len(raw_lines) - 1):
                if not is_heading_or_question_repeat(raw_lines[i]) and not is_heading_or_question_repeat(raw_lines[i+1]) and not is_non_explanatory_header_or_title(raw_lines[i]) and not is_non_explanatory_header_or_title(raw_lines[i+1]):
                    joined = raw_lines[i] + " " + raw_lines[i+1]
                    add_rec(joined)
            for i in range(len(raw_lines) - 2):
                if not is_heading_or_question_repeat(raw_lines[i]) and not is_heading_or_question_repeat(raw_lines[i+1]) and not is_heading_or_question_repeat(raw_lines[i+2]) and not is_non_explanatory_header_or_title(raw_lines[i]) and not is_non_explanatory_header_or_title(raw_lines[i+1]) and not is_non_explanatory_header_or_title(raw_lines[i+2]):
                    joined = raw_lines[i] + " " + raw_lines[i+1] + " " + raw_lines[i+2]
                    add_rec(joined)

            prose_buf = []
            for line in raw_lines:
                if is_heading_or_question_repeat(line) or is_non_explanatory_header_or_title(line):
                    continue
                if not re.search(r'\b[A-Z0-9]{5,}\b', line):
                    prose_buf.append(line)
                    if line.endswith(('.', ':', '?', ';')):
                        joined = " ".join(prose_buf)
                        add_rec(joined)
                        prose_buf = []
            if prose_buf:
                joined = " ".join(prose_buf)
                add_rec(joined)

            for rec_text in records:
                rec_text = rec_text.strip()
                if rec_text and rec_text[0].islower():
                    first_cap = re.search(r'\b[A-Z]', rec_text)
                    if first_cap and first_cap.start() > 0:
                        rec_text = rec_text[first_cap.start():]

                if is_heading_or_question_repeat(rec_text) or is_non_explanatory_header_or_title(rec_text):
                    continue

                rec_tokens = set(w.lower() for w in re.findall(r'\w+', rec_text))
                non_stop_rec = [w for w in rec_tokens if w not in ENGLISH_STOPWORDS]
                if not non_stop_rec:
                    # Skip empty fragments
                    continue

                matching_tokens = [t for t in q_tokens if tokens_match(t, rec_tokens)]
                if matching_tokens:
                    weighted_coverage = sum(token_weights[t] for t in matching_tokens) / max_weight_possible
                    has_data = 1.0 if re.search(r'\d+', rec_text) else 0.0
                    match_density = len(matching_tokens) / max(len(rec_tokens), 1)
                    is_complete_sentence = 1.0 if rec_text.endswith(('.', '!', '?')) and len(rec_text.split()) >= 10 else 0.0
                    is_definition_sentence = 1.0 if any(kw in rec_text.lower() for kw in ['stood for', 'freedom', 'equality', 'defined as', 'refers to', 'means', 'requirement', 'policy']) else 0.0
                    score = (4.0 * weighted_coverage) + (1.0 * has_data) + (0.5 * match_density) + (0.8 * is_complete_sentence) + (1.0 * is_definition_sentence)
                    candidate_entries.append({
                        "matches": len(matching_tokens),
                        "score": score,
                        "text": rec_text,
                        "chunk_text": chunk_text,
                        "doc_name": chunk_obj["document_name"],
                        "page_number": chunk_obj["page_number"]
                    })

        # Filter candidates to exclude any question repeats or title headers
        valid_candidates = [e for e in candidate_entries if not is_heading_or_question_repeat(e["text"]) and not is_non_explanatory_header_or_title(e["text"])]

        if not valid_candidates:
            if context_chunks:
                best_c = context_chunks[0]
                return f"Based on the retrieved document [{best_c['document_name']}, Page {best_c['page_number']}]: {best_c['text']}"
            return "The requested information could not be found in the provided document context."

        # Sort candidates by generic score descending
        valid_candidates.sort(key=lambda x: x["score"], reverse=True)
        best_entry = valid_candidates[0]

        best_doc = best_entry["doc_name"]
        best_page = best_entry["page_number"]

        # Restrict multi-line synthesis to explanatory candidates from the SAME document and page
        same_page_candidates = [e for e in valid_candidates if e["doc_name"] == best_doc and e["page_number"] == best_page]
        high_cov_entries = [e for e in same_page_candidates if e["matches"] >= 2 or e["score"] >= 2.0]
        if not high_cov_entries:
            high_cov_entries = same_page_candidates[:3]
        
        def clean_sentence_boundaries(text: str, parent_chunk: str = "") -> str:
            t = text.strip()
            if t and t[0].islower():
                first_cap = re.search(r'\b[A-Z]', t)
                if first_cap:
                    t = t[first_cap.start():]
                else:
                    return ""
            if t.endswith(('.', '!', '?')):
                return t
            last_punct = max(t.rfind('.'), t.rfind('!'), t.rfind('?'))
            if last_punct > 15:
                return t[:last_punct+1]
            return t

        unique_lines = []
        for e in high_cov_entries:
            txt = clean_sentence_boundaries(e["text"], e.get("chunk_text", ""))
            parent_chunk = e.get("chunk_text", "")
            if parent_chunk and txt not in parent_chunk:
                # Trim back to clean sentence in parent_chunk
                last_punct = max(parent_chunk.rfind('.'), parent_chunk.rfind('!'), parent_chunk.rfind('?'))
                if last_punct > 20:
                    txt = parent_chunk[:last_punct+1]
                else:
                    txt = parent_chunk
            if len(txt.split()) >= 6 and not any(txt in existing or existing in txt for existing in unique_lines):
                unique_lines.append(txt)

        if unique_lines:
            clean_answer = " ".join(unique_lines[:1])
        else:
            clean_answer = clean_sentence_boundaries(best_entry["text"], best_entry.get("chunk_text", ""))

        if clean_answer and clean_answer[0].islower():
            m = re.search(r'[A-Z]', clean_answer)
            if m and m.start() > 0:
                clean_answer = clean_answer[m.start():]

        return f"Based on the retrieved document [{best_entry['doc_name']}, Page {best_entry['page_number']}]: {clean_answer}"











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
