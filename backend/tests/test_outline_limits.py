import json
import unittest

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.dependencies import get_outline_generator, get_template_store
from app.main import app
from app.schemas.outline import OutlineRequest
from app.schemas.slide import SlideData, SlideStatus, SlideType
from app.services.outline_generator import OutlineGenerator


class _StubLLMClient:
    async def chat(self, *args, **kwargs):
        return "[]"


class _StubOutlineGenerator:
    def __init__(self, slide_count: int) -> None:
        self.llm_client = _StubLLMClient()
        self.chat_model = "test"
        self.slide_count = slide_count

    def _outline_prompt(self, text, slide_count, template_name):
        return []

    def _parse_slides_json(self, payload, session_id=None):
        slides = []
        for index in range(self.slide_count):
            slide_type = SlideType.cover if index == 0 else SlideType.ending if index == self.slide_count - 1 else SlideType.content
            slides.append(
                SlideData(
                    page_num=index + 1,
                    type=slide_type,
                    title=f"Slide {index + 1}",
                    content_text="content",
                    visual_desc="visual",
                    status=SlideStatus.pending,
                )
            )
        return slides


class _StubTemplateStore:
    def get_template(self, template_id):
        return None


class OutlineLimitTests(unittest.TestCase):
    def test_outline_request_allows_45_slides(self) -> None:
        try:
            payload = OutlineRequest(text="test", slide_count=45)
        except ValidationError as exc:  # pragma: no cover - exercised in red phase
            self.fail(f"45 slides should be accepted, but validation failed: {exc}")

        self.assertEqual(payload.slide_count, 45)

    def test_fallback_generation_keeps_requested_slide_count(self) -> None:
        generator = OutlineGenerator(llm_client=object(), chat_model="test")

        slides = generator._fallback_generate("paragraph 1\n\nparagraph 2", 45, None)

        self.assertEqual(len(slides), 45)

    def test_generate_stream_route_accepts_45_slides(self) -> None:
        app.dependency_overrides[get_outline_generator] = lambda: _StubOutlineGenerator(45)
        app.dependency_overrides[get_template_store] = lambda: _StubTemplateStore()

        try:
            client = TestClient(app)
            response = client.post("/api/outline/generate-stream", json={"text": "test", "slide_count": 45})
        finally:
            app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)

        payloads = [
            json.loads(line[6:])
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        slide_messages = [payload for payload in payloads if payload.get("type") == "slide"]

        self.assertEqual(len(slide_messages), 45)
        self.assertTrue(any(payload.get("type") == "complete" for payload in payloads))


if __name__ == "__main__":
    unittest.main()
