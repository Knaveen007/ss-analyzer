# Visual Memory Engine (SS-Analyzer) 🧠

A Zero-Cost, Semantic Visual Intelligence engine that acts as a visual memory layer. It processes images (screenshots), extracts semantic meaning using AI, checks for duplicates, and maintains a searchable memory stream.

## Features

- **Semantic Fingerprinting**: Efficiently checks for exact or similar images to avoid processing duplicates.
- **AI-Powered Extraction**: Uses OpenRouter (e.g., Gemini Flash, Llama) to extract descriptions and semantic intent from images.
- **Semantic Diffing**: Detects if a new image is a meaningful update to a previous memory or essentially the same.
- **Streamlit Interface**: user-friendly sidebar for viewing memory history and a main area for processing new images.
- **Local Database**: Stores memory embeddings and metadata using SQLite (via `libsql-experimental`).

## Prerequisites

- Python 3.10+
- [OpenRouter](https://openrouter.ai/) API Key (for LLM access)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Knaveen007/ss-analyzer.git
    cd ss-analyzer
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Setup:**
    Duplicate `.env.example` to `.env` and fill in your keys:
    ```bash
    cp .env.example .env
    ```
    
    Edit `.env`:
    ```env
    TURSO_DATABASE_URL="file:memories.db" # Or your Turso URL
    TURSO_AUTH_TOKEN="" # Optional for local file
    OPENROUTER_API_KEY="sk-or-..." 
    ```

## Usage

### Run the Web Interface
Start the Streamlit app:
```bash
streamlit run app.py
```
Upload an image in the UI to process it. The sidebar will update with the memory stream.

### Run via CLI
Process a single image file:
```bash
python main.py path/to/image.png
```

## Project Structure

- `app.py`: Main Streamlit application entry point.
- `main.py`: CLI entry point.
- `src/core/engine.py`: Core logic for the Visual Memory Engine.
- `src/`: Source code modules.
- `memories.db`: Local SQLite database (created on first run).

## License

MIT
