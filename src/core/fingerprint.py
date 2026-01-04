# src/core/fingerprint.py
import hashlib
from PIL import Image
import imagehash
import numpy as np
from dataclasses import dataclass

class ImageFingerprinter:
    """Generate multiple fingerprints for accurate change detection"""
    
    @staticmethod
    def content_hash(image_bytes: bytes) -> str:
        """SHA-256 of raw bytes"""
        return hashlib.sha256(image_bytes).hexdigest()
    
    @staticmethod
    def perceptual_hash(image: Image.Image) -> str:
        """Perceptual hash for similar images"""
        return str(imagehash.phash(image))
    
    @staticmethod
    def structural_hash(image: Image.Image) -> str:
        """Hash based on layout/structure"""
        # Convert to grayscale, resize, compute hash
        gray = image.convert('L').resize((32, 32))
        pixels = np.array(gray).flatten()
        return hashlib.sha256(pixels.tobytes()).hexdigest()
    
    @staticmethod
    def generate_all_fingerprints(image_path: str) -> dict:
        """Generate all fingerprint types"""
        with Image.open(image_path) as img:
            with open(image_path, 'rb') as f:
                content = f.read()
            
            return {
                'content': ImageFingerprinter.content_hash(content),
                'perceptual': ImageFingerprinter.perceptual_hash(img),
                'structural': ImageFingerprinter.structural_hash(img),
                'size': img.size,
                'mode': img.mode
            }