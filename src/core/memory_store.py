import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from contextlib import contextmanager
try:
    import libsql_experimental as libsql
    LIBSQL_AVAILABLE = True
except ImportError:
    LIBSQL_AVAILABLE = False

class MemoryDatabase:
    """Optimized SQLite storage with WAL mode"""
    
    def __init__(self, db_path: str = "memories.db"):
        self.db_path = db_path
        self.turso_url = os.getenv("TURSO_DATABASE_URL")
        self.turso_token = os.getenv("TURSO_AUTH_TOKEN")
        self.is_remote = bool(self.turso_url and LIBSQL_AVAILABLE)
        
        if self.is_remote:
            print(f"🔌 Connected to Turso DB: {self.turso_url}")
        else:
            print(f"💾 Using Local SQLite: {self.db_path}")
            
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        if self.is_remote:
            # LibSQL Connection
            if self.turso_token:
                conn = libsql.connect(self.turso_url, auth_token=self.turso_token)
            else:
                conn = libsql.connect(self.turso_url)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        else:
            # Standard SQLite Connection
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_database(self):
        """Initialize database with optimized schema"""
        with self._get_connection() as conn:
            # Common Schema
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content_hash TEXT UNIQUE,
                    perceptual_hash TEXT,
                    structured_content BLOB,
                    summary TEXT,
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT,
                    version INTEGER,
                    diff_content BLOB,
                    summary_diff TEXT,
                    created_at TIMESTAMP,
                    FOREIGN KEY (memory_id) REFERENCES memories(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_cache (
                    content_hash TEXT PRIMARY KEY,
                    memory_data BLOB,
                    last_accessed TIMESTAMP,
                    access_count INTEGER DEFAULT 0
                )
            """)
            
            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_perceptual ON memories(perceptual_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_updated ON memories(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_access ON memory_cache(last_accessed)")

    def add_memory(self, memory_id: str, content: Dict, fingerprints: Dict, metadata: Dict = None):
        """Add a new memory to the store"""
        metadata = metadata or {}
        now = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO memories (
                    id, content_hash, perceptual_hash, structured_content, 
                    summary, created_at, updated_at, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id,
                fingerprints.get('content'),
                fingerprints.get('perceptual'),
                json.dumps(content),
                content.get('full_summary', ''),
                now,
                now,
                json.dumps(metadata)
            ))

    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """Retrieve a memory by ID"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()
            
            if row:
                if isinstance(row, tuple):
                    # Manual mapping if tuple (ORDER MUST MATCH CREATE TABLE)
                    # id, content_hash, perceptual_hash, structured_content, summary, version, created_at, updated_at, metadata
                    data = {
                        "id": row[0],
                        "content_hash": row[1],
                        "perceptual_hash": row[2],
                        "structured_content": row[3],
                        "summary": row[4],
                        "version": row[5],
                        "created_at": row[6],
                        "updated_at": row[7],
                        "metadata": row[8]
                    }
                else:
                    data = dict(row)
                data['structured_content'] = json.loads(data['structured_content'])
                data['metadata'] = json.loads(data['metadata']) if data['metadata'] else {}
                return data
            return None

    def find_by_content_hash(self, content_hash: str) -> Optional[Dict]:
        """Find memory by exact content hash"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE content_hash = ?", (content_hash,)
            ).fetchone()
            
            if row:
                data = dict(row)
                data['structured_content'] = json.loads(data['structured_content'])
                return data
            return None
            
            
    def find_by_perceptual_hash(self, p_hash: str, threshold: int = 4) -> Optional[Dict]:
        """Find memory by perceptual hash similarity (Hamming distance)"""
        # Note: For massive scale, use Vector Search (pgvector/Turso vector).
        # For typical usage, scanning this index structure is acceptable.
        
        # We need to perform distance calc. We can fetch matching first 2 chars 
        # to filter, or just scan all for now since we are optimizing for accuracy.
        
        with self._get_connection() as conn:
            # We fetch ID and P_HASH to find closest
            cursor = conn.execute("SELECT id, perceptual_hash FROM memories")
            candidates = cursor.fetchall()
            
            best_match = None
            min_dist = 1000
            
            target_hash = p_hash
            
            import imagehash
            import numpy as np
            
            def hamming_distance(s1, s2):
                # Simple string hamming distance
                if len(s1) != len(s2): return 1000
                return sum(c1 != c2 for c1, c2 in zip(s1, s2))

            for row in candidates:
                # Handle tuple (libsql) or Row object (sqlite)
                if isinstance(row, tuple):
                    candidate_id = row[0]
                    candidate_hash = row[1]
                else:
                    candidate_id = row['id']
                    candidate_hash = row['perceptual_hash']
                    
                if not candidate_hash: continue
                
                dist = hamming_distance(target_hash, candidate_hash)
                    
                if dist <= threshold and dist < min_dist:
                    min_dist = dist
                    best_match = candidate_id
            
            if best_match:
                return self.get_memory(best_match)
                
            return None

    def update_memory(self, memory_id: str, new_content: Dict, 
                     changes: list, version_inc: int):
        """Update an existing memory with new content and log changes"""
        now = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            # 1. Update main memory record
            conn.execute("""
                UPDATE memories 
                SET structured_content = ?, 
                    summary = ?,
                    version = version + ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                json.dumps(new_content),
                new_content.get('full_summary', ''),
                version_inc,
                now,
                memory_id
            ))
            
            # 2. Log version history
            # Get current version for history
            current_ver = conn.execute(
                "SELECT version FROM memories WHERE id = ?", (memory_id,)
            ).fetchone()[0]
            
            conn.execute("""
                INSERT INTO memory_versions (
                    memory_id, version, diff_content, created_at
                ) VALUES (?, ?, ?, ?)
            """, (
                memory_id,
                current_ver,
                json.dumps(changes),
                now
            ))

    def get_recent_memories(self, limit: int = 10) -> list:
        """Fetch recent memories for UI display"""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM memories ORDER BY updated_at DESC LIMIT ?", (limit,)
            )
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                if isinstance(row, tuple):
                     # Manual mapping for LibSQL tuples
                    data = {
                        "id": row[0],
                        "summary": row[4],
                        "updated_at": row[7],
                         # Add other fields if needed for UI, keeping it light
                    }
                else:
                    data = dict(row)
                results.append(data)
            return results