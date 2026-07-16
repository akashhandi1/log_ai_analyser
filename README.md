# 🛡️ Local AI SRE - Log Analyzer

An offline Systems Reliability Engineering (SRE) assistant designed to parse application logs, analyze root causes, suggest remediation fixes using a local or cloud Large Language Model (LLM), and cache resolutions locally using a vector database for instant future lookups.

## 🚀 Features
* **Log Parsing:** Extracts timestamps, log levels, service names, and error messages dynamically.
* **Hybrid Smart Cache (RAG):** Integrates **Qdrant Vector DB** to store past incidents. Duplicate or highly similar errors are fetched instantly from local memory for $0 cost.
* **Local or Cloud AI Engine:** Supports running entirely offline via **Ollama** (`gemma3:4b`) or connecting to cloud-hosted options (**OpenAI GPT-4o-mini**).
* **Interactive Frontend:** Built with **Streamlit** to offer an easy-to-use playground for pasting logs or picking mock hardware/software scenarios.

---

## 🛠️ Tech Stack
* **Frontend:** Streamlit
* **Backend Framework:** FastAPI (Uvicorn)
* **Vector Database:** Qdrant (Local client routing)
* **Embeddings:** Sentence-Transformers (`all-MiniLM-L6-v2`)
* **LLM Engine:** Ollama / OpenAI SDK

---

## 📦 Installation & Setup

### 1. Clone & Initialize Environment
Clone or navigate to your project directory and activate the Python virtual environment:

```powershell
# Activate on Windows PowerShell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
