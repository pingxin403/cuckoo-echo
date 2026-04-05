"""Load test — simulate concurrent chat users.

Usage:
    # Full test (includes LLM calls — slow with local Ollama):
    locust -f tests/load/locustfile.py --host http://localhost --headless -u 5 -r 1 --run-time 120s

    # API-only test (no LLM, fast):
    locust -f tests/load/locustfile.py --host http://localhost --headless -u 50 -r 10 --run-time 30s --tags api
"""
from locust import HttpUser, task, between, tag


class ChatUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.headers = {
            "Authorization": "Bearer ck_test_integration_key",
            "Content-Type": "application/json",
        }
        # Login to get admin token
        resp = self.client.post(
            "/admin/v1/auth/login",
            json={"email": "admin@test.com", "password": "test123456"},
        )
        if resp.status_code == 200:
            self.admin_token = resp.json().get("access_token", "")
        else:
            self.admin_token = ""

    @task(2)
    def send_chat_message(self):
        """SSE chat — slow with local Ollama (10-30s per request)."""
        self.client.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Hello"}], "user_id": "load-test"},
            headers=self.headers,
            timeout=120,
        )

    @task(3)
    @tag("api")
    def check_health(self):
        self.client.get("/nginx-health")

    @task(2)
    @tag("api")
    def get_metrics(self):
        if self.admin_token:
            self.client.get(
                "/admin/v1/metrics/overview?range=7d",
                headers={"Authorization": f"Bearer {self.admin_token}"},
            )

    @task(1)
    @tag("api")
    def list_knowledge_docs(self):
        if self.admin_token:
            self.client.get(
                "/admin/v1/knowledge/docs",
                headers={"Authorization": f"Bearer {self.admin_token}"},
            )
