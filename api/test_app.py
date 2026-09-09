import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from api.app import REPORT_PATH, app, create_app


class ApiTests(unittest.TestCase):
    def test_health_and_real_report(self):
        with TestClient(app) as client:
            response = client.get("/api/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {"status": "ok", "service": "DataAgent API"})
            response = client.get("/api/analysis/latest")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), json.loads(REPORT_PATH.read_text(encoding="utf-8")))

    def test_missing_invalid_and_updated_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.json"
            with TestClient(create_app(path)) as client:
                response = client.get("/api/analysis/latest")
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"detail": "Nenhuma análise disponível."})
                for invalid in ["{", "[]", '{"value": NaN}']:
                    path.write_text(invalid, encoding="utf-8")
                    self.assertEqual(client.get("/api/analysis/latest").status_code, 500)
                for value in [1, 2]:
                    path.write_text(json.dumps({"value": value}), encoding="utf-8")
                    self.assertEqual(client.get("/api/analysis/latest").json(), {"value": value})

    def test_cors(self):
        with TestClient(app) as client:
            for origin in ["http://localhost:5173", "http://127.0.0.1:5173"]:
                response = client.get("/api/health", headers={"Origin": origin})
                self.assertEqual(response.headers["access-control-allow-origin"], origin)
                response = client.options("/api/analysis/latest", headers={
                    "Origin": origin, "Access-Control-Request-Method": "GET",
                })
                self.assertEqual(response.status_code, 200)
            response = client.get("/api/health", headers={"Origin": "https://example.com"})
            self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
