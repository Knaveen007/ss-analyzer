# src/utils/validation.py
class ContentValidator:
    """Validate extracted content for quality and completeness"""
    
    @staticmethod
    def validate_extraction(content: Dict, image_info: Dict = None) -> Dict[str, Any]:
        """Validate the extracted content meets quality standards"""
        validation_results = {
            'is_valid': True,
            'score': 0.0,
            'issues': [],
            'warnings': [],
            'suggestions': []
        }
        
        # 1. Check required fields
        required_fields = ['extracted_text', 'full_summary']
        for field in required_fields:
            if field not in content or not content[field]:
                validation_results['is_valid'] = False
                validation_results['issues'].append(f"Missing required field: {field}")
        
        # 2. Text quality checks
        if 'extracted_text' in content:
            text = content['extracted_text']
            
            # Length check
            if len(text) < 10:
                validation_results['warnings'].append("Extracted text is very short")
                validation_results['score'] -= 0.2
            
            # Garbage text detection
            if ContentValidator._is_garbage_text(text):
                validation_results['is_valid'] = False
                validation_results['issues'].append("Extracted text appears to be garbage/nonsense")
            
            # Repetition check
            if ContentValidator._has_excessive_repetition(text):
                validation_results['warnings'].append("Text has excessive repetition")
                validation_results['score'] -= 0.1
        
        # 3. Summary quality
        if 'full_summary' in content:
            summary = content['full_summary']
            if len(summary) < 20:
                validation_results['warnings'].append("Summary is very short")
                validation_results['score'] -= 0.1
            
            if len(summary) > 1000:
                validation_results['warnings'].append("Summary is too long")
                validation_results['score'] -= 0.1
        
        # 4. Calculate overall score (0-1)
        base_score = content.get('confidence', 0.5)
        validation_results['score'] = max(0, min(1, base_score + validation_results['score']))
        
        # 5. Add suggestions for improvement
        if validation_results['score'] < 0.7:
            validation_results['suggestions'].append(
                "Consider reprocessing with different vision API parameters"
            )
        
        return validation_results
    
    @staticmethod
    def _is_garbage_text(text: str) -> bool:
        """Detect if text is garbage/nonsense"""
        # Check for excessive special characters
        if len(text) > 0:
            special_char_ratio = sum(1 for c in text if not c.isalnum() and not c.isspace()) / len(text)
            if special_char_ratio > 0.5:
                return True
        
        # Check for repetitive patterns
        words = text.split()
        if len(words) > 10:
            unique_words = set(words)
            if len(unique_words) / len(words) < 0.3:
                return True
        
        return False
    
    @staticmethod
    def _has_excessive_repetition(text: str) -> bool:
        """Check for excessive repetition in text"""
        words = text.lower().split()
        if len(words) < 5:
            return False
        
        word_counts = {}
        for word in words:
            if len(word) > 3:  # Ignore short words
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Check if any word appears more than 30% of the time
        max_count = max(word_counts.values(), default=0)
        return max_count / len(words) > 0.3