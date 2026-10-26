# Devmate 🤖

**Devmate** is an autonomous AI software engineering and coding assistant CLI. It indexes, searches, understands, and implements features across your codebase using semantic search, autonomous multi-task execution, real-time background file watching, and low-cost OpenAI models.

---

## ✨ Features

- **AST-Aware Code Parsing**: Uses Tree-sitter to parse source files into meaningful semantic function, class, and method chunks.
- **Incremental Semantic Indexing**: Automatically tracks file modification times (`mtime`) in ChromaDB to only embed new or changed files, minimizing API costs.
- **Real-Time Background Watchdog**: Background watchdog observer keeps your vector index up-to-date as files are created, modified, or deleted without restarting.
- **Autonomous Task Planning & Execution (`/plan <goal>`)**:
  - Breaks high-level software goals into a concrete DAG of subtasks (5–20 tasks).
  - Human-in-the-loop interactive review & approval (`[A]pprove`, `[M]odify`, `[R]eject`).
  - Persistent SQLite state store (`.devmate/tasks.db`) with atomic state transitions and crash recovery.
  - Subtask agents equipped with focused, least-privilege toolsets.
  - LLM-as-judge quality verification verifying acceptance criteria before marking tasks completed.
- **Async Semantic Response Cache**: Redis and redisvl semantic caching with cosine similarity thresholding to serve repeated or similar queries instantly with zero LLM API cost. Graceful fallback when Redis is offline.
- **Extensible Skills Architecture**: Load markdown-defined workflows, prompt guides, and scripts dynamically on demand (`.devmate/skills/`).
- **Model Context Protocol (MCP)**: Seamlessly integrates with external MCP servers (e.g. GitHub MCP).
- **Cost-Optimized**: Pre-configured for low-cost OpenAI models (`gpt-4o-mini` for chat/judge and `text-embedding-3-small` for embeddings).
- **Production Evaluator Suites**: Automated DeepEval evaluation pipelines covering RAG retrieval precision/recall and agentic multi-turn task completion.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.12+ (tested on Python 3.14)
- [pipx](https://pypa.github.io/pipx/) or Poetry

### Installation

Install globally using `pipx`:

```bash
git clone https://github.com/SudeepKagi/devmate.git
cd devmate
pipx install . --editable
```

---

## ⚙️ Configuration

Devmate reads configuration from:
1. Current working directory `config.yaml`
2. `~/.devmate/config.yaml`
3. Built-in defaults

### 1. `.env`

Add your OpenAI API key to `.env` or `~/.devmate/.env`:

```ini
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. `config.yaml`

```yaml
llm:
  provider: openai
  model: gpt-4o-mini
  judge_model: gpt-4o-mini

embeddings:
  provider: openai
  model: text-embedding-3-small
  dims: 1536

vector_store:
  provider: chroma
  retrieval_mode: dense

chromadb:
  persist_dir: .devmate/chromadb/
  collection_name: codebase

tasks:
  db_path: .devmate/tasks.db

semantic_cache:
  enabled: true
  redis_url: redis://localhost:6379
  threshold: 0.85
  ttl: 86400
```

---

## 💻 Usage

Launch `devmate` in any codebase directory:

```bash
devmate
```

### Commands

| Command | Description |
|---|---|
| `/ask <question>` | Ask questions about the codebase using semantic retrieval |
| `/plan <goal>` | Generate, review, approve, and autonomously execute a plan |
| `/task_status` | Show task status and progress for the active plan |
| `/show_index` | View sample chunks currently indexed in ChromaDB |
| `/reindex` | Force a fresh re-indexing of all files in the current repository |
| `/new_session` | Start a fresh conversational session |
| `/switch <session_id>` | Switch to a prior conversational session |
| `/session` | Display current session ID |
| `/help` | Show available commands |
| `/exit` / `quit` | Exit the CLI session |

---

## 🧪 Evaluations

Run DeepEval test suites:

```bash
deepeval test run tests/evals/test_codebase_agent.py
deepeval test run tests/evals/test_rag_pipeline.py
deepeval test run tests/evals/test_task_planning_agent.py
```

---

## 📄 License

MIT
