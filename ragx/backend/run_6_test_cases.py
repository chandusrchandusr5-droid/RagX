import json
from app.services.rag_engine import rag_engine
from app.services.evaluator import AnswerEvaluator

test_cases = [
    {
        "id": 1,
        "name": "Greek struggle for independence",
        "type": "RAG_PIPELINE",
        "question": "When did the Greek struggle for independence begin?"
    },
    {
        "id": 2,
        "name": "Greek struggle for independence — 1830?",
        "type": "CUSTOM_ANSWER",
        "question": "When did the Greek struggle for independence begin?",
        "custom_answer": "The Greek struggle for independence began in 1830."
    },
    {
        "id": 3,
        "name": "Liberal-nationalist revolutions",
        "type": "RAG_PIPELINE",
        "question": "What were the major liberal-nationalist revolutions in Europe during the nineteenth century?"
    },
    {
        "id": 4,
        "name": "Liberalism among new middle classes",
        "type": "RAG_PIPELINE",
        "question": "What did ideas of national unity in early nineteenth-century Europe have to do with the ideology of liberalism among the new middle classes?"
    },
    {
        "id": 5,
        "name": "July Revolution in France",
        "type": "RAG_PIPELINE",
        "question": "What happened during the July Revolution in France?"
    },
    {
        "id": 6,
        "name": "Industrialisation custom-answer test",
        "type": "CUSTOM_ANSWER",
        "question": "How did industrialisation affect the new middle classes in Europe?",
        "custom_answer": "Industrialisation led to the growth of the educated liberal middle classes in Western and Central Europe."
    }
]

results = []

for case in test_cases:
    q = case["question"]
    if case["type"] == "RAG_PIPELINE":
        rag_res = rag_engine.query(question=q, top_k=3)
        ans = rag_res.get("answer", "")
        ev = rag_res.get("retrieved_evidence", [])
    else:
        ans = case["custom_answer"]
        rag_res = rag_engine.query(question=q, top_k=3)
        ev = rag_res.get("retrieved_evidence", [])

    rep = AnswerEvaluator.evaluate(query=q, answer=ans, retrieved_evidence=ev)
    
    sub = rep["scoring_breakdown"]["sub_scores"]
    raw = rep["scoring_breakdown"]["raw_measurements"]
    
    first_ev = ev[0]["text"][:80] + "..." if ev else "None"
    
    record = {
        "id": case["id"],
        "name": case["name"],
        "question": q,
        "retrieved_evidence_snippet": first_ev,
        "answer": ans,
        "s_supp": sub["claim_support_score"],
        "s_cov": sub["citation_coverage_score"],
        "s_sim": sub["retrieval_similarity_score"],
        "final_score": rep["overall_reliability_score"],
        "reliability_status": rep["reliability_status"],
        "hallucination_risk": rep["hallucination_risk"],
        "failure_category": rep["failure_category"]
    }
    results.append(record)
    print(f"=== TEST CASE {case['id']}: {case['name']} ===")
    print(f"  Question          : {q}")
    print(f"  Answer            : {ans}")
    print(f"  S_supp            : {sub['claim_support_score']}%")
    print(f"  S_cov             : {sub['citation_coverage_score']}%")
    print(f"  S_sim             : {sub['retrieval_similarity_score']}%")
    print(f"  Final Score       : {rep['overall_reliability_score']}%")
    print(f"  Reliability Status: {rep['reliability_status']}")
    print(f"  Hallucination Risk: {rep['hallucination_risk']}")
    print(f"  Failure Category  : {rep['failure_category']}\n")

with open("scratch_test_results.json", "w") as f:
    json.dump(results, f, indent=2)
