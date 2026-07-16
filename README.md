# 🛡️ Local AI SRE - Log Analyzer

An intelligent Systems Reliability Engineering (SRE) assistant designed to parse complex application logs, extract structural attributes, analyze root causes, suggest remediation commands, and cache results locally in a vector database for instant future lookups.

---

## 🚀 Key Features

* **Log Parsing:** Extracts timestamps, log levels, service names, and raw messages dynamically.
* **Hybrid Smart Cache (RAG):** Integrates **Qdrant Vector DB** and `Sentence-Transformers` (`all-MiniLM-L6-v2`) to save past resolutions. Matches are retrieved instantly for zero overhead.
* **Dual-Core AI Engine:**
    * **Local Execution (Default):** Runs offline using **Ollama** and Google's **Gemma 3** (`gemma3:4b`).
    * **Cloud Integration (Optional):** Supports **OpenAI GPT-4o-mini** if an API key is active, caching cloud results locally to prevent recurring costs.
* **Streamlit UI:** Clean, modern interface designed for visualizing extracted data and remediation workflows.

---

## 🛠️ Architecture Overview

```text
               ┌────────────────────────┐
               │   Streamlit Frontend   │
               └───────────┬────────────┘
                           │ POST /analyze
                           ▼
               ┌────────────────────────┐
               │    FastAPI Backend     │
               └───────────┬────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    [ Vector DB Cache? ]        [ Cache Miss: Generate ]
    Qdrant (Local Client)       ├── Local: Ollama (Gemma 3)
    └── Returns $0 Solution     └── Cloud: OpenAI (GPT-4o-mini)
```

---

## 📦 Installation & Setup

### 1. Configure the Environment
Navigate to your project directory (`D:\ai-log-analyzer`) and activate the Python virtual environment:

```powershell
# Windows PowerShell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configure the LLM Engine

#### Option A: Local AI Engine (Ollama)
1. Download and start the [Ollama Desktop App](https://ollama.com/).
2. Pull the Gemma 3 model:
   ```bash
   ollama pull gemma3:4b
   ```

#### Option B: Cloud AI Engine (OpenAI)
If you want to use the OpenAI API configuration, set your API key in your terminal session:
```powershell
$env:OPENAI_API_KEY="your-actual-api-key-here"
```

---

## 🚦 Running the Application

The application consists of two decoupled services. Open **two separate terminal windows** in VS Code:

### Terminal 1: Spin up the FastAPI Backend
```bash
uvicorn backend.main:app --reload --port 8000
```

### Terminal 2: Run the Streamlit Frontend
```bash
streamlit run frontend/app.py
```

Open your browser to the local URL provided by Streamlit (usually `http://localhost:8501`) to begin diagnostic runs.

---

## 📂 Complete Project Source Files

You can copy the code for each file directly from this documentation.

### 1. `.gitignore`
Save this code to a file named `.gitignore` in your root folder:
```text
.venv/
vector_db_data/
backend/vector_db_data/
__pycache__/
*.pyc
.env
```

### 2. `requirements.txt`
Save this code to a file named `requirements.txt` in your root folder:
```text
fastapi
uvicorn
requests
pydantic
streamlit
qdrant-client
sentence-transformers
openai
```

### 3. `backend/parser.py`
Save this code to `backend/parser.py`:
```python
import re
from datetime import datetime

# Common Log Regex: [Timestamp] LEVEL [Service] Message
LOG_PATTERN = re.compile(
    r"^\[(?P<timestamp>[^\]]+)\]\s+(?P<level>[A-Z]+)\s+\[(?P<service>[^\]]+)\]\s+(?P<message>.+)$"
)

def parse_log_line(line: str) -> dict:
    match = LOG_PATTERN.match(line.strip())
    if match:
        return match.groupdict()
        
    # Fallback if log format is unstructured
    return {
        "timestamp": datetime.now().isoformat(),
        "level": "UNKNOWN",
        "service": "system",
        "message": line.strip()
    }
```

### 4. `backend/vector_store.py`
Save this code to `backend/vector_store.py`:
```python
import os
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from sentence_transformers import SentenceTransformer

# Initialize embedding model
encoder = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize Local Qdrant Path
DB_PATH = os.path.join(os.path.dirname(__file__), "vector_db_data")
client = QdrantClient(path=DB_PATH)
COLLECTION_NAME = "log_incidents"

# Create collection if it doesn't exist
try:
    client.get_collection(collection_name=COLLECTION_NAME)
except Exception:
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=384, distance=Distance.COSINE),
    )

def add_incident(log_message: str, root_cause: str, fix: str):
    """Saves a resolved incident to Qdrant."""
    vector = encoder.encode(log_message).tolist()
    point_id = str(uuid.uuid4())
    
    payload = {
        "log_message": log_message,
        "root_cause": root_cause,
        "fix": fix
    }
    
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
        ]
    )

def search_similar_incidents(log_message: str, score_threshold: float = 0.8):
    """Queries Qdrant using the correct query_points methodology."""
    vector = encoder.encode(log_message).tolist()
    
    try:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector,
            limit=1
        ).points
        
        if results and results[0].score >= score_threshold:
            return results[0].payload
    except Exception as e:
        print(f"Error querying Qdrant: {e}")
    return None
```

