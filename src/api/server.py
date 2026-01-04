# src/api/server.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Optional
import uuid

app = FastAPI(title="Screenshot Memory System")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class MemoryAPI:
    def __init__(self):
        self.processor = VisionProcessor()
        self.db = MemoryDatabase()
        self.updater = MemoryUpdater()
    
    async def upload_screenshot(self, file: UploadFile) -> Dict:
        """Main endpoint for screenshot upload"""
        
        # 1. Save file temporarily
        temp_path = f"/tmp/{uuid.uuid4()}.png"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # 2. Generate fingerprints
        fingerprints = ImageFingerprinter.generate_all_fingerprints(temp_path)
        
        # 3. Check cache
        cached = await self._check_cache(fingerprints['content'])
        if cached:
            return cached
        
        # 4. Check if similar exists
        similar = self.db.find_similar(fingerprints['perceptual'])
        if similar:
            # Process with diff-only approach
            result = await self._process_update(similar, temp_path)
        else:
            # Full processing for new image
            result = await self._process_new(temp_path, fingerprints)
        
        # 5. Clean up and return
        os.remove(temp_path)
        return result
    
    async def query_memory(self, query: str, limit: int = 10) -> List[Dict]:
        """Query memories like ChatGPT"""
        # Semantic search implementation
        memories = self.db.search_memories(query, limit)
        
        # Format for ChatGPT-like interface
        formatted = []
        for memory in memories:
            formatted.append({
                'id': memory['id'],
                'summary': memory['summary'],
                'content_preview': memory['structured_content'][:200],
                'last_updated': memory['updated_at'],
                'version': memory['version']
            })
        
        return formatted