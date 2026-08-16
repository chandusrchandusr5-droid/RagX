"""
RAGX Heading Truncation Defect Regression Test Suite
Verifies that fallback synthesis does not truncate generated answers at section headers ending with ':'
and preserves the complete factual body including numeric figures and page citations.
"""
from app.services.rag_engine import RAGEngine


def test_heading_truncation_fix():
    print("==================================================")
    print(" HEADING TRUNCATION DEFECT REGRESSION TEST SUITE  ")
    print("==================================================")

    question = "What is the attendance requirement?"
    retrieved_evidence = [
        {
            "document_name": "Attendance_Policy.pdf",
            "page_number": 1,
            "chunk_id": "Attendance_Policy.pdf_p1_001",
            "text": "GENERAL ATTENDANCE REQUIREMENT:\nAll undergraduate students must maintain a minimum attendance of 75% in every course module.",
            "similarity_score": 0.6753
        }
    ]

    answer = RAGEngine.generate_llm_response(question, retrieved_evidence)
    print("\nGenerated Synthesized Answer:")
    print(answer)

    # 1. Assert answer does NOT terminate at the colon header
    assert not answer.strip().endswith("GENERAL ATTENDANCE REQUIREMENT:"), \
        "Synthesized answer incorrectly terminated at the section header ending with ':'!"

    # 2. Assert answer contains the complete policy statement and the 75% numeric requirement
    assert "75%" in answer, "Synthesized answer missing the critical 75% attendance requirement!"
    assert "All undergraduate students must maintain a minimum attendance of 75%" in answer, \
        "Synthesized answer missing the factual body text!"

    # 3. Assert correct source document and page citation are preserved
    assert "(Attendance_Policy.pdf, Page 1)" in answer, "Source document and page citation missing or corrupted!"

    print("\nPASSED: Synthesized answer complete, factual, and correctly cited!")
    print("==================================================")

if __name__ == "__main__":
    test_heading_truncation_fix()
