# Devmate 🤖

**Devmate** is an autonomous AI coding assistant CLI designed to index, understand, and answer questions about any codebase using semantic search and cutting-edge LLMs.

---

## ✨ Features

- **AST-Aware Code Parsing**: Uses Tree-sitter to parse source files into meaningful function and class chunks.
- **Semantic Codebase Indexing**: Embedded using Google Gemini embeddings (`gemini-embedding-001`) and stored in ChromaDB vector storage.
- **Autonomous Querying**: Ask questions with `/ask <question>` and Devmate retrieves relevant context using similarity search to generate precise answers.
- **Flexible Provider Support**: Powered by xAI Grok (`grok-2-latest`), OpenAI, and Google Gemini.
- **Local Zero-Cost Embeddings**: Uses HuggingFace (`sentence-transformers/all-MiniLM-L6-v2`) locally — zero rate limits, no API key needed for embeddings.
- **Universal CLI**: Runs anywhere across your project repositories via `pipx`.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+ (tested on Python 3.14)
- [pipx](https://pypa.github.io/pipx/) or Poetry

### Installation

Install globally using `pipx`:

```bash
git clone https://github.com/SudeepKagi/devmate.git
cd devmate
pipx install .
```

For development (editable install):

```bash
pipx install . --editable
```

---

## ⚙️ Configuration

Create a global configuration directory at `~/.devmate/`:

```
~/.devmate/
├── .env
└── config.yaml
```

### 1. `~/.devmate/.env`

```ini
XAI_API_KEY=your_xai_grok_key_here
# Optional:
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here
```

### 2. `~/.devmate/config.yaml`

```yaml
llm:
  provider: grok    # grok | openai | gemini
  model: grok-2-latest

embeddings:
  provider: huggingface    # huggingface (100% local, zero rate limits) | openai | gemini
  model: sentence-transformers/all-MiniLM-L6-v2

chromadb:
  persist_dir: .chromadb/
  collection_name: codebase
```

---

## 💻 Usage

Navigate to any codebase directory in your terminal and launch `devmate`:

```bash
devmate
```

### Commands

| Command | Description |
|---|---|
| `/ask <query>` | Ask questions about the codebase using semantic retrieval |
| `/reindex` | Force a fresh re-indexing of all files in the current repository |
| `/show_semantic_index` | View sample chunks currently indexed in ChromaDB |
| `/help` | Show available commands |
| `/exit` / `quit` | Exit the CLI session |

---

## 📄 License

MIT
