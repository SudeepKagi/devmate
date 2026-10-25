# Devmate 🤖

**Devmate** is an autonomous AI coding assistant CLI designed to index, understand, and answer questions about any codebase using semantic search and cutting-edge LLMs.

---

## ✨ Features

- **AST-Aware Code Parsing**: Uses Tree-sitter to parse source files into meaningful function and class chunks.
- **Semantic Codebase Indexing**: Embedded using Google Gemini embeddings (`gemini-embedding-001`) and stored in ChromaDB vector storage.
- **Autonomous Querying**: Ask questions with `/ask <question>` and Devmate retrieves relevant context using similarity search to generate precise answers.
- **Flexible Provider Support**: Powered by Google Gemini (`gemini-3.8-flash`) and xAI Grok.
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
GEMINI_API_KEY=your_gemini_api_key_here
# Optional:
XAI_API_KEY=your_xai_api_key_here
```

### 2. `~/.devmate/config.yaml`

```yaml
llm:
  provider: gemini
  gemini:
    model: gemini-3.8-flash
    temperature: 0.2
  grok:
    model: grok-2-latest
    temperature: 0.2

embedding:
  gemini:
    model: gemini-embedding-001

chromadb:
  persist_directory: .chromadb
  collection_name: codebase_semantic_index
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
| `/show_semantic_index` | View sample chunks currently indexed in ChromaDB |
| `exit` / `quit` | Exit the CLI session |

---

## 📄 License

MIT
