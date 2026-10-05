import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock

from models.query import Citation, QueryType, ParsedQuery, TemporalRange, RAGResponse, QueryResponse
from generation.answer import GenerationService
from generation.llm import FallbackLLM
from generation.prompts import GROUNDED_SYSTEM_PROMPT, GROUNDED_USER_PROMPT_TEMPLATE
from llama_index.core.base.llms.types import ChatMessage, ChatResponse, MessageRole, LLMMetadata
from llama_index.core.llms.custom import CustomLLM


class MockGroundedLLM(CustomLLM):
    name: str = "openrouter"

    @property
    def metadata(self) -> LLMMetadata:
        return LLMMetadata(model_name=self.name)

    def chat(self, messages, **kwargs):
        user_msg = next((m.content for m in messages if m.role == MessageRole.USER), "")
        
        if "database" in user_msg.lower() and "current" in user_msg.lower():
            content = (
                "# Current Database Decision\n\n"
                "The current production database is **PostgreSQL**. [1]\n\n"
                "> **Current decision:** PostgreSQL confirmed as production on August 10, 2026. [1]"
            )
        elif "prototype" in user_msg.lower():
            content = (
                "## Prototype Database Decision\n\n"
                "**SQLite** was used temporarily for the prototype on May 20, 2026. [1]"
            )
        elif "may 2026" in user_msg.lower() or "in may" in user_msg.lower():
            content = (
                "## Decision in May 2026\n\n"
                "On May 20, 2026, you decided to use **SQLite** temporarily for the prototype. [1]"
            )
        elif "vector database" in user_msg.lower():
            content = (
                "## Vector Database\n\n"
                "The project uses **Qdrant** as the vector database for dense retrieval. [1]"
            )
        elif "architecture" in user_msg.lower():
            content = (
                "# Project Architecture\n\n"
                "Your project currently uses **LlamaIndex** for ingestion and retrieval, with **Qdrant** as the vector database and **Ollama** for local inference. [1]\n\n"
                "## Database Component\n\n"
                "The current production database is **PostgreSQL**. [2]"
            )
        else:
            content = "The knowledge base does not contain sufficient evidence to answer this question."

        return ChatResponse(message=ChatMessage(role=MessageRole.ASSISTANT, content=content))

    def complete(self, prompt, **kwargs):
        pass
    def stream_complete(self, prompt, **kwargs):
        pass


@pytest.fixture
def mock_llm():
    mock = MockGroundedLLM()
    return FallbackLLM(providers=[("openrouter", mock)])


def test_citation_model_schema():
    """Verify Citation model structure conforming to requirement."""
    citation = Citation(
        id=1,
        source="database_decision.md",
        title="Database Decision",
        chunk_id="chunk_42",
        score=0.91,
        snippet="PostgreSQL confirmed as production on August 10, 2026.",
        created_at="2026-08-10",
        document_type="decision",
        status="active",
        event_at="2026-08-10T00:00:00Z",
    )
    assert citation.id == 1
    assert citation.source == "database_decision.md"
    assert citation.title == "Database Decision"
    assert citation.status == "active"
    assert citation.score == 0.91


def test_rag_response_schema():
    """Verify RAGResponse model with structured citations."""
    cit = Citation(
        id=1,
        source="rag_project.md",
        title="Personal Knowledge Base",
        snippet="Uses LlamaIndex and Qdrant.",
        status="active",
    )
    resp = RAGResponse(
        answer="The project uses **Qdrant** as its vector database. [1]",
        citations=[cit],
        metadata={"provider": "openrouter", "query_type": "SEMANTIC"},
    )
    assert resp.citations[0].id == 1
    assert "[1]" in resp.answer
    assert resp.metadata["provider"] == "openrouter"


def test_current_database_decision(mock_llm):
    """Test 1: 'What database am I currently using?' -> PostgreSQL active."""
    mock_retrieval = MagicMock()
    cit = Citation(
        id=1,
        source="database_decision.md",
        title="Database Decision",
        chunk_id="c1",
        score=0.95,
        snippet="On August 10, 2026, I confirmed that PostgreSQL remains the production database.",
        status="active",
        event_at="2026-08-10T00:00:00Z",
    )
    mock_retrieval.retrieve_context.return_value = (
        "[1] Source: database_decision.md | Status: ACTIVE | Date: 2026-08-10\nPostgreSQL confirmed as production.",
        [cit],
        ParsedQuery(original_query="What database am I currently using?", semantic_query="database", query_type=QueryType.CURRENT_STATE),
        None,
    )

    svc = GenerationService(retrieval_service=mock_retrieval, llm=mock_llm)
    res = svc.generate_answer("What is my current production database decision?")

    assert "postgresql" in res.answer.lower()
    assert "[1]" in res.answer
    assert len(res.citations) == 1
    assert res.citations[0].status == "active"
    assert res.citations[0].source == "database_decision.md"


