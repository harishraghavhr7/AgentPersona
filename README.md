# Personal Knowledge Base with Temporal Memory

A local-first, production-grade Grounded Retrieval-Augmented Generation (RAG) system with temporal indexing, document versioning, knowledge supersession, and traceable source provenance.

---

## 🌟 Key Capabilities

1. **Semantic Meaning**: Dense vector search powered by local Ollama embeddings (`embeddinggemma`).
2. **Deterministic Event Time**: Extracts explicit decision dates (e.g. `2026-03-15`, `March 15, 2026`) directly into typed Qdrant datetime payloads (`event_at`).
3. **Knowledge Validity Windows**: Maintains `valid_from` and `valid_until` timestamps for every chunk.
4. **Document Versioning & Supersession**:
   - Preserves historical knowledge without overwriting.
   - Automatically transitions replaced decisions to `status: superseded`.
   - Links successor versions via `supersedes_document_id`.
5. **Traceable Provenance**: Every response provides verified source citations (`document_id`, `chunk_id`, `source`, `event_at`, `status`, `score`, and snippet).
6. **Query Intent Classification & Server-Side Filtering**:
   - Classifies queries into `SEMANTIC`, `TEMPORAL`, `CURRENT_STATE`, `HISTORICAL`, `COMPARISON`, `SUPERSESSION`, `SOURCE_LOOKUP`.
   - Translates temporal clauses (e.g. *"last March"*, *"in May 2026"*, *"current"*, *"previous"*) into exact Qdrant server-side `DatetimeRange` and `MatchValue` filters.
7. **Strict Grounding (No Hallucination)**: Out-of-range queries (e.g. *"What did I decide in January 2020?"*) return an immediate no-evidence response without hallucinating facts.
8. **Manifest Deduplication**: Avoids duplicate embeddings by tracking content hashes in `.manifest.json`.

---

## 🏗️ Architecture

```
                    ┌─────────────────────────┐
                    │ Personal Data (Notes)   │
                    │ Markdown, TXT, PDF, etc.│
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Ingestion Layer         │
                    │ - Manifest & Dedup      │
                    │ - Temporal Parser       │
                    │ - Validity Calculator   │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Ollama Embeddings       │
                    │ (embeddinggemma: 768-d) │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │ Qdrant Vector Store     │
                    │ Payload indexes:        │
                    │ - event_at (datetime)   │
                    │ - valid_from/until      │
                    │ - status (keyword)      │
                    │ - document_id (keyword) │
                    └───────────┬─────────────┘
                                │
      User Query                │
          │                     │
          ▼                     ▼
┌──────────────────┐    ┌─────────────────────────┐
│ Temporal Parser  │───▶│ Qdrant Server Filter    │
│ & Intent Routing │    │ (DatetimeRange/Status)  │
└──────────────────┘    └───────────┬─────────────┘
                                    │
                                    ▼
                        ┌─────────────────────────┐
                        │ Retrieved Chunks &      │
                        │ Structured Provenance   │
                        └───────────┬─────────────┘
                                    │
                                    ▼
                        ┌─────────────────────────┐
                        │ Ollama LLM (llama3.2)   │
                        │ Strictly Grounded RAG   │
                        └───────────┬─────────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                  FastAPI REST API        Interactive UI
                  (http://localhost:8000) (Browser)
```

---

## 📁 Repository Structure

```
personal-kb/
├── data/
│   ├── .manifest.json       # Incremental change tracking & content hashes
│   └── notes/
│       ├── database_decision.md
│       └── rag_project.md
├── qdrant_storage/          # Persistent Qdrant vector database storage
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI application
│   │   ├── schemas.py       # API schemas (Pydantic)
│   │   ├── ui.py            # Responsive Web UI
│   │   └── routes/          # REST route handlers (/health, /ingest, /query, /documents)
│   ├── config/
│   │   └── settings.py      # Pydantic Settings & environment variables
│   ├── evaluation/
│   │   ├── dataset.py       # Benchmark evaluation dataset
│   │   ├── metrics.py       # Recall@K, Precision@K, MRR, Faithfulness, Temporal Accuracy
│   │   └── runner.py        # Automated benchmark runner
│   ├── generation/
│   │   ├── answer.py        # Grounded generation service
│   │   ├── llm.py           # Ollama LLM provider
│   │   └── prompts.py       # Strict system prompt templates
│   ├── ingestion/
│   │   ├── deduplication.py # ManifestManager & change detection
│   │   ├── loaders.py       # File loaders (Markdown, TXT, PDF, HTML, etc.)
│   │   ├── parser.py        # Temporal-aware document chunker
│   │   ├── pipeline.py      # LlamaIndex IngestionPipeline with Ollama
│   │   └── service.py       # Orchestrated IngestionService
│   ├── models/
│   │   ├── document.py      # NormalizedDocument model
│   │   ├── metadata.py      # DocumentMetadata & ChunkPayload
│   │   └── query.py         # ParsedQuery, TemporalRange, SourceCitation, QueryResponse
│   ├── retrieval/
│   │   ├── semantic.py      # Dense vector search against Qdrant
│   │   ├── temporal.py      # Temporal filtering & comparison decomposition
│   │   └── service.py       # RetrievalService & citation builder
│   ├── storage/
│   │   ├── indexes.py       # Qdrant typed payload schema definitions
│   │   └── qdrant.py        # Qdrant client & collection management
│   ├── temporal/
│   │   ├── filters.py       # Qdrant server-side filter generator
│   │   ├── parser.py        # Regex & relative temporal query parser
│   │   ├── resolver.py      # Temporal intent resolver & decomposer
│   │   └── versioning.py    # Version transitions & chronological sorting
│   └── main.py              # CLI entry point (ingest, chat, serve, eval)
├── tests/
│   ├── test_api.py
│   ├── test_chunking.py
│   ├── test_deduplication.py
│   ├── test_e2e_temporal_rag.py
│   └── test_temporal_extraction.py
├── .env.example
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🚀 Quickstart

### 1. Prerequisites
- **Python 3.11+**
- **Docker & Docker Compose**
- **Ollama** running locally with:
  ```bash
  ollama pull llama3.2
  ollama pull embeddinggemma
  ```

### 2. Start Qdrant Vector Store
```bash
docker compose up -d
```
Qdrant is accessible at `http://localhost:6333`.

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configuration & LLM Fallback Setup
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

