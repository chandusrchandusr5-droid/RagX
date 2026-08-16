"""
RAGX NOVA Assistant Automated Integration Test Suite
Verifies greeting endpoint, chat responses, categories, and zero regression.
"""
import requests

BASE_URL = "http://127.0.0.1:8000/api"

def test_nova_assistant():
    print("==================================================")
    print("      RAGX NOVA ASSISTANT INTEGRATION TEST SUITE  ")
    print("==================================================")

    # 1. Test Greeting Endpoint
    print("\n--- 1. Testing GET /api/nova/greeting ---")
    res_greet = requests.get(f"{BASE_URL}/nova/greeting")
    assert res_greet.status_code == 200, f"Greeting failed: {res_greet.status_code}"
    greet_data = res_greet.json()
    assert "greeting" in greet_data
    assert "suggested_prompts" in greet_data
    assert len(greet_data["suggested_prompts"]) > 0
    print("PASSED: NOVA greeting endpoint returned valid payload and suggested prompts!")

    # 2. Test "What is RAGX?" Query
    print("\n--- 2. Testing POST /api/nova/chat ('What is RAGX?') ---")
    res_q1 = requests.post(f"{BASE_URL}/nova/chat", json={"message": "What is RAGX?", "context_page": "documents"})
    assert res_q1.status_code == 200
    d1 = res_q1.json()
    assert d1["category"] == "PLATFORM_OVERVIEW"
    assert "Data Quality Analysis" in d1["response"] or "RAG" in d1["response"]
    print("PASSED: NOVA correctly responded to platform overview query!")

    # 3. Test "How is Reliability calculated?" Query
    print("\n--- 3. Testing POST /api/nova/chat ('How is Reliability calculated?') ---")
    res_q2 = requests.post(f"{BASE_URL}/nova/chat", json={"message": "How is Answer Reliability (S_Ans) calculated?", "context_page": "evaluator"})
    assert res_q2.status_code == 200
    d2 = res_q2.json()
    assert d2["category"] == "RELIABILITY_METHODOLOGY"
    assert "S_supp" in d2["response"] and "S_cov" in d2["response"] and "S_sim" in d2["response"]
    print("PASSED: NOVA accurately detailed the composite Answer Reliability Score math!")

    # 4. Test "What is a 5-tuple citation?" Query
    print("\n--- 4. Testing POST /api/nova/chat ('5-tuple citation') ---")
    res_q3 = requests.post(f"{BASE_URL}/nova/chat", json={"message": "What is a 5-tuple citation?", "context_page": "evaluator"})
    assert res_q3.status_code == 200
    d3 = res_q3.json()
    assert d3["category"] == "CITATION_TRACEABILITY"
    assert "source_file" in d3["response"] and "chunk_id" in d3["response"]
    print("PASSED: NOVA accurately detailed 5-tuple citation traceability structure!")

    print("\n==================================================")
    print("     ALL NOVA ASSISTANT TESTS PASSED (100%)       ")
    print("==================================================")

if __name__ == '__main__':
    test_nova_assistant()
