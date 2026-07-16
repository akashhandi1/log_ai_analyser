import streamlit as st
import requests

st.title("🛡️ Local AI SRE - Log Analyzer")

# Log input
log_input = st.text_area("Or paste a raw log line here:")

if st.button("Run AI Diagnostics"):
    if log_input.strip():
        with st.spinner("Analyzing with local SRE AI..."):
            try:
                response = requests.post("http://localhost:8000/analyze", json={"raw_log": log_input})
                if response.status_code == 200:
                    data = response.json()
                    
                    # Columns for Metadata and Decision Source
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Parsed Metadata")
                        st.json(data["parsed"])
                    with col2:
                        st.subheader("Diagnostic Vector Source")
                        st.info(f"Source: {data['source']}")
                    
                    st.write("---")
                    
                    # Output the specific Root Cause & Fix
                    st.subheader("🕵️ Root Cause")
                    st.write(data["root_cause"])
                    
                    st.subheader("🛠️ Recommended Fix")
                    st.markdown(data["fix"])
                    
                else:
                    st.error("Backend failed to compute diagnostics.")
            except Exception as e:
                st.error(f"Could not connect to backend: {e}")