The system employs a prioritized **LLM Model Fallback Chain**:
```
1. Groq (Primary) ──(if rate-limited/failed)──▶ 2. Gemini ──(if failed)──▶ 3. OpenRouter
```

Configure your API keys in `.env`:
```env
# LLM Fallback Order (Groq -> Gemini -> OpenRouter)
LLM_FALLBACK_ORDER=groq,gemini,openrouter

# 1. Groq (Primary)
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# 2. Google Gemini (First Fallback)
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash

# 3. OpenRouter (Second Fallback)
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct
```
If a provider is unconfigured, rate-limited (HTTP 429), or unavailable, the system automatically and transparently cascades to the next provider in the chain.

---

## 💻 CLI Commands

### Ingest Documents
Scans `data/`, computes content hashes, extracts temporal metadata, and embeds new or modified documents:
```bash
python src/main.py ingest
```

### Interactive Chat
Start a natural-language conversation with temporal memory in the terminal:
```bash
python src/main.py chat
```
*Tip: Type `/debug` during chat to toggle retrieval inspection.*

### Start REST API Server & Web UI
```bash
python src/main.py serve
```
Open **http://localhost:8000** in your browser to access the interactive Web UI and Swagger documentation at **http://localhost:8000/docs**.

### Run Evaluation Benchmark
```bash
python src/main.py eval
```

---

## 📊 Benchmark Evaluation Results

Running the automated benchmark against test questions yielded:

| Metric | Score |
| :--- | :--- |
| **Mean Recall@5** | **100.0%** |
| **Mean Precision@5** | **90.0%** |
| **Mean MRR** | **1.0000** |
| **Answer Faithfulness** | **100.0%** |
| **Temporal Accuracy** | **100.0%** |

### Benchmark Query Verification:
1. *"What did I decide about the database last March?"*
   - **Retrieved:** `database_decision.md` (March 15, 2026 chunk)
   - **Answer:** *"According to the context, on March 15, 2026, the decision was made to use PostgreSQL for production."*
2. *"What is my current production database decision?"*
   - **Retrieved:** `database_decision.md` (August 10, 2026 chunk, status: `active`)
   - **Answer:** *"The current production database decision is PostgreSQL, confirmed on August 10, 2026."*
3. *"What was my previous database decision?"*
   - **Retrieved:** Historical superseded chunks (SQLite on May 20, 2026 & PostgreSQL on March 15, 2026)
   - **Answer:** Details the previous decision to temporarily use SQLite for the prototype on May 20, 2026.
4. *"When did my database decision change?"*
   - **Retrieved:** Chronological progression of decisions
   - **Answer:** Summarizes the changes on May 20 (switched to SQLite prototype) and August 10 (confirmed PostgreSQL production).
5. *"What did I decide about databases in January 2020?"*
   - **Filter Result:** 0 chunks matched
   - **Answer:** *"The knowledge base does not contain sufficient evidence to answer this question."* (Zero hallucination).

---

## 🧪 Running Automated Tests

Run the complete test suite with `pytest`:
```bash
pytest tests
```
All unit, integration, API, and end-to-end RAG tests pass successfully.

---

## 🐳 Docker Deployment & CI/CD Pipeline

### Production Deployment
Launch the full multi-container stack (Qdrant + FastAPI Web App):
```bash
# From repository root or personal-kb/
docker compose up -d --build
```
- Web UI & REST API: **http://localhost:8000**
- Qdrant Vector DB: **http://localhost:6333**
- Auto-restart: `unless-stopped` with persistent data volumes (`./data` and `./qdrant_storage`).

### Development with Live Hot-Reload
When continuously developing features without rebuilding container images:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```
Any changes made inside `src/` will instantly trigger Uvicorn hot-reload inside the container.

### Developer CLI Scripts
Quick shortcuts for local testing and container management:
```powershell
# Windows PowerShell
.\dev.ps1 test      # Run fast temporal & grounding unit tests
.\dev.ps1 lint      # Run Ruff code quality check
.\dev.ps1 dev       # Start Docker stack with live hot-reloading
.\dev.ps1 up        # Start production Docker Compose stack
.\dev.ps1 down      # Stop running containers
.\dev.ps1 logs      # Follow application logs
```
```bash
# Linux / macOS / WSL
./dev.sh test
./dev.sh dev
./dev.sh up
./dev.sh down
```

### GitHub Actions CI/CD (`.github/workflows/ci.yml`)
Automated on every push and pull request:
1. **Linting**: Code quality enforcement via `ruff`.
2. **Temporal & Grounding Tests**: Verifies chunking, deduplication, date extraction, and fallback cascading.
3. **Container Delivery**: Verifies Docker compilation and automatically publishes release containers to **GitHub Container Registry (`ghcr.io`)** on merge to `main` or semantic release tags (`v*`).