def test_prototype_database_decision(mock_llm):
    """Test 2: 'What database did I use for the prototype?' -> SQLite."""
    mock_retrieval = MagicMock()
    cit = Citation(
        id=1,
        source="database_decision.md",
        title="Database Decision",
        chunk_id="c2",
        score=0.88,
        snippet="On May 20, 2026, I decided to use SQLite temporarily for the prototype.",
        status="superseded",
        event_at="2026-05-20T00:00:00Z",
    )
    mock_retrieval.retrieve_context.return_value = (
        "[1] Source: database_decision.md | Status: SUPERSEDED | Date: 2026-05-20\nSQLite temporarily for prototype.",
        [cit],
        ParsedQuery(original_query="What database did I use for the prototype?", semantic_query="prototype database", query_type=QueryType.HISTORICAL),
        None,
    )

    svc = GenerationService(retrieval_service=mock_retrieval, llm=mock_llm)
    res = svc.generate_answer("What database did I use for the prototype?")

    assert "sqlite" in res.answer.lower()
    assert "[1]" in res.answer
    assert res.citations[0].status == "superseded"


def test_may_2026_decision(mock_llm):
    """Test 3: 'What did I decide on in May 2026?' -> SQLite on May 20, 2026."""
    mock_retrieval = MagicMock()
    cit = Citation(
        id=1,
        source="database_decision.md",
        title="Database Decision",
        chunk_id="c3",
        snippet="On May 20, 2026, I decided to use SQLite temporarily for the prototype.",
        status="superseded",
        event_at="2026-05-20T00:00:00Z",
    )
    mock_retrieval.retrieve_context.return_value = (
        "[1] Source: database_decision.md | Status: SUPERSEDED | Date: 2026-05-20\nSQLite temporarily for prototype.",
        [cit],
        ParsedQuery(original_query="What did I decide on in May 2026?", semantic_query="decide May 2026", query_type=QueryType.TEMPORAL),
        None,
    )

    svc = GenerationService(retrieval_service=mock_retrieval, llm=mock_llm)
    res = svc.generate_answer("What did I decide on in May 2026?")

    assert "sqlite" in res.answer.lower()
    assert "may 20" in res.answer.lower()
    assert "[1]" in res.answer


def test_vector_database_query(mock_llm):
    """Test 4: 'What vector database does the project use?' -> Qdrant."""
    mock_retrieval = MagicMock()
    cit = Citation(
        id=1,
        source="rag_project.md",
        title="Personal Knowledge Base",
        snippet="Qdrant is used as the vector database.",
        status="active",
    )
    mock_retrieval.retrieve_context.return_value = (
        "[1] Source: rag_project.md | Status: ACTIVE\nQdrant is used as the vector database.",
        [cit],
        ParsedQuery(original_query="What vector database does the project use?", semantic_query="vector database", query_type=QueryType.SEMANTIC),
        None,
    )

    svc = GenerationService(retrieval_service=mock_retrieval, llm=mock_llm)
    res = svc.generate_answer("What vector database does the project use?")

    assert "qdrant" in res.answer.lower()
    assert "[1]" in res.answer


def test_project_architecture_multi_citation(mock_llm):
    """Test 5: 'What is the project architecture?' -> Markdown with [1] and [2] citations."""
    mock_retrieval = MagicMock()
    cit1 = Citation(
        id=1,
        source="rag_project.md",
        title="Personal Knowledge Base",
        snippet="Uses LlamaIndex, Qdrant, and Ollama.",
        status="active",
    )
    cit2 = Citation(
        id=2,
        source="database_decision.md",
        title="Database Decision",
        snippet="PostgreSQL confirmed as production.",
        status="active",
    )
    mock_retrieval.retrieve_context.return_value = (
        "[1] Source: rag_project.md\nUses LlamaIndex and Qdrant.\n\n[2] Source: database_decision.md\nPostgreSQL is production.",
        [cit1, cit2],
        ParsedQuery(original_query="What is the project architecture?", semantic_query="architecture", query_type=QueryType.SEMANTIC),
        None,
    )

    svc = GenerationService(retrieval_service=mock_retrieval, llm=mock_llm)
    res = svc.generate_answer("What is the project architecture?")

    assert "#" in res.answer
    assert "[1]" in res.answer
    assert "[2]" in res.answer
    assert len(res.citations) == 2
    assert res.citations[0].id == 1
    assert res.citations[1].id == 2


def test_out_of_range_insufficient_evidence(mock_llm):
    """Test 6: Out of knowledge query -> clearly states information is unavailable."""
    mock_retrieval = MagicMock()
    mock_retrieval.retrieve_context.return_value = (
        "",
        [],
        ParsedQuery(original_query="Tell me about quantum physics in 1920", semantic_query="quantum", query_type=QueryType.TEMPORAL),
        None,
    )

    svc = GenerationService(retrieval_service=mock_retrieval, llm=mock_llm)
    res = svc.generate_answer("Tell me about quantum physics in 1920")

    assert "couldn't find" in res.answer.lower() or "sufficient evidence" in res.answer.lower()
    assert len(res.citations) == 0
