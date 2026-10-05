from datetime import datetime
import logging
from typing import Any, Dict, Optional
from llama_index.core.base.llms.types import ChatMessage, MessageRole

from models.query import QueryResponse, QueryType
from retrieval.service import RetrievalService
from .llm import get_llm
from .prompts import GROUNDED_SYSTEM_PROMPT, GROUNDED_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)


class GenerationService:
    """
    Executes grounded RAG generation with provenance tracking and strict temporal adherence.
    """

    def __init__(
        self,
        retrieval_service: Optional[RetrievalService] = None,
        llm: Optional[Any] = None,
    ):
        self.retrieval_service = retrieval_service or RetrievalService()
        self.llm = llm or get_llm()

    def generate_answer(
        self,
        query: str,
        top_k: Optional[int] = None,
        reference_date: Optional[datetime] = None,
        debug: bool = False,
    ) -> QueryResponse:
        # 1. Retrieve grounded context and citations
        context, citations, parsed_query, qdrant_filter = self.retrieval_service.retrieve_context(
            query=query,
            top_k=top_k,
            reference_date=reference_date,
        )

        # 2. Strict grounding guard: If no relevant evidence was retrieved
        if not citations or not context.strip():
            logger.info("No matching evidence found in knowledge base.")
            return QueryResponse(
                answer="I couldn't find enough information in the knowledge base to answer that. The knowledge base does not contain sufficient evidence for this query.",
                citations=[],
                sources=[],
                query_type=parsed_query.query_type,
                temporal_filter=qdrant_filter.model_dump(exclude_none=True) if qdrant_filter else None,
                debug_info={"reason": "No retrieved context points after filtering"} if debug else None,
                metadata={"provider": getattr(self.llm, "last_used_provider", "none"), "citations_count": 0},
            )

        # 3. Format grounded prompt
        user_content = GROUNDED_USER_PROMPT_TEMPLATE.format(
            context=context,
            question=query,
        )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=GROUNDED_SYSTEM_PROMPT),
            ChatMessage(role=MessageRole.USER, content=user_content),
        ]

        # 4. Generate answer via fallback LLM chain
        try:
            response = self.llm.chat(messages)
            raw_answer = response.message.content.strip()
        except Exception as e:
            logger.error(f"Error calling LLM: {e}", exc_info=True)
            raw_answer = f"Error generating answer: {str(e)}"

        provider_used = getattr(self.llm, "last_used_provider", None)
        fallback_errors = getattr(self.llm, "last_errors", [])
        if provider_used:
            logger.info(f"Answer successfully produced by LLM provider: {provider_used}")

        if debug:
            debug_payload = {
                "original_query": parsed_query.original_query,
                "semantic_query": parsed_query.semantic_query,
                "query_type": parsed_query.query_type.value,
                "temporal_range": parsed_query.temporal_range.model_dump() if parsed_query.temporal_range else None,
                "filter": qdrant_filter.model_dump(exclude_none=True) if qdrant_filter else None,
                "context_length": len(context),
                "llm_provider": provider_used,
                "fallback_errors": fallback_errors if fallback_errors else None,
            }
        elif provider_used:
            debug_payload = {
                "llm_provider": provider_used,
            }
        else:
            debug_payload = None

        metadata = {
            "query_type": parsed_query.query_type.value,
            "provider": provider_used or "unknown",
            "citations_count": len(citations),
        }

        return QueryResponse(
            answer=raw_answer,
            citations=citations,
            sources=citations,
            query_type=parsed_query.query_type,
            temporal_filter=qdrant_filter.model_dump(exclude_none=True) if qdrant_filter else None,
            debug_info=debug_payload,
            metadata=metadata,
        )
