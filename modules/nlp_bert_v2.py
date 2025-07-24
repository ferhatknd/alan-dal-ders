"""
Advanced Turkish BERT + Semantic Similarity System (v2.0)
========================================================

Rebuilt from scratch based on 2025 best practices:
- Turkish BERT with optimized fill-mask strategy
- Advanced semantic similarity with sentence transformers
- Smart space detection and pattern-aware text correction
- Hybrid approach combining both systems optimally

Key Improvements:
1. Proper Turkish BERT model selection and usage
2. Advanced masking techniques for text correction
3. Optimized semantic similarity with better thresholds
4. Context-aware correction algorithms
5. Performance-optimized with caching and batching

Authors: Claude Code
Date: 2025-07-24
Version: 2.0
"""

import re
import logging
import time
from typing import List, Dict, Tuple, Optional, Union
from functools import lru_cache
import warnings
from dataclasses import dataclass
from enum import Enum

# Suppress transformer warnings
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*resume_download.*")

# Import dependencies with fallbacks
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForMaskedLM, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    torch = None

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    np = None

try:
    import nltk
    from nltk.tokenize import sent_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False


class CorrectionConfidence(Enum):
    """Confidence levels for text corrections."""
    LOW = 0.3
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 0.9


@dataclass
class CorrectionResult:
    """Result of a text correction operation."""
    original: str
    corrected: str
    confidence: float
    method: str
    applied: bool


class TurkishPatternDetector:
    """Advanced pattern detection for Turkish text issues."""
    
    def __init__(self):
        # Compile patterns once for performance
        self.patterns = {
            'word_splits': re.compile(r'\b(\w{3,})\s+(\w{1,3})\b'),
            'affix_splits': re.compile(r'\b(\w+[aeiouüöıi])\s+(n[ıiıuüa]|[ıiıuüa]n|d[aeiıuüo]|t[aeiıuüo]|[lnrmk][aeiıuüo])\b'),
            'punctuation_spacing': re.compile(r'\s+([,.;:!?])\s*'),
            'hyphen_spacing': re.compile(r'\s*-\s*'),
            'compound_separation': re.compile(r'\b(\w+)(lar|ler)\s+(ı|i|ü|u|ın|in|ün|un)\b'),
            'possessive_splits': re.compile(r'\b(\w+)\s+(s[ıiıuüa])\b'),
        }
        
        # Common Turkish word fixes from PDF parsing errors
        self.common_fixes = {
            # Direct replacements
            'Büyüklükle r': 'Büyüklükler',
            'Lehim leme': 'Lehimleme', 
            'Ölçü m': 'Ölçüm',
            'day alı': 'dayalı',
            'amacı nı': 'amacını',
            'v e': 've',
            'kon ulan': 'konulan',
            'a çıklar': 'açıklar',
            'sa yar': 'sayar',
            'üre ci': 'üreci',
            'çizi mi': 'çizimi',
            'bilgi sa yar': 'bilgi sayar',
            'öğren me': 'öğrenme',
            'sü re ci': 'süreci',
        }
    
    def detect_problems(self, text: str) -> List[Dict]:
        """Detect all potential problems in text with positions and types."""
        problems = []
        
        # Check common fixes first (highest confidence)
        for wrong, correct in self.common_fixes.items():
            if wrong.lower() in text.lower():
                start = text.lower().find(wrong.lower())
                if start != -1:
                    problems.append({
                        'type': 'common_fix',
                        'original': text[start:start+len(wrong)],
                        'suggested': correct,
                        'start': start,
                        'end': start + len(wrong),
                        'confidence': CorrectionConfidence.VERY_HIGH.value
                    })
        
        # Pattern-based detection
        for pattern_name, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                suggested = self._generate_pattern_fix(pattern_name, match)
                if suggested and suggested != match.group(0):
                    problems.append({
                        'type': pattern_name,
                        'original': match.group(0),
                        'suggested': suggested,
                        'start': match.start(),
                        'end': match.end(),
                        'confidence': self._get_pattern_confidence(pattern_name)
                    })
        
        # Sort by position to handle overlaps
        problems.sort(key=lambda x: x['start'])
        return self._remove_overlaps(problems)
    
    def _generate_pattern_fix(self, pattern_name: str, match: re.Match) -> Optional[str]:
        """Generate correction suggestion for a pattern match."""
        if pattern_name == 'word_splits':
            # Combine split words: "day alı" -> "dayalı"
            return match.group(1) + match.group(2)
        
        elif pattern_name == 'affix_splits':
            # Combine split affixes: "amacı nı" -> "amacını"
            return match.group(1) + match.group(2)
        
        elif pattern_name == 'punctuation_spacing':
            # Fix punctuation spacing: " , " -> ", "
            punct = match.group(1)
            return f"{punct} "
        
        elif pattern_name == 'hyphen_spacing':
            # Fix hyphen spacing: " - " -> "-"
            return "-"
        
        elif pattern_name == 'compound_separation':
            # Fix compound word separation: "uygulama lar ı" -> "uygulamaları"
            return match.group(1) + match.group(2) + match.group(3)
        
        elif pattern_name == 'possessive_splits':
            # Fix possessive splits: "kitap sı" -> "kitabı"
            return match.group(1) + match.group(2)
        
        return None
    
    def _get_pattern_confidence(self, pattern_name: str) -> float:
        """Get confidence level for different pattern types."""
        confidence_map = {
            'word_splits': CorrectionConfidence.HIGH.value,
            'affix_splits': CorrectionConfidence.VERY_HIGH.value,
            'punctuation_spacing': CorrectionConfidence.VERY_HIGH.value,
            'hyphen_spacing': CorrectionConfidence.HIGH.value,
            'compound_separation': CorrectionConfidence.MEDIUM.value,
            'possessive_splits': CorrectionConfidence.MEDIUM.value,
        }
        return confidence_map.get(pattern_name, CorrectionConfidence.LOW.value)
    
    def _remove_overlaps(self, problems: List[Dict]) -> List[Dict]:
        """Remove overlapping problems, keeping higher confidence ones."""
        if not problems:
            return problems
        
        result = []
        current = problems[0]
        
        for next_problem in problems[1:]:
            # Check if problems overlap
            if next_problem['start'] < current['end']:
                # Keep higher confidence problem
                if next_problem['confidence'] > current['confidence']:
                    current = next_problem
            else:
                result.append(current)
                current = next_problem
        
        result.append(current)
        return result


