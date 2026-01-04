
from src.core.vision_processor import VisionProcessor
from src.core.memory_store import MemoryDatabase
from src.core.updater import MemoryUpdater
from src.core.fingerprint import ImageFingerprinter
from typing import Dict, Any, Optional
import os
import uuid

class VisualMemoryEngine:
    """
    Main entry point for the Visual Memory System for your Product.
    Integrates Vision, Storage, and Updates.
    """
    
    def __init__(self, api_keys: Dict[str, str], db_path: str = "memories.db"):
        self.vision = VisionProcessor(api_keys)
        self.store = MemoryDatabase(db_path)
        self.updater = MemoryUpdater()
        
    async def process_screen(self, image_path: str, metadata: Dict = None) -> Dict[str, Any]:
        """
        Process a new screenshot/image for memory.
        
        Args:
            image_path: Path to the image file
            metadata: Optional metadata (e.g., {'window_title': 'Project X', 'app_name': 'VS Code'})
            
        Returns:
            Dict containing the processing result (status, memory_id, summary, changes?)
        """
        # 1. Generate Fingerprints (Local, Fast)
        fingerprints = ImageFingerprinter.generate_all_fingerprints(image_path)
        content_hash = fingerprints['content']
        
        # 2. Check for Exact Match (Duplicate)
        existing_exact = self.store.find_by_content_hash(content_hash)
        if existing_exact:
            return {
                "status": "unchanged",
                "memory_id": existing_exact['id'],
                "summary": existing_exact['summary'],
                "message": "Exact duplicate found. No processing needed."
            }
            
        # 3. Vision API Extraction (Cloud, Smart)
        # Attempt to get OpenAI key, fallback to Gemini or use both based on config
        # Here we just delegate to the hybrid processor
        structured_content = await self.vision.process_hybrid(image_path)
        
        # 4. Check for Semantic Updates (Automatic Similarity Search)
        # We search by perceptual hash to find the "closest" previous version.
        
        perceptual_hash = fingerprints.get('perceptual')
        target_memory_id = None
        
        # Check explicit first (if provided)
        if metadata and metadata.get('update_memory_id'):
            target_memory_id = metadata.get('update_memory_id')
        else:
            # Auto-detect similar image
            closest_match = self.store.find_by_perceptual_hash(perceptual_hash, threshold=4)
            if closest_match:
                target_memory_id = closest_match['id']
                print(f"🔄 Auto-linked to similar memory: {target_memory_id}")

        if target_memory_id:
            # Explicit update requested or Similar image found
            old_memory = self.store.get_memory(target_memory_id)
            if old_memory:
                return self._perform_update(target_memory_id, old_memory, structured_content)

        # 5. Save as New Memory
        new_id = str(uuid.uuid4())
        self.store.add_memory(new_id, structured_content, fingerprints, metadata)
        
        return {
            "status": "created",
            "memory_id": new_id,
            "summary": structured_content.get('full_summary'),
            "message": "New memory created successfully."
        }
    
    def _perform_update(self, memory_id: str, old_memory: Dict, new_content: Dict) -> Dict:
        """Helper to run the semantic diff and update loop"""
        update_result = self.updater.update_memory_incrementally(
            memory_id,
            old_memory.get('structured_content', {}),
            new_content
        )
        
        if update_result['updated']:
            self.store.update_memory(
                memory_id,
                update_result['new_content'],
                update_result['changes'],
                update_result['version_increment']
            )
            return {
                "status": "updated",
                "memory_id": memory_id,
                "summary": update_result['new_summary'],
                "changes_count": len(update_result['changes']),
                "message": "Memory updated with semantic changes."
            }
        else:
            return {
                "status": "skipped",
                "memory_id": memory_id,
                "message": "No semantic changes detected."
            }
