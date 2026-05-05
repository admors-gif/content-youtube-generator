import unittest

from scripts.sentry_observability import sanitize_sentry_event


class SentryObservabilityTests(unittest.TestCase):
    def test_sanitizer_redacts_sensitive_payload_without_losing_project_context(self):
        event = {
            "request": {
                "headers": {
                    "Authorization": "Bearer secret-token",
                    "X-Admin-Token": "admin-token",
                    "Content-Type": "application/json",
                },
                "url": "https://api.example.com/produce?token=secret&projectId=abc",
                "query_string": "token=secret&projectId=abc",
            },
            "extra": {
                "project_id": "project_123",
                "firebase_credentials": "{\"private_key\":\"secret\"}",
                "nested": {"api_key": "secret-key", "safe": "kept"},
            },
            "tags": {"project_id": "project_123"},
        }

        sanitized = sanitize_sentry_event(event, hint={})

        self.assertEqual(sanitized["request"]["headers"]["Authorization"], "[Filtered]")
        self.assertEqual(sanitized["request"]["headers"]["X-Admin-Token"], "[Filtered]")
        self.assertEqual(sanitized["request"]["headers"]["Content-Type"], "application/json")
        self.assertEqual(sanitized["request"]["url"], "https://api.example.com/produce?[Filtered]")
        self.assertEqual(sanitized["request"]["query_string"], "[Filtered]")
        self.assertEqual(sanitized["extra"]["firebase_credentials"], "[Filtered]")
        self.assertEqual(sanitized["extra"]["nested"]["api_key"], "[Filtered]")
        self.assertEqual(sanitized["extra"]["nested"]["safe"], "kept")
        self.assertEqual(sanitized["tags"]["project_id"], "project_123")


if __name__ == "__main__":
    unittest.main()
