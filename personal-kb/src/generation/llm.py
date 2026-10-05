import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple
from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseAsyncGen,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseAsyncGen,
    CompletionResponseGen,
    LLMMetadata,
)
from llama_index.core.llms.custom import CustomLLM
from llama_index.core.llms.llm import LLM
from llama_index.llms.openai import OpenAI
from llama_index.llms.ollama import Ollama
from pydantic import Field, PrivateAttr

from config.settings import get_settings

logger = logging.getLogger(__name__)


class AllLLMsFailedError(RuntimeError):
    """Raised when every LLM provider in the fallback chain fails."""

    def __init__(self, message: str, errors: List[Tuple[str, str]]):
        super().__init__(message)
        self.errors = errors


class MissingKeyLLM(CustomLLM):
    """
    Placeholder LLM used when an API key is not configured.
    Immediately raises a descriptive ValueError upon any invocation so
    the FallbackLLM can gracefully move to the next provider.
    """

    provider_name: str
    env_var_name: str

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(model_name=f"{self.provider_name}-unconfigured")

    def _fail(self):
        raise ValueError(
            f"Provider '{self.provider_name}' is not configured: "
            f"{self.env_var_name} is not set in environment or .env"
        )

    def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
        self._fail()

    def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
        self._fail()

    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        self._fail()

    def stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseGen:
        self._fail()


class FallbackLLM(CustomLLM):
    """
    LLM wrapper that executes a sequence of LLM providers in prioritized order.
    If the primary provider fails (e.g. rate limit, quota, timeout, network error,
    or missing credentials), execution seamlessly cascades to the next provider.

    Default Order:
    1. Groq
    2. Gemini
    3. OpenRouter
    """

    providers: List[Tuple[str, Any]] = Field(default_factory=list)
    _last_used_provider: Optional[str] = PrivateAttr(default=None)
    _last_errors: List[Tuple[str, str]] = PrivateAttr(default_factory=list)

    @property
    def metadata(self) -> LLMMetadata:
        provider_names = [name for name, _ in self.providers]
        chain_str = " -> ".join(provider_names) if provider_names else "empty"
        active_model = self._last_used_provider or (provider_names[0] if provider_names else "none")
        return LLMMetadata(
            model_name=f"fallback[{active_model}] (chain: {chain_str})"
        )

    @property
    def last_used_provider(self) -> Optional[str]:
        """Returns the name of the LLM provider that successfully fulfilled the last call."""
        return self._last_used_provider

    @property
    def last_errors(self) -> List[Tuple[str, str]]:
        """Returns the list of (provider_name, error_message) from the last execution."""
        return self._last_errors

    def _handle_all_failed(self, operation: str) -> AllLLMsFailedError:
        error_lines = [f"  - {name}: {err}" for name, err in self._last_errors]
        summary = "\n".join(error_lines)
        msg = (
            f"All LLM providers in fallback chain failed during {operation}:\n"
            f"{summary}\n"
            f"Please verify API keys and quotas for GROQ_API_KEY, GEMINI_API_KEY, and OPENROUTER_API_KEY."
        )
        logger.error(msg)
        return AllLLMsFailedError(msg, self._last_errors)

    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        self._last_errors = []
        for name, provider in self.providers:
            try:
                logger.info(f"Attempting chat generation with LLM provider: '{name}'")
                response = provider.chat(messages, **kwargs)
                self._last_used_provider = name
                logger.info(f"Successfully generated answer with LLM provider: '{name}'")
                return response
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                logger.warning(
                    f"LLM provider '{name}' failed during chat: {err_msg}. "
                    f"Falling back to next provider in chain..."
                )
                self._last_errors.append((name, err_msg))

        raise self._handle_all_failed("chat")

    def complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponse:
        self._last_errors = []
        for name, provider in self.providers:
            try:
                logger.info(f"Attempting text completion with LLM provider: '{name}'")
                response = provider.complete(prompt, formatted=formatted, **kwargs)
                self._last_used_provider = name
                logger.info(f"Successfully completed text with LLM provider: '{name}'")
                return response
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                logger.warning(
                    f"LLM provider '{name}' failed during complete: {err_msg}. "
                    f"Falling back to next provider in chain..."
                )
                self._last_errors.append((name, err_msg))

        raise self._handle_all_failed("complete")

    def stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseGen:
        self._last_errors = []
        for name, provider in self.providers:
            try:
                logger.info(f"Attempting stream_chat with LLM provider: '{name}'")
                gen = provider.stream_chat(messages, **kwargs)
                first_chunk = next(gen)
                self._last_used_provider = name
                logger.info(f"Streaming initiated with LLM provider: '{name}'")

                def _wrapper():
                    yield first_chunk
                    yield from gen

                return _wrapper()
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                logger.warning(
                    f"LLM provider '{name}' failed stream_chat: {err_msg}. "
                    f"Falling back to next provider in chain..."
                )
                self._last_errors.append((name, err_msg))

        raise self._handle_all_failed("stream_chat")

    def stream_complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponseGen:
        self._last_errors = []
        for name, provider in self.providers:
            try:
                logger.info(f"Attempting stream_complete with LLM provider: '{name}'")
                gen = provider.stream_complete(prompt, formatted=formatted, **kwargs)
                first_chunk = next(gen)
                self._last_used_provider = name
                logger.info(f"Streaming complete initiated with LLM provider: '{name}'")

                def _wrapper():
                    yield first_chunk
                    yield from gen

                return _wrapper()
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                logger.warning(
                    f"LLM provider '{name}' failed stream_complete: {err_msg}. "
                    f"Falling back to next provider in chain..."
                )
                self._last_errors.append((name, err_msg))

        raise self._handle_all_failed("stream_complete")

    async def achat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        self._last_errors = []
        for name, provider in self.providers:
            try:
                logger.info(f"Attempting async chat with LLM provider: '{name}'")
                if hasattr(provider, "achat") and callable(provider.achat):
                    response = await provider.achat(messages, **kwargs)
                else:
                    response = provider.chat(messages, **kwargs)
                self._last_used_provider = name
                logger.info(f"Successfully generated async answer with LLM provider: '{name}'")
                return response
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                logger.warning(
                    f"LLM provider '{name}' failed during achat: {err_msg}. "
                    f"Falling back to next provider in chain..."
                )
                self._last_errors.append((name, err_msg))

        raise self._handle_all_failed("achat")

    async def acomplete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponse:
        self._last_errors = []
        for name, provider in self.providers:
            try:
                logger.info(f"Attempting async completion with LLM provider: '{name}'")
                if hasattr(provider, "acomplete") and callable(provider.acomplete):
                    response = await provider.acomplete(prompt, formatted=formatted, **kwargs)
                else:
                    response = provider.complete(prompt, formatted=formatted, **kwargs)
                self._last_used_provider = name
                logger.info(f"Successfully completed async text with LLM provider: '{name}'")
                return response
            except Exception as e:
                err_msg = f"{type(e).__name__}: {str(e)}"
                logger.warning(
                    f"LLM provider '{name}' failed during acomplete: {err_msg}. "
                    f"Falling back to next provider in chain..."
                )
                self._last_errors.append((name, err_msg))

        raise self._handle_all_failed("acomplete")

    @classmethod
    def class_name(cls) -> str:
        return "fallback_llm"


