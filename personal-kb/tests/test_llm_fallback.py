import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from typing import Sequence, Any
from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    CompletionResponse,
    MessageRole,
    LLMMetadata,
)
from llama_index.core.llms.custom import CustomLLM

from generation.llm import (
    FallbackLLM,
    AllLLMsFailedError,
    MissingKeyLLM,
    get_llm,
    create_groq_llm,
    create_gemini_llm,
    create_openrouter_llm,
)
from config.settings import get_settings


class MockTestLLM(CustomLLM):
    name: str
    should_fail: bool = False
    failure_message: str = "Rate limit reached (429)"
    calls: int = 0

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(model_name=self.name)

    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        self.calls += 1
        if self.should_fail:
            raise RuntimeError(f"Error in {self.name}: {self.failure_message}")
        return ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content=f"Response from {self.name}",
            )
        )

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        self.calls += 1
        if self.should_fail:
            raise RuntimeError(f"Error in {self.name}: {self.failure_message}")
        return CompletionResponse(text=f"Completion from {self.name}")

    def stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any):
        self.calls += 1
        if self.should_fail:
            raise RuntimeError(f"Error in {self.name}: {self.failure_message}")
        yield ChatResponse(
            message=ChatMessage(
                role=MessageRole.ASSISTANT,
                content=f"Stream from {self.name}",
            )
        )

    def stream_complete(self, prompt: str, **kwargs: Any):
        self.calls += 1
        if self.should_fail:
            raise RuntimeError(f"Error in {self.name}: {self.failure_message}")
        yield CompletionResponse(text=f"Stream completion from {self.name}")


def test_default_fallback_order():
    """Verify that get_llm orders providers as groq -> gemini -> openrouter."""
    llm = get_llm(fallback_order=["groq", "gemini", "openrouter"])
    assert isinstance(llm, FallbackLLM)
    provider_names = [name for name, _ in llm.providers]
    assert provider_names == ["groq", "gemini", "openrouter"]


def test_groq_primary_success():
    """When Groq succeeds, it is used and subsequent providers are untouched."""
    groq_mock = MockTestLLM(name="groq", should_fail=False)
    gemini_mock = MockTestLLM(name="gemini", should_fail=False)
    openrouter_mock = MockTestLLM(name="openrouter", should_fail=False)

    fallback = FallbackLLM(
        providers=[
            ("groq", groq_mock),
            ("gemini", gemini_mock),
            ("openrouter", openrouter_mock),
        ]
    )

    resp = fallback.chat([ChatMessage(role=MessageRole.USER, content="Hello")])
    assert resp.message.content == "Response from groq"
    assert fallback.last_used_provider == "groq"
    assert groq_mock.calls == 1
    assert gemini_mock.calls == 0
    assert openrouter_mock.calls == 0


def test_groq_fails_gemini_fallback():
    """When Groq fails (e.g., rate limit 429), fallback routes seamlessly to Gemini."""
    groq_mock = MockTestLLM(name="groq", should_fail=True, failure_message="Rate limit 429")
    gemini_mock = MockTestLLM(name="gemini", should_fail=False)
    openrouter_mock = MockTestLLM(name="openrouter", should_fail=False)

    fallback = FallbackLLM(
        providers=[
            ("groq", groq_mock),
            ("gemini", gemini_mock),
            ("openrouter", openrouter_mock),
        ]
    )

    resp = fallback.chat([ChatMessage(role=MessageRole.USER, content="Hello")])
    assert resp.message.content == "Response from gemini"
    assert fallback.last_used_provider == "gemini"
    assert groq_mock.calls == 1
    assert gemini_mock.calls == 1
    assert openrouter_mock.calls == 0
    assert len(fallback.last_errors) == 1
    assert fallback.last_errors[0][0] == "groq"


def test_groq_and_gemini_fail_openrouter_fallback():
    """When Groq and Gemini fail, fallback routes to OpenRouter."""
    groq_mock = MockTestLLM(name="groq", should_fail=True, failure_message="Rate limit 429")
    gemini_mock = MockTestLLM(name="gemini", should_fail=True, failure_message="Quota exceeded")
    openrouter_mock = MockTestLLM(name="openrouter", should_fail=False)

    fallback = FallbackLLM(
        providers=[
            ("groq", groq_mock),
            ("gemini", gemini_mock),
            ("openrouter", openrouter_mock),
        ]
    )

    resp = fallback.chat([ChatMessage(role=MessageRole.USER, content="Hello")])
    assert resp.message.content == "Response from openrouter"
    assert fallback.last_used_provider == "openrouter"
    assert groq_mock.calls == 1
    assert gemini_mock.calls == 1
    assert openrouter_mock.calls == 1
    assert len(fallback.last_errors) == 2