class AdvancedTurkishBERT:
    """Advanced Turkish BERT with optimized fill-mask strategy."""
    
    def __init__(self):
        self.device = self._get_optimal_device()
        self.model_name = "dbmdz/bert-base-turkish-cased"
        self.model = None
        self.tokenizer = None
        self.fill_mask_pipeline = None
        self.max_length = 512
        self.confidence_threshold = 0.85
        self._initialize_model()
    
    def _get_optimal_device(self) -> str:
        """Determine optimal device (Apple Silicon GPU, CUDA, or CPU)."""
        if not TRANSFORMERS_AVAILABLE or not torch:
            return "cpu"
        
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon GPU
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def _initialize_model(self):
        """Initialize Turkish BERT model with optimized settings."""
        if not TRANSFORMERS_AVAILABLE:
            logging.warning("Transformers not available. BERT correction disabled.")
            return
        
        try:
            logging.info(f"Loading Turkish BERT: {self.model_name}")
            start_time = time.time()
            
            # Load tokenizer with optimized settings
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                use_fast=True,  # Use fast tokenizer for performance
                do_lower_case=False  # Preserve case for Turkish
            )
            
            # Load model
            self.model = AutoModelForMaskedLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device != "cpu" else torch.float32
            )
            
            # Move to optimal device
            if self.device != "cpu":
                self.model = self.model.to(self.device)
            
            # Create optimized pipeline
            self.fill_mask_pipeline = pipeline(
                "fill-mask",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                top_k=10,  # Get more candidates
                return_all_scores=False
            )
            
            load_time = time.time() - start_time
            logging.info(f"Turkish BERT loaded in {load_time:.2f}s on {self.device}")
            
        except Exception as e:
            logging.error(f"Failed to load Turkish BERT: {e}")
            self.model = None
    
    def get_correction_suggestions(self, sentence: str, problem_area: str) -> List[Tuple[str, float]]:
        """Get BERT-based correction suggestions using advanced masking."""
        if not self.fill_mask_pipeline:
            return []
        
        try:
            # Smart masking strategy
            masked_versions = self._create_smart_masks(sentence, problem_area)
            all_suggestions = []
            
            for masked_sentence in masked_versions:
                # Ensure sentence isn't too long
                if len(self.tokenizer.encode(masked_sentence)) > self.max_length:
                    continue
                
                # Get BERT predictions
                predictions = self.fill_mask_pipeline(masked_sentence)
                
                # Process predictions
                if predictions:
                    for pred in predictions:
                        token_str = pred.get('token_str', '').strip()
                        score = pred.get('score', 0.0)
                        
                        if token_str and score > 0.1:  # Basic filtering
                            all_suggestions.append((token_str, float(score)))
            
            # Deduplicate and sort by score
            suggestion_dict = {}
            for suggestion, score in all_suggestions:
                if suggestion not in suggestion_dict or score > suggestion_dict[suggestion]:
                    suggestion_dict[suggestion] = score
            
            # Return top suggestions sorted by score
            sorted_suggestions = sorted(suggestion_dict.items(), key=lambda x: x[1], reverse=True)
            return sorted_suggestions[:5]  # Top 5 suggestions
            
        except Exception as e:
            logging.warning(f"BERT suggestion failed: {e}")
            return []
    
    def _create_smart_masks(self, sentence: str, problem_area: str) -> List[str]:
        """Create multiple smart mask versions for better suggestions."""
        if not self.tokenizer:
            return []
        
        mask_token = self.tokenizer.mask_token
        masked_versions = []
        
        # Strategy 1: Replace entire problem area
        masked_versions.append(sentence.replace(problem_area, mask_token))
        
        # Strategy 2: For split words, mask individual parts
        if ' ' in problem_area:
            parts = problem_area.split()
            for i, part in enumerate(parts):
                masked_parts = parts.copy()
                masked_parts[i] = mask_token
                masked_area = ' '.join(masked_parts)
                masked_versions.append(sentence.replace(problem_area, masked_area))
        
        # Strategy 3: For longer problems, create partial masks
        if len(problem_area.split()) > 2:
            words = problem_area.split()
            mid_point = len(words) // 2
            first_half = ' '.join(words[:mid_point])
            second_half = ' '.join(words[mid_point:])
            
            # Mask first half
            masked_versions.append(sentence.replace(problem_area, f"{mask_token} {second_half}"))
            # Mask second half  
            masked_versions.append(sentence.replace(problem_area, f"{first_half} {mask_token}"))
        
        return list(set(masked_versions))  # Remove duplicates


