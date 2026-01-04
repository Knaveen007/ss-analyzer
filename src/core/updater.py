import difflib
import json
from typing import List, Tuple, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import hashlib

@dataclass
class DiffOperation:
    """Represents a single change operation"""
    op: str  # 'update', 'add', 'remove', 'move'
    path: List[str]  # JSON path to the element
    old_value: Any = None
    new_value: Any = None
    confidence: float = 1.0
    
    def to_dict(self):
        return {
            'op': self.op,
            'path': self.path,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'confidence': self.confidence
        }

class MemoryUpdater:
    """Complete Memory Updater with full diff and update logic"""
    
    def __init__(self):
        self.diff_cache = {}
    
    def compute_text_diff(self, old_text: str, new_text: str) -> List[Dict[str, Any]]:
        """Compute minimal text differences with context"""
        diff = difflib.SequenceMatcher(None, old_text, new_text, autojunk=False)
        operations = []
        
        for tag, i1, i2, j1, j2 in diff.get_opcodes():
            if tag == 'replace':
                operations.append({
                    'op': 'replace',
                    'position': i1,
                    'old_length': i2 - i1,
                    'old_text': old_text[i1:i2],
                    'new_text': new_text[j1:j2],
                    'context_before': old_text[max(0, i1-50):i1],
                    'context_after': old_text[i2:min(len(old_text), i2+50)]
                })
            elif tag == 'delete':
                operations.append({
                    'op': 'delete',
                    'position': i1,
                    'length': i2 - i1,
                    'text': old_text[i1:i2],
                    'context_before': old_text[max(0, i1-50):i1],
                    'context_after': old_text[i2:min(len(old_text), i2+50)]
                })
            elif tag == 'insert':
                operations.append({
                    'op': 'insert',
                    'position': i1,
                    'text': new_text[j1:j2],
                    'context_before': old_text[max(0, i1-50):i1],
                    'context_after': old_text[i1:min(len(old_text), i1+50)]
                })
        
        return operations
    
    def _compute_structured_diff(self, old: Dict, new: Dict) -> List[DiffOperation]:
        """Compute semantic diff between two structured contents"""
        operations = []
        
        # Compare root-level fields
        all_keys = set(old.keys()).union(set(new.keys()))
        
        for key in all_keys:
            if key.startswith('_'):
                continue  # Skip metadata fields
            
            old_val = old.get(key)
            new_val = new.get(key)
            
            if key not in old:
                # New key added
                operations.append(DiffOperation(
                    op='add',
                    path=[key],
                    new_value=new_val,
                    confidence=1.0
                ))
            elif key not in new:
                # Key removed
                operations.append(DiffOperation(
                    op='remove',
                    path=[key],
                    old_value=old_val,
                    confidence=1.0
                ))
            else:
                # Key exists in both, compare values
                self._compare_values(old_val, new_val, [key], operations)
        
        return operations
    
    def _compare_values(self, old_val: Any, new_val: Any, 
                       path: List[str], operations: List[DiffOperation]):
        """Recursively compare values and record changes"""
        
        # Type change
        if type(old_val) != type(new_val):
            operations.append(DiffOperation(
                op='update',
                path=path,
                old_value=old_val,
                new_value=new_val,
                confidence=1.0
            ))
            return
        
        # Handle different types
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            self._compare_dicts(old_val, new_val, path, operations)
        elif isinstance(old_val, list) and isinstance(new_val, list):
            self._compare_lists(old_val, new_val, path, operations)
        elif old_val != new_val:
            # Primitive values that changed
            operations.append(DiffOperation(
                op='update',
                path=path,
                old_value=old_val,
                new_value=new_val,
                confidence=self._compute_similarity(old_val, new_val)
            ))
    
    def _compare_dicts(self, old_dict: Dict, new_dict: Dict, 
                      path: List[str], operations: List[DiffOperation]):
        """Compare two dictionaries recursively"""
        all_keys = set(old_dict.keys()).union(set(new_dict.keys()))
        
        for key in all_keys:
            if key.startswith('_'):
                continue
            
            new_path = path + [key]
            old_val = old_dict.get(key)
            new_val = new_dict.get(key)
            
            if key not in old_dict:
                # New key
                operations.append(DiffOperation(
                    op='add',
                    path=new_path,
                    new_value=new_val
                ))
            elif key not in new_dict:
                # Removed key
                operations.append(DiffOperation(
                    op='remove',
                    path=new_path,
                    old_value=old_val
                ))
            else:
                # Compare values
                self._compare_values(old_val, new_val, new_path, operations)
    
    def _compare_lists(self, old_list: List, new_list: List, 
                      path: List[str], operations: List[DiffOperation]):
        """Compare two lists with semantic understanding"""
        
        # Simple case: lists of primitives
        if (all(isinstance(x, (str, int, float, bool)) for x in old_list) and
            all(isinstance(x, (str, int, float, bool)) for x in new_list)):
            
            # Find added and removed items
            added = [x for x in new_list if x not in old_list]
            removed = [x for x in old_list if x not in new_list]
            
            for item in added:
                operations.append(DiffOperation(
                    op='add',
                    path=path,
                    new_value=item
                ))
            
            for item in removed:
                operations.append(DiffOperation(
                    op='remove',
                    path=path,
                    old_value=item
                ))
            
            return
        
        # Complex case: lists of objects - use heuristic matching
        # This is simplified; in production you'd want a more sophisticated algorithm
        if old_list == new_list:
            return  # No changes
        
        # Mark entire list as changed (for simplicity in hackathon)
        operations.append(DiffOperation(
            op='update',
            path=path,
            old_value=old_list,
            new_value=new_list,
            confidence=0.8
        ))
    
    def _compute_similarity(self, old_val: Any, new_val: Any) -> float:
        """Compute similarity between two values (0-1)"""
        if old_val == new_val:
            return 1.0
        
        if isinstance(old_val, str) and isinstance(new_val, str):
            # String similarity
            if not old_val or not new_val:
                return 0.0
            
            # Simple Jaccard similarity on words
            old_words = set(old_val.lower().split())
            new_words = set(new_val.lower().split())
            
            if not old_words or not new_words:
                return 0.0
            
            intersection = len(old_words.intersection(new_words))
            union = len(old_words.union(new_words))
            
            return intersection / union
        elif isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
            # Numeric similarity
            if old_val == 0 and new_val == 0:
                return 1.0
            elif old_val == 0 or new_val == 0:
                return 0.0
            
            diff = abs(old_val - new_val)
            max_val = max(abs(old_val), abs(new_val))
            return 1.0 - (diff / max_val)
        
        return 0.0
    
    def _update_nested(self, obj: Dict, path: List[str], value: Any):
        """Update a nested field in the object"""
        current = obj
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        if isinstance(current, dict):
            current[path[-1]] = value
        elif isinstance(current, list):
            index = int(path[-1])
            if 0 <= index < len(current):
                current[index] = value
            else:
                raise IndexError(f"Index {index} out of bounds for list")
    
    def _add_to_nested(self, obj: Dict, path: List[str], value: Any):
        """Add a value to a nested structure"""
        current = obj
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        last_key = path[-1]
        
        if isinstance(current, dict):
            if last_key not in current:
                current[last_key] = value
            else:
                # Key already exists, convert to list if needed
                existing = current[last_key]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    current[last_key] = [existing, value]
        elif isinstance(current, list):
            index = int(last_key)
            if index >= len(current):
                current.extend([None] * (index - len(current) + 1))
            current[index] = value
    
    def _remove_from_nested(self, obj: Dict, path: List[str]):
        """Remove a value from a nested structure"""
        current = obj
        for key in path[:-1]:
            if key not in current:
                return  # Path doesn't exist
            current = current[key]
        
        last_key = path[-1]
        
        if isinstance(current, dict) and last_key in current:
            del current[last_key]
        elif isinstance(current, list):
            index = int(last_key)
            if 0 <= index < len(current):
                current.pop(index)
    
    def apply_diff(self, old_content: Dict, diff_operations: List[DiffOperation]) -> Dict:
        """Apply diff operations to structured content"""
        # Deep copy to avoid modifying original
        import copy
        new_content = copy.deepcopy(old_content)
        
        for operation in diff_operations:
            try:
                if operation.op == 'update':
                    self._update_nested(new_content, operation.path, operation.new_value)
                elif operation.op == 'add':
                    self._add_to_nested(new_content, operation.path, operation.new_value)
                elif operation.op == 'remove':
                    self._remove_from_nested(new_content, operation.path)
            except (KeyError, IndexError, TypeError) as e:
                print(f"Warning: Failed to apply operation {operation.op} at {operation.path}: {e}")
                # Continue with other operations
        
        return new_content
    
    def _generate_incremental_summary(self, old_summary: str, 
                                     changes: List[DiffOperation],
                                     new_content: Dict) -> str:
        """Generate updated summary based on changes"""
        
        if not changes:
            return old_summary
        
        # Extract key changes to incorporate into summary
        significant_changes = []
        
        for change in changes:
            # Look for significant changes in key fields
            if any(keyword in ' '.join(change.path) for keyword in 
                  ['extracted_text', 'key_points', 'ui_components', 'content_type']):
                
                if change.op == 'add':
                    significant_changes.append(f"Added {change.path[-1]}: {change.new_value}")
                elif change.op == 'remove':
                    significant_changes.append(f"Removed {change.path[-1]}: {change.old_value}")
                elif change.op == 'update':
                    if isinstance(change.old_value, str) and isinstance(change.new_value, str):
                        if len(change.new_value) - len(change.old_value) > 50:  # Significant text addition
                            significant_changes.append(f"Updated {change.path[-1]} with additional content")
        
        if not significant_changes:
            # No significant changes, keep old summary
            return old_summary
        
        # Create new summary by incorporating changes
        changes_text = "; ".join(significant_changes[:3])  # Limit to 3 most significant
        
        # Check if the old summary mentions specific elements that changed
        old_summary_lower = old_summary.lower()
        
        # Simple update: append changes to existing summary
        if len(old_summary) < 200:
            # Room to add changes
            updated_summary = f"{old_summary} [Updated: {changes_text}]"
        else:
            # Replace part of summary with changes
            # Split summary and insert changes
            sentences = old_summary.split('. ')
            if len(sentences) > 1:
                # Insert changes after first sentence
                sentences.insert(1, f"Updated: {changes_text}")
                updated_summary = '. '.join(sentences)
            else:
                # Append changes
                updated_summary = f"{old_summary} [Updated: {changes_text}]"
        
        # Ensure summary doesn't get too long
        if len(updated_summary) > 500:
            updated_summary = updated_summary[:497] + "..."
        
        return updated_summary
    
    def update_memory_incrementally(self, memory_id: str, 
                                  old_content: Dict, 
                                  new_content: Dict) -> Dict:
        """Smart incremental update with full implementation"""
        
        # 1. Compute structured differences
        changes = self._compute_structured_diff(old_content, new_content)
        
        if not changes:
            # No changes detected
            return {
                'updated': False,
                'memory_id': memory_id,
                'changes': [],
                'new_content': old_content,
                'new_summary': old_content.get('full_summary', ''),
                'version_increment': 0
            }
        
        # 2. Apply changes to create new version
        updated_content = self.apply_diff(old_content, changes)
        
        # 3. Generate updated summary
        old_summary = old_content.get('full_summary', '')
        new_summary = self._generate_incremental_summary(
            old_summary, 
            changes, 
            updated_content
        )
        
        # Update the summary in the content
        updated_content['full_summary'] = new_summary
        
        # 4. Compute text diffs for key text fields
        text_diffs = {}
        
        text_fields = ['extracted_text', 'layout_description', 'full_summary']
        for field in text_fields:
            old_text = old_content.get(field, '')
            new_text = updated_content.get(field, '')
            if old_text != new_text:
                text_diffs[field] = self.compute_text_diff(old_text, new_text)
        
        # 5. Prepare diff log entry
        diff_log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operations': [op.to_dict() for op in changes],
            'text_diffs': text_diffs,
            'change_count': len(changes),
            'change_hash': self._compute_changes_hash(changes)
        }
        
        return {
            'updated': True,
            'memory_id': memory_id,
            'changes': [op.to_dict() for op in changes],
            'diff_log_entry': diff_log_entry,
            'new_content': updated_content,
            'new_summary': new_summary,
            'version_increment': 1
        }
    
    def _compute_changes_hash(self, changes: List[DiffOperation]) -> str:
        """Compute hash of changes for deduplication"""
        changes_data = []
        for change in changes:
            changes_data.append(f"{change.op}:{':'.join(change.path)}:{change.old_value}:{change.new_value}")
        
        changes_str = '|'.join(sorted(changes_data))
        return hashlib.md5(changes_str.encode()).hexdigest()
    
    def compress_diffs(self, diff_log: List[Dict]) -> List[Dict]:
        """Compress multiple diffs into minimal representation"""
        if len(diff_log) <= 1:
            return diff_log
        
        # Group consecutive similar diffs
        compressed = []
        current = diff_log[0]
        
        for next_diff in diff_log[1:]:
            # Check if diffs can be merged (similar operations)
            if self._can_merge_diffs(current, next_diff):
                current = self._merge_diffs(current, next_diff)
            else:
                compressed.append(current)
                current = next_diff
        
        compressed.append(current)
        return compressed
    
    def _can_merge_diffs(self, diff1: Dict, diff2: Dict) -> bool:
        """Check if two diffs can be merged"""
        # Simplified: merge if they're within 5 minutes and have similar operations
        time1 = datetime.fromisoformat(diff1['timestamp'])
        time2 = datetime.fromisoformat(diff2['timestamp'])
        
        time_diff = abs((time2 - time1).total_seconds())
        if time_diff > 300:  # 5 minutes
            return False
        
        # Check if operations are similar
        ops1 = set(str(op) for op in diff1['operations'])
        ops2 = set(str(op) for op in diff2['operations'])
        
        similarity = len(ops1.intersection(ops2)) / max(len(ops1), len(ops2))
        return similarity > 0.5
    
    def _merge_diffs(self, diff1: Dict, diff2: Dict) -> Dict:
        """Merge two diffs into one"""
        merged_ops = diff1['operations'] + diff2['operations']
        
        return {
            'timestamp': diff2['timestamp'],  # Use later timestamp
            'operations': merged_ops,
            'text_diffs': {**diff1.get('text_diffs', {}), **diff2.get('text_diffs', {})},
            'change_count': diff1['change_count'] + diff2['change_count'],
            'change_hash': hashlib.md5(
                (diff1['change_hash'] + diff2['change_hash']).encode()
            ).hexdigest(),
            'merged_from': [diff1.get('change_hash'), diff2.get('change_hash')]
        }