import hashlib
import re
import logging
from pathlib import Path
from app.core.config import settings
from app.core.vector_db import vector_db
from app.services.document_parser import DocumentParser

logger = logging.getLogger("ragx.data_quality")

_QUALITY_AUDIT_CACHE = {}

class DataQualityService:
    @classmethod
    def invalidate_audit_cache(cls):
        global _QUALITY_AUDIT_CACHE
        _QUALITY_AUDIT_CACHE.clear()

    @staticmethod
    def calculate_file_md5(file_path: Path) -> str:
        hasher = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def is_legitimate_low_text_page(text: str) -> bool:
        """
        Contextually checks if a low-text page is a valid structural page
        (e.g., Title Page, Table of Contents, Signatures, End Notes, Cover).
        """
        text_lower = text.lower()
        structural_keywords = [
            "table of contents", "title", "chapter", "section", "signature",
            "approved by", "manual", "policy document", "version", "index",
            "college of engineering", "academic policy"
        ]
        return any(kw in text_lower for kw in structural_keywords) or len(text.strip().splitlines()) <= 4

    @classmethod
    def audit_knowledge_base(cls, registry_file_path: Path = None, uploads_dir_path: Path = None, owner_id: str = None, document_id: str = None) -> dict:
        from app.services.document_registry import DocumentRegistryService

        upload_dir = uploads_dir_path or settings.UPLOAD_DIR
        
        target_doc = None
        if document_id and str(document_id).strip() and str(document_id).lower() != "all":
            target_doc = DocumentRegistryService.get_document_by_id(document_id, owner_id=owner_id)
            if not target_doc:
                target_doc = DocumentRegistryService.get_document_by_name(document_id, owner_id=owner_id)

        # Filter files by owner_id and optional target document
        if owner_id:
            user_docs = DocumentRegistryService.get_all_documents(owner_id=owner_id, status_filter="ACTIVE")
            user_doc_names = set(d.get("document_name", "") for d in user_docs)
            if target_doc:
                user_doc_names = {target_doc["document_name"]}
            uploaded_files = [f for f in upload_dir.iterdir() if f.is_file() and f.name in user_doc_names] if upload_dir.exists() else []
        elif target_doc:
            uploaded_files = [f for f in upload_dir.iterdir() if f.is_file() and f.name == target_doc["document_name"]] if upload_dir.exists() else []
        else:
            uploaded_files = [f for f in upload_dir.iterdir() if f.is_file() and f.suffix.lower() in ['.pdf', '.txt', '.md']] if upload_dir.exists() else []

        cache_key = (
            owner_id or "global",
            document_id or "all",
            tuple(sorted([(f.name, f.stat().st_mtime) for f in uploaded_files]))
        )
        if cache_key in _QUALITY_AUDIT_CACHE:
            return _QUALITY_AUDIT_CACHE[cache_key]

        # Raw Measurements Tracker
        raw_measurements = {
            "total_documents": len(uploaded_files),
            "total_pages": 0,
            "unextractable_pages": 0,
            "legitimate_low_text_pages": 0,
            "total_chunks": 0,
            "redundant_chunks_count": 0,
            "total_topics_evaluated": 0,
            "conflicting_topics_count": 0
        }

        # Edge Case 1: Empty Knowledge Base for current user
        if not uploaded_files:
            return {
                "composite_reliability_score": 100.0,
                "user_facing_status": "GOOD",
                "display_status": "GOOD",
                "message": "No documents uploaded yet. Upload documents to perform a Data Quality Audit.",
                "scoring_breakdown": {
                    "raw_measurements": raw_measurements,
                    "sub_scores": {
                        "extraction_integrity_score": 100.0,
                        "vector_diversity_score": 100.0,
                        "consistency_index": 100.0
                    },
                    "configured_weights": {
                        "extraction_weight": settings.WEIGHT_EXTRACTION,
                        "diversity_weight": settings.WEIGHT_DIVERSITY,
                        "consistency_weight": settings.WEIGHT_CONSISTENCY
                    }
                },
                "summary": {
                    "total_documents": 0,
                    "total_chunks": 0,
                    "total_issues_found": 0,
                    "confirmed_issues": 0,
                    "suspected_signals": 0
                },
                "issues": []
            }


        issues = []
        issue_counter = 1

        # -------------------------------------------------------------
        # CHECK 1: File Hashes & Exact Duplicate Document Detection
        # -------------------------------------------------------------
        file_hashes = {}
        parsed_docs = {}

        for file_path in uploaded_files:
            md5_hash = cls.calculate_file_md5(file_path)
            if md5_hash in file_hashes:
                existing_file = file_hashes[md5_hash]
                issues.append({
                    "issue_id": f"QUAL-{issue_counter:03d}",
                    "issue_type": "DUPLICATE_FILE_REDUNDANCY",
                    "category": "REDUNDANCY",
                    "issue_status": "DETECTED_ISSUE",
                    "confidence": 1.0,
                    "severity": "WARNING",
                    "title": f"Exact Duplicate File Uploaded ('{file_path.name}')",
                    "source_file": file_path.name,
                    "page_number": 1,
                    "chunk_id": "N/A",
                    "related_file": existing_file,
                    "evidence_snippet": f"MD5 Hash: {md5_hash}",
                    "related_snippet": f"MD5 Hash: {md5_hash}",
                    "potential_rag_impact": "Identical files consume duplicate vector store space and reduce retrieval context diversity during search.",
                    "remediation": "Consider removing the duplicate file to optimize vector search efficiency.",
                    "demonstrated_impact": None
                })
                issue_counter += 1
            else:
                file_hashes[md5_hash] = file_path.name

            # Parse document pages for all uploaded files
            try:
                parsed = DocumentParser.parse_document(file_path)
                parsed_docs[file_path.name] = parsed
                raw_measurements["total_pages"] += parsed["total_pages"]

                # -------------------------------------------------------------
                # CHECK 2: Contextual Page Health Check
                # -------------------------------------------------------------
                for page in parsed["pages"]:
                    page_text = page["text"].strip()
                    page_num = page["page_number"]

                    if len(page_text) == 0:
                        raw_measurements["unextractable_pages"] += 1
                        issues.append({
                            "issue_id": f"QUAL-{issue_counter:03d}",
                            "issue_type": "UNEXTRACTABLE_PAGE",
                            "category": "EXTRACTION",
                            "issue_status": "DETECTED_ISSUE",
                            "confidence": 1.0,
                            "severity": "CRITICAL",
                            "title": f"Un-extractable or Empty Page Detected (Page {page_num})",
                            "source_file": file_path.name,
                            "page_number": page_num,
                            "chunk_id": "N/A",
                            "related_file": None,
                            "evidence_snippet": "Zero extractable characters found on this page.",
                            "related_snippet": None,
                            "potential_rag_impact": "Page text could not be extracted (possibly a scanned image or corrupted PDF page), preventing RAG indexing for this section.",
                            "remediation": "Run OCR processing on scanned pages before uploading.",
                            "demonstrated_impact": None
                        })
                        issue_counter += 1
                    elif len(page_text) < 50:
                        if cls.is_legitimate_low_text_page(page_text):
                            raw_measurements["legitimate_low_text_pages"] += 1
                            issues.append({
                                "issue_id": f"QUAL-{issue_counter:03d}",
                                "issue_type": "PAGE_NOTICE",
                                "category": "EXTRACTION",
                                "issue_status": "DETECTED_ISSUE",
                                "confidence": 1.0,
                                "severity": "INFO",
                                "title": f"Legitimate Structural/Low-Text Page (Page {page_num})",
                                "source_file": file_path.name,
                                "page_number": page_num,
                                "chunk_id": "N/A",
                                "related_file": None,
                                "evidence_snippet": f"\"{page_text[:60]}...\"",
                                "related_snippet": None,
                                "potential_rag_impact": "Valid structural page (Title/Cover/Signature). Excluded from un-extractable health penalty.",
                                "remediation": "No action required.",
                                "demonstrated_impact": None
                            })
                            issue_counter += 1
            except Exception as e:
                logger.error(f"Error parsing document {file_path.name} for quality audit: {e}")


        # -------------------------------------------------------------
        # CHECK 3: Scalable Near-Duplicate Chunk Audit (ANN Top-K Vector Search)
        # -------------------------------------------------------------
        redundant_chunks_set = set()
        try:
            all_chunks_data = vector_db.get_all_chunks(owner_id=owner_id)
            if all_chunks_data and all_chunks_data.get("documents"):
                raw_docs = all_chunks_data["documents"]
                raw_metas = all_chunks_data["metadatas"]
                raw_embs = all_chunks_data.get("embeddings")

                if target_doc:
                    t_id = target_doc["document_id"]
                    t_name = target_doc["document_name"]
                    indices = [i for i, m in enumerate(raw_metas) if m.get("document_id") == t_id or m.get("document_name") == t_name]
                    documents = [raw_docs[i] for i in indices]
                    metadatas = [raw_metas[i] for i in indices]
                    embeddings = [raw_embs[i] for i in indices] if raw_embs is not None else None
                else:
                    documents = raw_docs
                    metadatas = raw_metas
                    embeddings = raw_embs

                raw_measurements["total_chunks"] = len(documents)

                if embeddings is not None and len(embeddings) > 1:
                    threshold = settings.CHUNK_DUPLICATE_THRESHOLD
                    try:
                        import numpy as np
                        embs_arr = np.array(embeddings)
                        norms = np.linalg.norm(embs_arr, axis=1, keepdims=True) + 1e-9
                        norm_embs = embs_arr / norms
                        sim_matrix = np.dot(norm_embs, norm_embs.T)

                        n = len(embeddings)
                        for i in range(n):
                            chunk_id_i = metadatas[i].get("chunk_id", f"chunk_{i}")
                            doc_name_i = metadatas[i].get("document_name", "Unknown")
                            page_num_i = metadatas[i].get("page_number", 1)
                            for j in range(i + 1, n):
                                similarity = float(sim_matrix[i, j])
                                if similarity >= threshold:
                                    chunk_id_j = metadatas[j].get("chunk_id", f"chunk_{j}")
                                    doc_name_j = metadatas[j].get("document_name", "Unknown")
                                    pair_key = (chunk_id_i, chunk_id_j)
                                    if pair_key not in redundant_chunks_set:
                                        redundant_chunks_set.add(pair_key)
                                        issues.append({
                                            "issue_id": f"QUAL-{issue_counter:03d}",
                                            "issue_type": "HIGH_OVERLAP_CHUNK",
                                            "category": "REDUNDANCY",
                                            "issue_status": "DETECTED_ISSUE",
                                            "confidence": 0.92,
                                            "severity": "WARNING",
                                            "title": "High Semantic Overlap Between Chunks",
                                            "source_file": doc_name_i,
                                            "page_number": page_num_i,
                                            "chunk_id": chunk_id_i,
                                            "related_file": doc_name_j,
                                            "evidence_snippet": documents[i][:80] + "...",
                                            "related_snippet": documents[j][:80] + "...",
                                            "potential_rag_impact": f"Chunks share {similarity * 100:.1f}% semantic similarity. Consumes top-K retrieval slots with duplicate information.",
                                            "remediation": "Adjust chunk overlap parameters or remove duplicate document passages.",
                                            "demonstrated_impact": None
                                        })
                                        issue_counter += 1
                    except Exception as e:
                        logger.error(f"Error performing similarity matrix calculation: {e}")

                # Calculate unique redundant chunks count
                unique_redundant_ids = set()
                for p1, p2 in redundant_chunks_set:
                    unique_redundant_ids.add(p1)
                    unique_redundant_ids.add(p2)
                raw_measurements["redundant_chunks_count"] = len(unique_redundant_ids)
        except Exception as e:
            logger.error(f"Error auditing chunk redundancies: {e}")



        # -------------------------------------------------------------
        # CHECK 4: Candidate Conflict Detection Across Knowledge Base
        # -------------------------------------------------------------
        entity_topics = ["attendance", "grading", "mark", "fee", "exam", "condonation", "requirement"]
        raw_measurements["total_topics_evaluated"] = len(entity_topics)

        # Regex extractors for numeric percentages & figures
        num_pattern = re.compile(r'\d{1,3}%|\d{1,3}\s*marks|\d{1,3}\s*percent')

        topic_conflicts_detected = set()

        if len(parsed_docs) >= 1:
            all_snippets = []
            for doc_name, doc_data in parsed_docs.items():
                for page in doc_data["pages"]:
                    text = page["text"]
                    # Normalize soft line breaks inside paragraphs
                    paragraphs = re.split(r'\n\s*\n', text)
                    for para in paragraphs:
                        para_clean = " ".join(para.split())
                        if len(para_clean) > 10:
                            all_snippets.append({
                                "doc_name": doc_name,
                                "page_number": page["page_number"],
                                "text": para_clean
                            })


            # Group snippets that contain numerical figures by topic
            topic_snippets = {}
            for snip in all_snippets:
                snip_lower = snip["text"].lower()
                nums = num_pattern.findall(snip_lower)
                if nums:
                    for topic in entity_topics:
                        if topic in snip_lower:
                            if topic not in topic_snippets:
                                topic_snippets[topic] = []
                            topic_snippets[topic].append((snip, nums))

            for topic, snip_list in topic_snippets.items():
                for i in range(len(snip_list)):
                    for j in range(i + 1, len(snip_list)):
                        s1, num1 = snip_list[i]
                        s2, num2 = snip_list[j]
                        if s1["doc_name"] != s2["doc_name"] and set(num1) != set(num2):
                            topic_conflicts_detected.add(topic)
                            issues.append({
                                "issue_id": f"QUAL-{issue_counter:03d}",
                                "issue_type": "SUSPECTED_CONFLICT_SIGNAL",
                                "category": "CONSISTENCY",
                                "issue_status": "SUSPECTED_SIGNAL",
                                "confidence": 0.75,
                                "severity": "WARNING",
                                "title": f"Suspected Numerical Disparity in Topic '{topic.capitalize()}'",
                                "source_file": s1["doc_name"],
                                "page_number": s1["page_number"],
                                "chunk_id": "N/A",
                                "related_file": s2["doc_name"],
                                "evidence_snippet": s1["text"],
                                "related_snippet": s2["text"],
                                "potential_rag_impact": f"Document '{s1['doc_name']}' mentions '{', '.join(num1)}' while '{s2['doc_name']}' mentions '{', '.join(num2)}'. If both are retrieved, LLM receives conflicting context.",
                                "remediation": f"Verify if {s2['doc_name']} is an updated policy or applies to a different student category.",
                                "demonstrated_impact": None
                            })
                            issue_counter += 1



        raw_measurements["conflicting_topics_count"] = len(topic_conflicts_detected)

        # -------------------------------------------------------------
        # CALCULATE NORMALIZED SUB-SCORES & COMPOSITE RELIABILITY SCORE
        # -------------------------------------------------------------
        tot_pages = raw_measurements["total_pages"]
        unext_pages = raw_measurements["unextractable_pages"]
        tot_chunks = raw_measurements["total_chunks"]
        red_chunks = raw_measurements["redundant_chunks_count"]
        tot_topics = raw_measurements["total_topics_evaluated"]
        conf_topics = raw_measurements["conflicting_topics_count"]

        # Sub-Score 1: Extraction Integrity
        r_ext = 1.0 if tot_pages == 0 else max(0.0, (tot_pages - unext_pages) / tot_pages)
        s_ext = round(r_ext * 100.0, 1)

        # Sub-Score 2: Vector Diversity
        r_red = 0.0 if tot_chunks <= 1 else min(1.0, red_chunks / tot_chunks)
        s_div = round(max(0.0, (1.0 - r_red) * 100.0), 1)

        # Sub-Score 3: Consistency Index
        r_conf = 0.0 if tot_topics == 0 else min(1.0, (conf_topics * 0.75) / max(1, tot_topics))
        s_cons = round(max(0.0, (1.0 - r_conf) * 100.0), 1)

        # Configured Weights
        w_ext = settings.WEIGHT_EXTRACTION
        w_div = settings.WEIGHT_DIVERSITY
        w_cons = settings.WEIGHT_CONSISTENCY

        composite_score = round((w_ext * s_ext) + (w_div * s_div) + (w_cons * s_cons), 1)
        composite_score = max(0.0, min(100.0, composite_score))

        # Status Classification
        if composite_score >= 85.0:
            user_status = "GOOD"
        elif composite_score >= 65.0:
            user_status = "MODERATE"
        else:
            user_status = "NEEDS_ATTENTION"

        res_report = {
            "composite_reliability_score": composite_score,
            "audited_document_id": target_doc.get("document_id") if target_doc else "all",
            "audited_document_name": target_doc.get("document_name") if target_doc else "All Documents",
            "user_facing_status": user_status,
            "display_status": user_status,
            "scoring_breakdown": {
                "raw_measurements": raw_measurements,
                "sub_scores": {
                    "extraction_integrity_score": s_ext,
                    "vector_diversity_score": s_div,
                    "consistency_index": s_cons
                },
                "configured_weights": {
                    "extraction_weight": w_ext,
                    "diversity_weight": w_div,
                    "consistency_weight": w_cons
                }
            },
            "summary": {
                "total_documents": raw_measurements["total_documents"],
                "total_chunks": tot_chunks,
                "total_issues_found": len(issues),
                "confirmed_issues": sum(1 for i in issues if i["issue_status"] == "DETECTED_ISSUE"),
                "suspected_signals": sum(1 for i in issues if i["issue_status"] == "SUSPECTED_SIGNAL")
            },
            "issues": issues
        }
        _QUALITY_AUDIT_CACHE[cache_key] = res_report
        return res_report

data_quality_service = DataQualityService()