def create_groq_llm(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 120.0,
    temperature: float = 0.0,
) -> LLM:
    """Instantiate Groq LLM client via OpenAI-compatible endpoint."""
    settings = get_settings()
    key = api_key or settings.groq_api_key
    if not key or not key.strip():
        return MissingKeyLLM(provider_name="groq", env_var_name="GROQ_API_KEY")

    return OpenAI(
        model=model or settings.groq_model,
        api_key=key.strip(),
        api_base=base_url or settings.groq_base_url,
        request_timeout=timeout,
        temperature=temperature,
    )


def create_gemini_llm(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 120.0,
    temperature: float = 0.0,
) -> LLM:
    """Instantiate Google Gemini LLM client via official OpenAI-compatible endpoint."""
    settings = get_settings()
    key = api_key or settings.gemini_api_key
    if not key or not key.strip():
        return MissingKeyLLM(provider_name="gemini", env_var_name="GEMINI_API_KEY")

    return OpenAI(
        model=model or settings.gemini_model,
        api_key=key.strip(),
        api_base=base_url or settings.gemini_base_url,
        request_timeout=timeout,
        temperature=temperature,
    )


def create_openrouter_llm(
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 120.0,
    temperature: float = 0.0,
) -> LLM:
    """Instantiate OpenRouter LLM client via OpenAI-compatible endpoint."""
    settings = get_settings()
    key = api_key or settings.openrouter_api_key
    if not key or not key.strip():
        return MissingKeyLLM(provider_name="openrouter", env_var_name="OPENROUTER_API_KEY")

    return OpenAI(
        model=model or settings.openrouter_model,
        api_key=key.strip(),
        api_base=base_url or settings.openrouter_base_url,
        request_timeout=timeout,
        temperature=temperature,
        default_headers={
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Personal-Knowledge-Base",
        },
    )


def create_ollama_llm(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 120.0,
    temperature: float = 0.0,
) -> Ollama:
    """Instantiate local Ollama LLM."""
    settings = get_settings()
    return Ollama(
        model=model or settings.llm_model,
        base_url=base_url or settings.ollama_base_url,
        request_timeout=timeout,
        temperature=temperature,
        additional_kwargs={"temperature": temperature},
    )


def get_llm(
    fallback_order: Optional[List[str]] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: float = 120.0,
    temperature: float = 0.0,
) -> FallbackLLM:
    """
    Constructs and returns a FallbackLLM configured strictly in the order:
    1. Groq
    2. Gemini
    3. OpenRouter
    (and optional local Ollama fallback if enabled).

    Falls through in exact priority if rate-limited, quota-limited, timed out, or unconfigured.
    """
    settings = get_settings()
    order = fallback_order or settings.llm_fallback_order

    factories = {
        "groq": lambda: create_groq_llm(
            model=model if model and "llama" in model.lower() else None,
            base_url=base_url if base_url and "groq" in base_url else None,
            timeout=timeout,
            temperature=temperature,
        ),
        "gemini": lambda: create_gemini_llm(
            model=model if model and "gemini" in model.lower() else None,
            base_url=base_url if base_url and "google" in base_url else None,
            timeout=timeout,
            temperature=temperature,
        ),
        "openrouter": lambda: create_openrouter_llm(
            model=model if model and ("/" in model or "openrouter" in model) else None,
            base_url=base_url if base_url and "openrouter" in base_url else None,
            timeout=timeout,
            temperature=temperature,
        ),
        "ollama": lambda: create_ollama_llm(
            model=model if model and "llama" in model.lower() else None,
            base_url=base_url if base_url and "localhost" in base_url else None,
            timeout=timeout,
            temperature=temperature,
        ),
    }

    providers: List[Tuple[str, LLM]] = []
    for provider_name in order:
        key = provider_name.strip().lower()
        if key in factories:
            providers.append((key, factories[key]()))

    # Optional local Ollama fallback if enabled in settings and caller did not specify explicit order
    if fallback_order is None and settings.enable_ollama_fallback and "ollama" not in [name for name, _ in providers]:
        providers.append(("ollama", factories["ollama"]()))

    return FallbackLLM(providers=providers)