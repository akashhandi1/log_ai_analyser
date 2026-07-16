# backend/main.py (Updated `/analyze` endpoint)
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import re  # <-- Make sure re is imported
from backend.parser import parse_log_line
from backend.vector_store import search_similar_incidents, add_incident

app = FastAPI(title="Local AI SRE Engine")

class LogPayload(BaseModel):
    raw_log: str

OLLAMA_URL = "http://localhost:11434/api/generate"

@app.post("/analyze")
def analyze_log(payload: LogPayload):
    # 1. Parse raw log
    parsed = parse_log_line(payload.raw_log)
    log_msg = parsed["message"]
    
    # 2. Check Vector DB for a past solution
    cached_solution = search_similar_incidents(log_msg)
    if cached_solution:
        return {
            "parsed": parsed,
            "root_cause": cached_solution.get("root_cause", "Unknown"),
            "fix": cached_solution.get("fix", "Review manual logs"),
            "source": "Vector Cache (Resolved Past Incident)"
        }
        
    # 3. If cache miss, Query local Ollama
    prompt = f"""
    You are an expert Systems Reliability Engineer (SRE). Analyze this log error:
    Service: {parsed['service']}
    Message: {log_msg}
    
    Provide your analysis in EXACTLY this format:
    ROOT CAUSE: [Provide 1-sentence explanation]
    FIX: [Provide step-by-step resolution command or steps]
    """
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "gemma3:4b", 
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        print("--- OLLAMA RAW RESPONSE ---")
        print(response.json())
        print("---------------------------")
        
        ai_raw_text = response.json().get("response", "")
        ai_raw_text = response.json().get("response", "")
        
        # 4. Smart Robust Parsing using Regular Expressions
        # This matches "ROOT CAUSE:" or "**ROOT CAUSE**:" with any casing/markdown
        root_cause_match = re.search(r"(?i)(?:root\s*cause|cause)\s*:\s*(.*?)(?=(?:fix|remediation)\s*:|$)", ai_raw_text, re.DOTALL)
        fix_match = re.search(r"(?i)(?:fix|remediation)\s*:\s*(.*)", ai_raw_text, re.DOTALL)
        
        # Strip out any residual markdown symbols if found
        root_cause = root_cause_match.group(1).strip("* \n\r") if root_cause_match else "Unknown"
        fix = fix_match.group(1).strip("* \n\r") if fix_match else "Review manual logs"
        
        # If the regex split fails completely, fall back to showing the raw AI output in the fix box
        if root_cause == "Unknown" and fix == "Review manual logs":
            fix = ai_raw_text
            root_cause = f"Refer to the diagnostics below for the parsed service error: {parsed['service']}"

        # Save to Qdrant so the system "learns" from this analysis
        add_incident(log_msg, root_cause, fix)
        
        return {
            "parsed": parsed,
            "root_cause": root_cause,
            "fix": fix,
            "source": "Generative Local AI"
        }
        
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ollama local service unreachable: {str(e)}")