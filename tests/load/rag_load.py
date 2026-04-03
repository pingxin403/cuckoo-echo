"""Load test — simulate concurrent RAG queries.

Usage:
    locust -f tests/load/rag_load.py --host http://localhost:8000
"""
from locust import HttpUser, task, between


class RAGUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        self.headers = {
            "Authorization": "Bearer ck_load_test_key",
            "Content-Type": "application/json",
        }

    @task
    def send_rag_query(self):
        self.client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "What is the return policy?"}
                ],
                "user_id": "rag-load-test",
            },
            headers=self.headers,
        )

    @task
    def send_long_rag_query(self):
        self.client.post(
            "/v1/chat/completions",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "Explain the detailed shipping process "
                        "including international orders and customs handling",
                    }
                ],
                "user_id": "rag-load-test",
            },
            headers=self.headers,
        )