class EnhancedSemanticMatcher:
    """Enhanced semantic similarity matching with optimized performance."""
    
    def __init__(self):
        self.model = None
        self.embedding_cache = {}
        self.model_name = "all-MiniLM-L6-v2"  # Optimized for speed and accuracy
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize sentence transformer model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logging.warning("Sentence Transformers not available. Semantic matching disabled.")
            return
        
        try:
            logging.info(f"Loading Semantic Model: {self.model_name}")
            start_time = time.time()
            
            self.model = SentenceTransformer(self.model_name)
            
            load_time = time.time() - start_time
            logging.info(f"Semantic model loaded in {load_time:.2f}s")
            
        except Exception as e:
            logging.error(f"Failed to load semantic model: {e}")
            self.model = None
    
    @lru_cache(maxsize=1000)
    def _get_embedding(self, text: str):
        """Get cached embedding for text with LRU cache."""
        if not self.model or not np:
            return None
        
        try:
            # Normalize text
            normalized_text = text.strip().lower()
            embedding = self.model.encode(normalized_text, convert_to_tensor=False)
            return embedding
        except Exception:
            return None
    
    def get_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between two texts."""
        if not self.model or not np:
            return 0.0
        
        embedding1 = self._get_embedding(text1)
        embedding2 = self._get_embedding(text2)
        
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        try:
            similarity = cosine_similarity([embedding1], [embedding2])[0][0]
            return max(0.0, min(1.0, float(similarity)))  # Clamp to [0,1]
        except Exception:
            return 0.0
    
    def find_best_matches(self, query: str, candidates: List[str], threshold: float = 0.7) -> List[Tuple[str, float]]:
        """Find best semantic matches with optimized batch processing."""
        if not self.model or not candidates or not np:
            return []
        
        try:
            # Batch encode for efficiency
            all_texts = [query] + candidates
            embeddings = self.model.encode(all_texts, convert_to_tensor=False)
            
            query_embedding = embeddings[0:1]
            candidate_embeddings = embeddings[1:]
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, candidate_embeddings)[0]
            
            # Filter and sort results
            results = []
            for i, similarity in enumerate(similarities):
                if similarity >= threshold:
                    results.append((candidates[i], float(similarity)))
            
            return sorted(results, key=lambda x: x[1], reverse=True)
            
        except Exception as e:
            logging.warning(f"Batch similarity calculation failed: {e}")
            return []
    
    def semantic_find(self, query: str, content: str, threshold: float = 0.7) -> int:
        """Find semantic match position in content using sliding window."""
        if not self.model or not np:
            # Fallback to simple search
            return content.upper().find(query.upper())
        
        # Create sliding window candidates
        query_words = query.split()
        content_words = content.split()
        query_length = len(query_words)
        
        if query_length == 0 or query_length > len(content_words):
            return -1
        
        candidates = []
        positions = []
        
        # Create overlapping windows
        for i in range(len(content_words) - query_length + 1):
            candidate = ' '.join(content_words[i:i + query_length])
            candidates.append(candidate)
            
            # Calculate approximate character position
            char_pos = content.find(candidate)
            positions.append(char_pos if char_pos != -1 else -1)
        
        if not candidates:
            return -1
        
        # Find best semantic match
        matches = self.find_best_matches(query, candidates, threshold)
        
        if matches:
            best_match = matches[0][0]
            # Find position of best match
            for i, candidate in enumerate(candidates):
                if candidate == best_match:
                    return positions[i]
        
        return -1


class HybridTurkishCorrector:
    """Hybrid system combining BERT and Semantic Similarity optimally."""
    
    def __init__(self):
        self.pattern_detector = TurkishPatternDetector()
        self.bert_corrector = AdvancedTurkishBERT()
        self.semantic_matcher = EnhancedSemanticMatcher()
        self.correction_cache = {}
    
    def correct_text(self, text: str, use_bert: bool = True, use_semantic: bool = True) -> str:
        """Main correction function with hybrid approach."""
        if not text or not text.strip():
            return text
        
        # Check cache first
        cache_key = hash(text)
        if cache_key in self.correction_cache:
            return self.correction_cache[cache_key]
        
        start_time = time.time()
        
        try:
            # Step 1: Detect problems using pattern analysis
            problems = self.pattern_detector.detect_problems(text)
            
            if not problems:
                return text
            
            # Step 2: Apply corrections in order of confidence
            corrected_text = text
            corrections_applied = []
            
            # Sort problems by confidence (highest first)
            problems.sort(key=lambda x: x['confidence'], reverse=True)
            
            for problem in problems:
                correction_result = self._apply_single_correction(
                    corrected_text, problem, use_bert, use_semantic
                )
                
                if correction_result.applied:
                    corrected_text = correction_result.corrected
                    corrections_applied.append(correction_result)
            
            # Step 3: Final cleanup
            final_text = self._final_cleanup(corrected_text)
            
            # Cache result
            self.correction_cache[cache_key] = final_text
            
            processing_time = time.time() - start_time
            if corrections_applied:
                logging.info(f"Applied {len(corrections_applied)} corrections in {processing_time:.3f}s")
            
            return final_text
            
        except Exception as e:
            logging.error(f"Correction failed: {e}")
            return text
    
    def _apply_single_correction(self, text: str, problem: Dict, use_bert: bool, use_semantic: bool) -> CorrectionResult:
        """Apply a single correction with validation."""
        original = problem['original']
        suggested = problem['suggested']
        confidence = problem['confidence']
        
        # High confidence corrections are applied directly
        if confidence >= CorrectionConfidence.HIGH.value:
            corrected_text = text.replace(original, suggested, 1)
            return CorrectionResult(
                original=original,
                corrected=suggested,
                confidence=confidence,
                method='pattern_high_confidence',
                applied=True
            )
        
        # Medium confidence corrections need validation
        if confidence >= CorrectionConfidence.MEDIUM.value:
            # Use semantic similarity for validation
            if use_semantic and self.semantic_matcher.model:
                semantic_similarity = self.semantic_matcher.get_similarity(original, suggested)
                
                # If semantic similarity is high, apply correction
                if semantic_similarity >= 0.7:
                    corrected_text = text.replace(original, suggested, 1)
                    combined_confidence = (confidence + semantic_similarity) / 2
                    return CorrectionResult(
                        original=original,
                        corrected=suggested,
                        confidence=combined_confidence,
                        method='pattern_semantic_validated',
                        applied=True
                    )
        
        # Low confidence corrections need BERT validation
        if use_bert and self.bert_corrector.model:
            # Create sentence context around the problem
            sentence_context = self._extract_sentence_context(text, problem['start'], problem['end'])
            
            # Get BERT suggestions
            bert_suggestions = self.bert_corrector.get_correction_suggestions(sentence_context, original)
            
            # Check if any BERT suggestion matches our pattern suggestion
            for bert_suggestion, bert_score in bert_suggestions:
                if use_semantic and self.semantic_matcher.model:
                    semantic_sim = self.semantic_matcher.get_similarity(suggested, bert_suggestion)
                    if semantic_sim >= 0.8 and bert_score >= 0.5:
                        corrected_text = text.replace(original, bert_suggestion, 1)
                        combined_confidence = (confidence + bert_score + semantic_sim) / 3
                        return CorrectionResult(
                            original=original,
                            corrected=bert_suggestion,
                            confidence=combined_confidence,
                            method='pattern_bert_semantic_validated',
                            applied=True
                        )
        
        # If no validation passed, don't apply correction
        return CorrectionResult(
            original=original,
            corrected=suggested,
            confidence=confidence,
            method='not_applied',
            applied=False
        )
    
    def _extract_sentence_context(self, text: str, start: int, end: int, context_size: int = 100) -> str:
        """Extract sentence context around a problem area."""
        context_start = max(0, start - context_size)
        context_end = min(len(text), end + context_size)
        return text[context_start:context_end]
    
    def _final_cleanup(self, text: str) -> str:
        """Apply final cleanup rules."""
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Fix punctuation spacing
        text = re.sub(r'\s+([,.;:!?])', r'\1', text)
        text = re.sub(r'([,.;:!?])([^\s])', r'\1 \2', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text
    
    def semantic_find(self, query: str, content: str, threshold: float = 0.7) -> int:
        """Enhanced semantic find with fallback."""
        if self.semantic_matcher.model:
            return self.semantic_matcher.semantic_find(query, content, threshold)
        else:
            # Fallback to case-insensitive search
            return content.upper().find(query.upper())


# Global instances and factory functions
_hybrid_corrector_instance = None

def get_hybrid_corrector() -> HybridTurkishCorrector:
    """Get or create global hybrid corrector instance."""
    global _hybrid_corrector_instance
    if _hybrid_corrector_instance is None:
        _hybrid_corrector_instance = HybridTurkishCorrector()
    return _hybrid_corrector_instance

def correct_turkish_text_with_bert(text: str) -> str:
    """
    Main function for Turkish text correction with hybrid BERT + Semantic approach.
    
    Args:
        text (str): Input Turkish text to correct
        
    Returns:
        str: Corrected Turkish text
    """
    corrector = get_hybrid_corrector()
    return corrector.correct_text(text)

def semantic_find(query: str, content: str, threshold: float = 0.7) -> int:
    """
    Enhanced semantic find function.
    
    Args:
        query (str): Text to search for
        content (str): Content to search in  
        threshold (float): Minimum similarity threshold
        
    Returns:
        int: Position of best match or -1 if not found
    """
    corrector = get_hybrid_corrector()
    return corrector.semantic_find(query, content, threshold)

def get_semantic_matcher() -> EnhancedSemanticMatcher:
    """Get semantic matcher instance."""
    corrector = get_hybrid_corrector()
    return corrector.semantic_matcher

# Testing and debugging functions
def test_hybrid_system():
    """Test the hybrid correction system."""
    test_cases = [
        "day alı amacı nı tahvil , repo",
        "bilgi sa yar sistemleri",
        "öğren me süre ci",
        "Büyüklükle r ve Ölçü m",
        "Lehim leme v e montaj işlemleri",
        "kon ulan yöntem a çıklar"
    ]
    
    print("Hybrid Turkish BERT + Semantic Correction Test")
    print("=" * 60)
    
    corrector = get_hybrid_corrector()
    
    for test_text in test_cases:
        corrected = corrector.correct_text(test_text)
        print(f"Original:  {test_text}")
        print(f"Corrected: {corrected}")
        print("-" * 40)

def test_semantic_find():
    """Test semantic find functionality."""
    content = "Bu dersin amacı öğrencilere temel bilgileri vermektir. Ders kapsamında konular işlenecektir."
    
    test_queries = [
        "dersin amacı",
        "temel bilgiler", 
        "konular işlenecek",
        "Ders Amacı",  # Case difference
        "öğrenci bilgi"  # Partial match
    ]
    
    print("Semantic Find Test")
    print("=" * 40)
    print(f"Content: {content}")
    print()
    
    for query in test_queries:
        position = semantic_find(query, content, threshold=0.7)
        if position >= 0:
            found_text = content[position:position+len(query)]
            print(f"Query: '{query}' -> Found at position {position}: '{found_text}'")
        else:
            print(f"Query: '{query}' -> Not found")

if __name__ == "__main__":
    # Run tests
    test_hybrid_system()
    print("\n")
    test_semantic_find()