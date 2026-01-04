# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-12-21
### Added
- **Visual Memory Engine Core**:
  - Implemented `VisualMemoryEngine` in `src/core/engine.py` as the main entry point.
  - Implemented `MemoryDatabase` (SQLite) with WAL mode for high-performance storage.
  - Implemented `ImageFingerprinter` (Perceptual & Content Hashing) to detect duplicates locally.
  - Implemented `MemoryUpdater` for semantic diffing (tracking structure changes over time).

- **Zero-Cost Vision Pipeline**:
  - Integrated **OpenRouter API** to leverage free-tier vision models.
  - **Primary Model**: `qwen/qwen-2.5-vl-7b-instruct:free` (Verified working).
  - **Fallback Model**: `google/gemini-2.0-flash-exp:free`.
  - Removed dependency on paid OpenAI/Gemini direct clients to ensure zero operational cost.

- **Production Utilities**:
  - Created `main.py`: A robust CLI tool for processing images and outputting JSON.
  - Created `DEPLOYMENT.md`: Documentation for integrating the engine into the main product.
  - Created `requirements.txt`: Minimal dependency list (`openai`, `tenacity`, `pillow`, `imagehash`, `numpy`, `libsql-experimental`).

- **Database**:
  - Added support for **Turso (LibSQL)** for serverless low-latency storage.
  - System automatically switches between Local SQLite and Cloud LibSQL based on `.env` vars.
  - Fixed row factory handling for remote LibSQL connections.

- **Semantic Intelligence**:
  - Enabled **Auto-Linking** of similar images using Perceptual Hash (Hamming Distance).
  - Images that are visually similar but semantically different now trigger an **Update** instead of a New Creation.

- **User Interface**:
  - Created `app.py`: A **Streamlit** based web interface for demos.
  - Sidebar displays real-time **Memory Stream** from Turso/SQLite.
  - Drag-and-drop processing for easy validation.




### Fixed
- **Vision Processor Stability**:
  - Replaced unstable `google.generativeai` direct integration with OpenRouter's OpenAI-compatible client.
  - Fixed logic for extracting JSON from LLM responses (robust regex to handle markdown code blocks).
- **Database Initialization**: Fixed `MemoryDatabase` `__init__` method to correctly set up tables (`memories`, `memory_versions`, `memory_cache`) and indexes.

### Configuration
- System now requires `OPENROUTER_API_KEY` in `.env`.
- Removed `GOOGLE_API_KEY` and `OPENAI_API_KEY` requirements to prevent confusion.

### Usage Snapshot (Validation)
- **Status**: Deployment Ready
- **Test Command**: `python main.py /path/to/image.png`
- **Expected Output**: JSON object with `status` ("created", "unchanged", "updated") and extracted content.