def test_all_providers_fail_raises_exception():
    """When all providers fail, AllLLMsFailedError is raised with complete diagnostics."""
    groq_mock = MockTestLLM(name="groq", should_fail=True, failure_message="429 Too Many Requests")
    gemini_mock = MockTestLLM(name="gemini", should_fail=True, failure_message="Resource Exhausted")
    openrouter_mock = MockTestLLM(name="openrouter", should_fail=True, failure_message="Service Unavailable")

    fallback = FallbackLLM(
        providers=[
            ("groq", groq_mock),
            ("gemini", gemini_mock),
            ("openrouter", openrouter_mock),
        ]
    )

    with pytest.raises(AllLLMsFailedError) as exc_info:
        fallback.chat([ChatMessage(role=MessageRole.USER, content="Hello")])

    err_text = str(exc_info.value)
    assert "groq" in err_text
    assert "gemini" in err_text
    assert "openrouter" in err_text
    assert len(exc_info.value.errors) == 3


def test_missing_key_llm_cascades_gracefully():
    """MissingKeyLLM raises an error that allows the fallback chain to continue."""
    missing_groq = MissingKeyLLM(provider_name="groq", env_var_name="GROQ_API_KEY")
    gemini_mock = MockTestLLM(name="gemini", should_fail=False)

    fallback = FallbackLLM(
        providers=[
            ("groq", missing_groq),
            ("gemini", gemini_mock),
        ]
    )

    resp = fallback.chat([ChatMessage(role=MessageRole.USER, content="Test")])
    assert resp.message.content == "Response from gemini"
    assert fallback.last_used_provider == "gemini"
    assert len(fallback.last_errors) == 1
    assert "GROQ_API_KEY is not set" in fallback.last_errors[0][1]


def test_completion_fallback():
    """Text completion complete() also falls back properly."""
    groq_mock = MockTestLLM(name="groq", should_fail=True)
    gemini_mock = MockTestLLM(name="gemini", should_fail=False)

    fallback = FallbackLLM(providers=[("groq", groq_mock), ("gemini", gemini_mock)])
    res = fallback.complete("Test prompt")
    assert res.text == "Completion from gemini"
    assert fallback.last_used_provider == "gemini"


@pytest.mark.asyncio
async def test_async_chat_fallback():
    """Async chat achat() falls back properly across providers."""
    groq_mock = MockTestLLM(name="groq", should_fail=True)
    gemini_mock = MockTestLLM(name="gemini", should_fail=False)

    fallback = FallbackLLM(providers=[("groq", groq_mock), ("gemini", gemini_mock)])
    res = await fallback.achat([ChatMessage(role=MessageRole.USER, content="Hi")])
    assert res.message.content == "Response from gemini"
    assert fallback.last_used_provider == "gemini"


def test_streaming_fallback():
    """stream_chat() gracefully cascades to the fallback provider if primary fails."""
    groq_mock = MockTestLLM(name="groq", should_fail=True)
    gemini_mock = MockTestLLM(name="gemini", should_fail=False)

    fallback = FallbackLLM(providers=[("groq", groq_mock), ("gemini", gemini_mock)])
    gen = fallback.stream_chat([ChatMessage(role=MessageRole.USER, content="Stream test")])
    chunks = list(gen)
    assert len(chunks) == 1
    assert chunks[0].message.content == "Stream from gemini"
    assert fallback.last_used_provider == "gemini"


def test_generation_service_integration():
    """Verify GenerationService tracks fallback provider in debug metadata."""
    from unittest.mock import MagicMock
    from generation.answer import GenerationService
    from models.query import ParsedQuery, QueryType, SourceCitation

    mock_retrieval = MagicMock()
    mock_parsed_query = ParsedQuery(
        original_query="What is the database decision?",
        semantic_query="database decision",
        query_type=QueryType.CURRENT_STATE,
    )
    citation = SourceCitation(
        id=1,
        document_id="doc1",
        chunk_id="chunk1",
        source="doc1.md",
        snippet="We decided on PostgreSQL.",
        valid_from="2026-01-01T00:00:00Z",
    )
    mock_retrieval.retrieve_context.return_value = (
        "We decided on PostgreSQL.",
        [citation],
        mock_parsed_query,
        None,
    )

    groq_mock = MockTestLLM(name="groq", should_fail=True)
    gemini_mock = MockTestLLM(name="gemini", should_fail=False)
    fallback = FallbackLLM(providers=[("groq", groq_mock), ("gemini", gemini_mock)])

    service = GenerationService(retrieval_service=mock_retrieval, llm=fallback)
    response = service.generate_answer(query="What is the database decision?", debug=True)

    assert response.answer == "Response from gemini"
    assert response.debug_info["llm_provider"] == "gemini"
    assert response.debug_info["fallback_errors"] is not None
    assert response.debug_info["fallback_errors"][0][0] == "groq"

