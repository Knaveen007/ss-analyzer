# Visual Memory Engine - Deployment Guide

This system provides a **Visual Memory Backend** that processes screenshots/images, extracts structured data, and tracks semantic changes over time (Incremental Memory).

## 🚀 Key Features
- **Zero Cost Operation**: Uses OpenRouter Free Tier (Qwen Google Gemini 1.5 Flash (Free Tier) Llama).
- **Semantic Diffing**: Tracks context/meaning changes, not just pixel diffs.
- **Low Compute**: Local fingerprinting prevents re-processing duplicates.

## 🛠 Setup for Deployment

1.  **Environment Variables**
    Ensure your production environment has the following variable:
    ```bash
    OPENROUTER_API_KEY="sk-or-v1-..."
    ```

2.  **Dependencies**
    Install the required lightweight packages:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Integration Code**
    Use `src/core/engine.py` as your main interface.

    ```python
    from src.core.engine import VisualMemoryEngine
    import os

    # Initialize once
    engine = VisualMemoryEngine(api_keys={"openrouter": os.getenv("OPENROUTER_API_KEY")})

    # Process images (Async)
    async def handle_upload(file_path):
        result = await engine.process_screen(file_path)
        return result
    ```

4.  **Database**
    The system automatically creates a SQLite database (`memories.db`) in the working directory. Ensure the app has write permissions.

## 📂 Project Structure
- `src/core/valison_processor.py`: Handles Gemini API interaction (Zero Cost).
- `src/core/updater.py`: Handles Semantic Diffing logic.
- `src/core/engine.py`: Main class `VisualMemoryEngine`.
- `src/core/memory_store.py`: SQLite storage logic.

## ✅ Production CLI Usage
The system exposes a robust CLI for integration:

```bash
# Process an image and get JSON output
python main.py path/to/image.png

# Process with metadata
python main.py screenshot.png --metadata '{"source": "user_123", "context": "dashboard"}'
```

**Output will be pure JSON**, making it easy to pipe into other tools or logs.


## ☁️ Serverless Database Setup (Turso)
To use Turso (Free & Fast) instead of local SQLite:

1.  **Sign up** at [turso.tech](https://turso.tech).
2.  **Create a DB**: `turso db create visual-memory`
3.  **Get URL**: `turso db show visual-memory --url`
4.  **Get Token**: `turso db tokens create visual-memory`
5.  **Update .env**:
    ```bash
    TURSO_DATABASE_URL="libsql://visual-memory-user.turso.io"
    TURSO_AUTH_TOKEN="ey..."
    ```

The system will automatically switch to Cloud Mode when these variables are detected.
