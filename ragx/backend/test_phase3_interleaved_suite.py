"""
RAGX Phase 3 — Complete Multi-Aspect & Interleaved Audit Regression Test Suite
Verifies query independence, multi-part question aspect coverage, zero data leakage,
and authentic 5-tuple citation traceability.
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/evaluator/query-and-evaluate"

def run_test_query(query: str, step_label: str):
    print(f"\n=======================================================")
    print(f"[{step_label}] Testing Query: '{query[:80]}...'")
    print(f"=======================================================")

    res = requests.post(BASE_URL, json={"question": query, "top_k": 3}, timeout=15)
    assert res.status_code == 200, f"Failed HTTP {res.status_code}: {res.text}"

    data = res.json()
    q_returned = data.get("question")
    answer = data.get("answer", "")
    evidence = data.get("retrieved_evidence", [])
    report = data.get("evaluation_report", {})

    rel_score = report.get("overall_reliability_score", 0.0)
    status = report.get("reliability_status", "")
    fail_cat = report.get("failure_category", "")
    h_risk = report.get("hallucination_risk", "")
    claims = report.get("claim_analysis", [])
    coverage = report.get("question_coverage_analysis", {})

    ans_disp = answer.encode('ascii', 'replace').decode('ascii')
    q_disp = q_returned.encode('ascii', 'replace').decode('ascii') if q_returned else ""
    print(f"Returned Query        : {q_disp}")
    print(f"Generated Answer      : {ans_disp[:140]}..." if len(ans_disp) > 140 else f"Generated Answer      : {ans_disp}")

    print(f"Reliability Score     : {rel_score}%")
    print(f"Reliability Status    : {status}")
    print(f"Failure Category      : {fail_cat}")
    print(f"Hallucination Risk    : {h_risk}")
    # Verify 5-tuple citation traceability for supported claims:
    # 1. claim_id, 2. claim_text, 3. chunk_id, 4. source_file, 5. page_number
    traceable_claims_count = 0
    for claim in claims:
        if claim.get("support_status") == "SUPPORTED":
            matched_ev = claim.get("matched_evidence", {})
            has_valid_5_tuple = (
                bool(claim.get("claim_id")) and
                bool(claim.get("claim_text")) and
                claim.get("citation_traceable") is True and
                matched_ev.get("chunk_id") != "N/A" and
                matched_ev.get("source_file") != "Unknown" and
                matched_ev.get("page_number") is not None
            )
            assert has_valid_5_tuple, f"5-tuple citation proof broken for claim {claim.get('claim_id')}"
            traceable_claims_count += 1

    print(f"5-Tuple Citation Verified: {traceable_claims_count} supported claims fully traceable to (Claim ID -> Claim Text -> Chunk ID -> Document Name -> Page Number).")


    return {
        "query": query,
        "returned_query": q_returned,
        "answer": answer,
        "evidence_count": len(evidence),
        "score": rel_score,
        "status": status,
        "failure_category": fail_cat,
        "h_risk": h_risk,
        "claims_count": len(claims),
        "coverage_ratio": coverage.get('coverage_ratio', 1.0),
        "traceable_claims": traceable_claims_count
    }


def main():
    print("Starting RAGX Phase 3 Multi-Aspect & Interleaved Regression Test Suite...")

    COMPLEX_QUERY = "How did the rise of the educated liberal middle classes, the economic changes caused by industrialisation, and the ideas of liberalism contribute to the emergence of nationalism and the demand for nation-states in nineteenth-century Europe? Explain the connection between these factors using evidence from the chapter."

    # Test Cases A, B, C, D, E, and Interleaved Sequence F
    seq = [
        ("Test A — Mathematics-II", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?"),
        ("Test B — Chemistry", "What are the marks obtained in CHEMISTRY FOR CSE STREAM?"),
        ("Test C — Complex Multi-Part", COMPLEX_QUERY),
        ("Test D — Unsupported", "What is the speed of light in vacuum?"),
        ("Test E — Short Unrelated", "sr"),
        ("Interleaved F1 (A)", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?"),
        ("Interleaved F2 (B)", "What are the marks obtained in CHEMISTRY FOR CSE STREAM?"),
        ("Interleaved F3 (A)", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?"),
        ("Interleaved F4 (C)", COMPLEX_QUERY),
        ("Interleaved F5 (B)", "What are the marks obtained in CHEMISTRY FOR CSE STREAM?"),
        ("Interleaved F6 (C)", COMPLEX_QUERY),
        ("Interleaved F7 (A)", "What are the marks obtained in MATHEMATICS-II FOR CSE STREAM?")
    ]

    results = []
    for label, q in seq:
        res = run_test_query(q, label)
        results.append((label, res))

    print("\n\n=======================================================")
    print("COMPREHENSIVE REGRESSION TEST SUMMARY")
    print("=======================================================")
    
    passed_all = True
    for label, res in results:
        q = res["query"]
        ans = res["answer"]
        score = res["score"]
        fail_cat = res["failure_category"]
        cov_ratio = res["coverage_ratio"]

        if q == "sr":
            if "MATHEMATICS" in ans.upper() or "CHEMISTRY" in ans.upper():
                print(f"FAILED [{label}]: Stale result leakage detected in 'sr' query! Answer: {ans.encode('ascii', 'replace').decode()}")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Clean query independence for 'sr'. Score: {score}%, Category: {fail_cat}")

        elif "MATHEMATICS" in q.upper():
            if "BMATS201" not in ans and "MATHEMATICS" not in ans.upper():
                print(f"FAILED [{label}]: Expected Mathematics-II result, got: {ans.encode('ascii', 'replace').decode()}")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Mathematics-II evaluated correctly. Score: {score}%, Category: {fail_cat}")

        elif "CHEMISTRY" in q.upper():
            if "BCHES202" not in ans and "CHEMISTRY" not in ans.upper():
                print(f"FAILED [{label}]: Expected Chemistry result, got: {ans.encode('ascii', 'replace').decode()}")
                passed_all = False
            elif "BMATS201" in ans:
                print(f"FAILED [{label}]: Leakage of Mathematics-II into Chemistry query!")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Chemistry evaluated correctly. Score: {score}%, Category: {fail_cat}")

        elif "SPEED OF LIGHT" in q.upper():
            if fail_cat != "EVIDENCE_INSUFFICIENCY" or score != 0.0:
                print(f"FAILED [{label}]: Expected EVIDENCE_INSUFFICIENCY / 0.0%, got: {fail_cat} / {score}%")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Unsupported query evaluated safely. Score: {score}%, Category: {fail_cat}")

        else:
            if score < 50.0 or cov_ratio < 0.5:
                print(f"FAILED [{label}]: Low complex score/coverage! Score: {score}%, Coverage: {cov_ratio}")
                passed_all = False
            else:
                print(f"PASSED [{label}]: Complex query evaluated cleanly. Score: {score}%, Coverage: {cov_ratio}, Category: {fail_cat}")

    print("\n=======================================================")
    print("COMPREHENSIVE REGRESSION TEST SUMMARY")
    print("=======================================================")
    if passed_all:
        print("ALL REGRESSION TESTS PASSED! ZERO DATA LEAKAGE DETECTED.")
    else:
        print("SOME REGRESSION TESTS FAILED! CHECK LOGS ABOVE.")


if __name__ == "__main__":
    main()
