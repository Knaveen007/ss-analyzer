import asyncio
import argparse
import json
import os
import sys
from dotenv import load_dotenv
from src.core.engine import VisualMemoryEngine

# Load environment
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Visual Memory Engine CLI")
    parser.add_argument("image_path", help="Path to the image file to process")
    parser.add_argument("--metadata", default="{}", help="JSON string of metadata (optional)")
    
    args = parser.parse_args()
    
    # Validation
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print(json.dumps({"error": "OPENROUTER_API_KEY not found in environment"}), file=sys.stderr)
        sys.exit(1)
        
    if not os.path.exists(args.image_path):
        print(json.dumps({"error": f"File not found: {args.image_path}"}), file=sys.stderr)
        sys.exit(1)

    try:
        meta = json.loads(args.metadata)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON for --metadata"}), file=sys.stderr)
        sys.exit(1)

    # Execution
    try:
        engine = VisualMemoryEngine(api_keys={"openrouter": api_key})
        
        # Run async process
        result = asyncio.run(engine.process_screen(args.image_path, metadata=meta))
        
        # Output JSON result
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
