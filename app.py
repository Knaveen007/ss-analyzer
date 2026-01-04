import streamlit as st
import asyncio
import os
import json
from dotenv import load_dotenv
from src.core.engine import VisualMemoryEngine
from PIL import Image

# Setup
st.set_page_config(page_title="Visual Memory Engine", page_icon="🧠", layout="wide")
load_dotenv()

# Initialize Engine (Cached)
@st.cache_resource
def get_engine():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        st.error("OPENROUTER_API_KEY not found in .env")
        return None
    return VisualMemoryEngine(api_keys={"openrouter": api_key})

engine = get_engine()

# --- Sidebar: Memory Stream ---
st.sidebar.title("🧠 Memory Stream")
if engine:
    try:
        memories = engine.store.get_recent_memories(limit=15)
        for mem in memories:
            with st.sidebar.expander(f"{mem['updated_at'][:16]}", expanded=False):
                st.caption(f"ID: {mem['id'][:8]}...")
                st.markdown(mem.get('summary', 'No summary'))
    except Exception as e:
        st.sidebar.error(f"Error loading memories: {e}")

# --- Main Interface ---
st.title("🧠 Visual Memory Engine")
st.markdown("### Zero-Cost, Semantic Visual Intelligence")

uploaded_file = st.file_uploader("Upload a screenshot to process:", type=["png", "jpg", "jpeg"])

if uploaded_file and engine:
    # 1. Preview
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image(uploaded_file, caption="Input Image", use_container_width=True)
        # Save temp file
        temp_path = f"temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

    with col2:
        if st.button("🧠 Process Memory", type="primary"):
            with st.spinner("Analyzing semantics & checking for duplicates..."):
                try:
                    # Run Async Processing
                    result = asyncio.run(engine.process_screen(temp_path))
                    
                    # Clean up
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    # Display Results
                    status = result.get('status')
                    
                    if status == "created":
                        st.success(f"✅ New Memory Created! (ID: {result.get('memory_id')})")
                    elif status == "updated":
                        st.info(f"🔄 Memory Updated (Semantic Diff)! (ID: {result.get('memory_id')})")
                        st.metric("Changes Detected", result.get('changes_count', 0))
                    elif status == "unchanged":
                        st.warning("⏸️ Duplicate Intent (Unchanged)")
                        
                    st.json(result)
                    
                    # Reload page to update sidebar (simple way)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Processing Error: {e}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

# Instructions
with st.expander("ℹ️ How it works"):
    st.markdown("""
    1.  **Fingerprinting**: Locally checks if this exact image exists (Zero Cost).
    2.  **Semantic Search**: Checks if a *similar* image exists in the DB (Turso/SQLite).
    3.  **Vision AI**: If new/different, uses OpenRouter (Free) to extract content.
    4.  **Diffing**: If similar, calculates semantic differences and updates the existing memory.
    """)
