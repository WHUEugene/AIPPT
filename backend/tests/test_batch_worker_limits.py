import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.dependencies import get_settings
from app.main import app
from app.routers.slide import get_batch_generator


class _StubBatchGenerator:
    def __init__(self) -> None:
        self.calls = []
        self.batch_id = uuid4()

    def create_batch(self, *, slides, style_prompt, max_workers, aspect_ratio):
        self.calls.append(
            {
                "slides_count": len(slides),
                "style_prompt": style_prompt,
                "max_workers": max_workers,
                "aspect_ratio": aspect_ratio,
            }
        )
        return self.batch_id

    def get_batch_status(self, batch_id):
        return SimpleNamespace(
            status="completed",
            successful=1,
            failed=0,
            results=[],
        )


class BatchWorkerLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.batch_generator = _StubBatchGenerator()
        app.dependency_overrides[get_batch_generator] = lambda: self.batch_generator
        app.dependency_overrides[get_settings] = lambda: SimpleNamespace(
            batch_max_workers=20,
            batch_max_concurrent=10,
        )
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def _make_payload(self, *, max_workers):
        payload = {
            "slides": [
                {
                    "id": str(uuid4()),
                    "page_num": index + 1,
                    "type": "content",
                    "title": f"Slide {index + 1}",
                    "content_text": "content",
                    "visual_desc": "visual",
                    "status": "pending",
                }
                for index in range(45)
            ],
            "style_prompt": "style",
            "aspect_ratio": "16:9",
        }
        if max_workers is not None:
            payload["max_workers"] = max_workers
        return payload

    def test_batch_generate_caps_explicit_worker_count_at_maximum(self) -> None:
        response = self.client.post("/api/slide/batch/generate", json=self._make_payload(max_workers=45))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.batch_generator.calls[0]["max_workers"], 20)

    def test_batch_generate_caps_default_worker_count_at_maximum(self) -> None:
        response = self.client.post("/api/slide/batch/generate", json=self._make_payload(max_workers=None))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.batch_generator.calls[0]["max_workers"], 20)


if __name__ == "__main__":
    unittest.main()
