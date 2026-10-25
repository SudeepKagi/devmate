# Devmate 🤖

**Devmate** is an autonomous AI coding assistant CLI designed to index, understand, and answer questions about any codebase using semantic search and cutting-edge LLMs.

---

## ✨ Features

- **AST-Aware Code Parsing**: Uses Tree-sitter to parse source files into meaningful function and class chunks.
- **Semantic Codebase Indexing**: Embedded using Google Gemini embeddings (`gemini-embedding-001`) and stored in ChromaDB vector storage.
- **Autonomous Querying**: Ask questions with `/ask <question>` and Devmate retrieves relevant context using similarity search to generate precise answers.
- **Flexible Provider Support**: Powered by OpenAI (`gpt-4o-mini`, `text-embedding-3-small`), Google Gemini, and xAI Grok.
- **Cost & Token Efficient**: Optimized for low token consumption with compact retrieval chunks and strict output budgets.
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
OPENAI_API_KEY=your_openai_api_key_here
# Optional:
GEMINI_API_KEY=your_gemini_api_key_here
XAI_API_KEY=your_xai_api_key_here
```

### 2. `~/.devmate/config.yaml`

```yaml
llm:
  provider: openai    # openai | gemini | grok
  model: gpt-4o-mini
  max_tokens: 1000

embeddings:
  provider: openai    # openai | gemini | huggingface
  model: text-embedding-3-small

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