### 5. `backend/main.py`
Save this code to `backend/main.py`:
```python
import os
import re
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI  # Supports Cloud Mode
from backend.parser import parse_log_line
from backend.vector_store import search_similar_incidents, add_incident

app = FastAPI(title="Local AI SRE Engine")

class LogPayload(BaseModel):
    raw_log: str

OLLAMA_URL = "http://localhost:11434/api/generate"

# Initialize OpenAI Client (Pulls key automatically from system environment if available)
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None

@app.post("/analyze")
def analyze_log(payload: LogPayload):
    # 1. Parse raw log
    parsed = parse_log_line(payload.raw_log)
    log_msg = parsed["message"]
    
    # 2. Check Local Vector DB cache for a past solution
    cached_solution = search_similar_incidents(log_msg)
    if cached_solution:
        return {
            "parsed": parsed,
            "root_cause": cached_solution.get("root_cause", "Unknown"),
            "fix": cached_solution.get("fix", "Review manual logs"),
            "source": "Vector Cache (Resolved Past Incident)"
        }
        
    # Prompt Template
    prompt = f"""
    You are an expert Systems Reliability Engineer (SRE). Analyze this log error:
    Service: {parsed['service']}
    Message: {log_msg}
    
    Provide your analysis in EXACTLY this format:
    ROOT CAUSE: [Provide 1-sentence explanation]
    FIX: [Provide step-by-step resolution command or steps]
    """
    
    # 3. Determine Engine (Cloud OpenAI vs. Local Ollama) and Analyze
    try:
        if openai_client:
            # --- CLOUD ENGINE (OpenAI GPT-4o-mini) ---
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful SRE assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
            )
            ai_raw_text = response.choices[0].message.content
            engine_source = "Cloud OpenAI (GPT-4o-mini)"
        else:
            # --- LOCAL ENGINE (Ollama Gemma 3) ---
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": "gemma3:4b", 
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            ai_raw_text = response.json().get("response", "")
            engine_source = "Generative Local AI"
        
        # 4. Robust Output Parsing using Regex
        root_cause_match = re.search(r"(?i)(?:root\s*cause|cause)\s*:\s*(.*?)(?=(?:fix|remediation)\s*:|$)", ai_raw_text, re.DOTALL)
        fix_match = re.search(r"(?i)(?:fix|remediation)\s*:\s*(.*)", ai_raw_text, re.DOTALL)
        
        root_cause = root_cause_match.group(1).strip("* \n\r") if root_cause_match else "Unknown"
        fix = fix_match.group(1).strip("* \n\r") if fix_match else "Review manual logs"
        
        if root_cause == "Unknown" and fix == "Review manual logs":
            fix = ai_raw_text
            root_cause = f"Refer to the diagnostics below for the parsed service error: {parsed['service']}"

        # Save generated result to local Vector DB cache
        add_incident(log_msg, root_cause, fix)
        
        return {
            "parsed": parsed,
            "root_cause": root_cause,
            "fix": fix,
            "source": engine_source
        }
        
    except Exception as e:
        engine_name = "Cloud OpenAI" if openai_client else "Ollama local service"
        raise HTTPException(status_code=500, detail=f"{engine_name} failed: {str(e)}")
```

### 6. `frontend/app.py`
Save this code to `frontend/app.py`:
```python
import streamlit as st
import requests

st.set_page_config(page_title="Local AI Log SRE", layout="wide")

st.title("🛡️ Local AI SRE - Log Analyzer")
st.caption("Running fully offline or with secure hybrid cloud configurations.")

st.sidebar.header("Sample Scenarios")
test_logs = {
    "DB Connection Timeout": "[2026-07-16 11:22:10] ERROR [database_service] Connection refused at port 5432, pool capacity reached max_connections=100",
    "Out of Memory": "[2026-07-16 11:25:44] CRITICAL [payment_service] java.lang.OutOfMemoryError: Java heap space",
    "API Auth Failure": "[2026-07-16 11:28:01] WARN [gateway_service] Invalid JWT token signature decoded from user client IP 192.168.1.45"
}

selected_scenario = st.sidebar.selectbox("Load a sample log:", list(test_logs.keys()))
raw_input = st.text_area("Or paste a raw log line here:", value=test_logs[selected_scenario], height=100)

if st.button("Run AI Diagnostics"):
    with st.spinner("Analyzing log..."):
        try:
            res = requests.post("http://localhost:8000/analyze", json={"raw_log": raw_input})
            if res.status_code == 200:
                data = res.json()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Parsed Metadata")
                    st.json(data["parsed"])
                with col2:
                    st.subheader("Diagnostic Vector Source")
                    st.info(f"Source of Decision: **{data['source']}**")
                
                st.write("---")
                st.subheader("AI Root Cause Analysis")
                st.error(data["root_cause"])
                
                st.subheader("Suggested Remediation Steps")
                st.success(data["fix"])
            else:
                st.error("Backend failed to compute diagnostics.")
        except Exception as e:
            st.error(f"Cannot connect to backend: {e}. Did you start main.py?")
```
