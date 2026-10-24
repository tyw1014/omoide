"""Exercise the real SDK serializer against a local mock transport; no live keys."""
import json
from datetime import date

import httpx
import pytest

from ai_service import AIService, DEMO_LABEL, DemoProvider, GeminiProvider
from chapter_service import ChapterService
from memory_service import MemoryService
from models import MemoryInput
from recap_service import RecapService


def completion(content):
    return {
        "id": "gemini-test", "object": "chat.completion", "created": 0,
        "model": "gemini-3.8-flash",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
    }


def test_gemini_sdk_endpoint_and_structured_metadata(monkeypatch):
    requests = []

    def respond(request):
        requests.append(request)
        metadata = DemoProvider().extract("Basketball practice", "Court")
        return httpx.Response(200, json=completion(metadata.model_dump_json()))

    # Force the provider's real client constructor to use an in-process transport.
    from openai import OpenAI
    real_constructor = OpenAI
    constructor_options = []

    def local_client(**kwargs):
        constructor_options.append(kwargs)
        return real_constructor(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond)))

    monkeypatch.setattr("openai.OpenAI", local_client)
    provider = GeminiProvider("fake-gemini-key", consent=True)
    try:
        result = AIService(provider).extract("Basketball practice", "Court")
        assert result.mode == "Cloud AI · Google Gemini"
        assert result.value.location == "Court"
        assert len(requests) == 1
        request = requests[0]
        assert str(request.url) == "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        assert request.headers["authorization"] == "Bearer fake-gemini-key"
        body = json.loads(request.content)
        assert body["model"] == "gemini-3.8-flash"
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["strict"] is True
        assert json.loads(body["messages"][1]["content"]) == {"original": "Basketball practice", "user_location": "Court"}
        assert constructor_options[0]["timeout"] == 25.0
        assert constructor_options[0]["max_retries"] == 1
    finally:
        provider.client.close()


def test_gemini_requires_its_own_key():
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiProvider(None, consent=True)


def test_gemini_metadata_recap_and_chapter_integration(db, tmp_path):
    from unittest.mock import Mock
    from types import SimpleNamespace

    client = Mock()
    provider = GeminiProvider("fake-gemini-key", "gemini-custom-model", consent=True, client=client)
    ai = AIService(provider)
    metadata = DemoProvider().extract("Basketball practice", "Court")

    def output(value):
        client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(refusal=None, content=value.model_dump_json()))])

    output(metadata)
    service = MemoryService(db, tmp_path / "media", ai)
    eid = service.create(MemoryInput(content="Basketball practice", occurred_at=date(2026, 10, 10), location="Court"))
    assert db.get_entry(eid)["processing_mode"] == provider.label
    entries = db.list_entries()
    narrative = DemoProvider().narrate(entries, "My basketball story")
    output(narrative)
    recap = RecapService(db, ai).generate("Weekly", date(2026, 10, 10))
    assert recap.mode == provider.label and recap.value.source_ids() == [eid]
    cid = db.create_chapter("Basketball", "", [eid])
    ChapterService(db, ai).generate(cid)
    assert db.get_chapter(cid)["processing_mode"] == provider.label
    assert client.chat.completions.create.call_args.kwargs["model"] == "gemini-custom-model"

    # Structurally valid but invented citations must fall back before storage.
    invalid = narrative.model_copy(deep=True)
    invalid.overview.entry_ids = [999999]
    output(invalid)
    result = RecapService(db, ai).generate("Weekly", date(2026, 10, 10))
    assert result.mode == DEMO_LABEL
    assert result.value.source_ids() == [eid]


@pytest.mark.parametrize("status", [401, 429, 500])
def test_gemini_http_errors_fall_back_without_exposing_key(status):
    from openai import OpenAI

    def respond(request):
        return httpx.Response(status, json={"error": {"message": "private input fake-gemini-key"}})

    with OpenAI(api_key="fake-gemini-key", base_url=GeminiProvider.base_url, max_retries=0,
                http_client=httpx.Client(transport=httpx.MockTransport(respond))) as client:
        result = AIService(GeminiProvider("fake-gemini-key", consent=True, client=client)).extract("Basketball practice")
        assert result.mode == DEMO_LABEL
        assert "private input" not in result.note and "fake-gemini-key" not in result.note
