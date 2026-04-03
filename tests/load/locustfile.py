"""Load test — simulate concurrent chat users.

Usage:
    locust -f tests/load/locustfile.py --host http://localhost:8000
"""
from locust import HttpUser, task, between


class ChatUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.headers = {
            "Authorization": "Bearer ck_load_test_key",
            "Content-Type": "application/json",
        }

    @task(3)
    def send_chat_message(self):
        self.client.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "user_id": "load-test",
            },
            headers=self.headers,
        )

    @task(1)
    def check_health(self):
        self.client.get("/health")
