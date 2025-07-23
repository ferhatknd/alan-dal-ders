"""
Turkish BERT + Fuzzy Match Text Correction System

This module provides context-aware text correction for Turkish text using:
- Turkish BERT model (dbmdz/bert-base-turkish-cased) for semantic analysis
- Fuzzy matching with rapidfuzz for similarity-based corrections
- Rule-based post-processing for Turkish-specific patterns

Main function: correct_turkish_text_with_bert(text: str) -> str
"""

import re
import logging
import time
from typing import List, Dict, Tuple, Optional
from functools import lru_cache
import warnings

# Suppress noisy warnings
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=".*resume_download.*")

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForMaskedLM, pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers not available. Install with: pip install transformers torch")

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    # Import numpy separately for fallback functions
    try:
        import numpy as np
    except ImportError:
        np = None

try:
    import nltk
    from nltk.tokenize import sent_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False
    # Silent fallback - no warning needed

# Global model cache
_model_cache = None
_tokenizer_cache = None
_pipeline_cache = None

# Configuration
MODEL_NAME = "dbmdz/bert-base-turkish-cased"
CONFIDENCE_THRESHOLD = 0.85
MAX_SENTENCE_LENGTH = 512
BATCH_SIZE = 8

class TurkishBERTCorrector:
    """Turkish BERT-based text correction system with fuzzy matching."""
    
    def __init__(self):
        self.device = self._get_optimal_device()
        self.model = None
        self.tokenizer = None
        self.fill_mask_pipeline = None
        self._initialize_model()
    
    def _get_optimal_device(self) -> str:
        """Determine optimal device for processing (Apple Silicon GPU, CUDA, or CPU)."""
        if not TRANSFORMERS_AVAILABLE:
            return "cpu"
        
        if torch.backends.mps.is_available():
            return "mps"  # Apple Silicon GPU
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def _initialize_model(self):
        """Initialize and cache BERT model and tokenizer."""
        global _model_cache, _tokenizer_cache, _pipeline_cache
        
        if not TRANSFORMERS_AVAILABLE:
            logging.error("Transformers not available. Cannot initialize BERT model.")
            return
        
        if _model_cache is None or _tokenizer_cache is None:
            try:
                logging.info(f"Loading Turkish BERT model: {MODEL_NAME}")
                start_time = time.time()
                
                # Load tokenizer
                _tokenizer_cache = AutoTokenizer.from_pretrained(MODEL_NAME)
                
                # Load model
                _model_cache = AutoModelForMaskedLM.from_pretrained(MODEL_NAME)
                
                # Move to optimal device
                if self.device != "cpu":
                    _model_cache = _model_cache.to(self.device)
                
                # Create fill-mask pipeline
                _pipeline_cache = pipeline(
                    "fill-mask",
                    model=_model_cache,
                    tokenizer=_tokenizer_cache,
                    device=0 if self.device == "cuda" else -1,
                    top_k=5
                )
                
                load_time = time.time() - start_time
                logging.info(f"Model loaded successfully in {load_time:.2f}s on device: {self.device}")
                
            except Exception as e:
                # Silent fallback - BERT not available, use rule-based only
                return
        
        self.model = _model_cache
        self.tokenizer = _tokenizer_cache
        self.fill_mask_pipeline = _pipeline_cache
    
    def _segment_sentences(self, text: str) -> List[str]:
        """Segment text into sentences using NLTK or rule-based approach."""
        if not text.strip():
            return []
        
        if NLTK_AVAILABLE:
            try:
                # Try to download Turkish punkt tokenizer if not available
                try:
                    sentences = sent_tokenize(text, language='turkish')
                except LookupError:
                    # Fallback to English if Turkish not available
                    sentences = sent_tokenize(text)
                return [s.strip() for s in sentences if s.strip()]
            except Exception as e:
                logging.warning(f"NLTK sentence tokenization failed: {e}")
        
        # Fallback: rule-based sentence segmentation
        sentences = re.split(r'[.!?]+\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _identify_problem_areas(self, sentence: str) -> List[Tuple[str, int, int]]:
        """Identify potential problem areas in text that need correction."""
        problems = []
        
        # Pattern 1: Word splits (space in middle of words)
        # "day alı" -> should be "dayalı"
        split_word_pattern = r'\b(\w{2,})\s+(\w{1,3})\b'
        for match in re.finditer(split_word_pattern, sentence):
            full_match = match.group(0)
            problems.append((full_match, match.start(), match.end()))
        
        # Pattern 2: Affix separation
        # "amacı nı" -> should be "amacını"
        affix_pattern = r'\b(\w+)\s+(n[ıiıuüa]|[ıiıuüa]n|d[aeiıuüo]|t[aeiıuüo]|[lnr][aeiıuüo])\b'
        for match in re.finditer(affix_pattern, sentence):
            full_match = match.group(0)
            problems.append((full_match, match.start(), match.end()))
        
        # Pattern 3: Punctuation spacing issues
        # "tahvil , repo" -> should be "tahvil, repo"
        punct_pattern = r'\s+([,.;:!?])\s*'
        for match in re.finditer(punct_pattern, sentence):
            full_match = match.group(0)
            problems.append((full_match, match.start(), match.end()))
        
        return problems
    
    def _get_bert_suggestions(self, sentence: str, problem_area: str) -> List[Tuple[str, float]]:
        """Get BERT-based suggestions for problematic text segments."""
        if not self.fill_mask_pipeline:
            return []
        
        try:
            # Create masked version of the sentence
            masked_sentence = sentence.replace(problem_area, self.tokenizer.mask_token)
            
            # Ensure sentence isn't too long
            if len(self.tokenizer.encode(masked_sentence)) > MAX_SENTENCE_LENGTH:
                return []
            
            # Get BERT predictions
            predictions = self.fill_mask_pipeline(masked_sentence)
            
            # Format results
            suggestions = []
            for pred in predictions:
                token_str = pred['token_str']
                score = pred['score']
                if score >= CONFIDENCE_THRESHOLD * 0.5:  # Lower threshold for initial filtering
                    suggestions.append((token_str, score))
            
            return suggestions
            
        except Exception as e:
            logging.warning(f"BERT suggestion failed for '{problem_area}': {e}")
            return []
    
    def _apply_semantic_correction(self, original_segment: str, bert_suggestions: List[Tuple[str, float]]) -> Tuple[str, float]:
        """Apply semantic similarity to validate and refine BERT suggestions."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE or not bert_suggestions:
            return original_segment, 0.0
        
        matcher = get_semantic_matcher()
        if not matcher.model:
            return original_segment, 0.0
        
        best_correction = original_segment
        best_confidence = 0.0
        
        # Create candidate corrections by combining original with BERT suggestions
        candidates = []
        
        # Direct BERT suggestions
        for suggestion, bert_score in bert_suggestions:
            candidates.append((suggestion, bert_score))
        
        # For word splits, try combining the parts
        if ' ' in original_segment:
            parts = original_segment.split()
            if len(parts) == 2:
                combined = ''.join(parts)
                candidates.append((combined, 0.7))
        
        # For affix separation, try combining
        affix_match = re.match(r'(\w+)\s+(n[ıiıuüa]|[ıiıuüa]n|d[aeiıuüo]|t[aeiıuüo]|[lnr][aeiıuüo])', original_segment)
        if affix_match:
            root = affix_match.group(1)
            affix = affix_match.group(2)
            combined = root + affix
            candidates.append((combined, 0.8))
        
        # Evaluate candidates using semantic similarity
        for candidate, base_score in candidates:
            # Calculate semantic similarity with original
            similarity = matcher.get_similarity(original_segment, candidate)
            
            # Combined confidence score
            combined_confidence = (base_score + similarity) / 2.0
            
            if combined_confidence > best_confidence and combined_confidence >= CONFIDENCE_THRESHOLD * 0.6:
                best_correction = candidate
                best_confidence = combined_confidence
        
        return best_correction, best_confidence
    
    def _apply_turkish_rules(self, text: str) -> str:
        """Apply Turkish-specific rule-based corrections."""
        corrected = text
        
        # Rule 1: Fix punctuation spacing
        # "word , word" -> "word, word"
        corrected = re.sub(r'\s+([,.;:!?])\s*', r'\1 ', corrected)
        
        # Rule 2: Fix Turkish word splits - Common PDF parsing errors
        turkish_word_fixes = {
            # Suffix separations - most common PDF parsing errors
            r'\b(\w+ı)\s+(nı|nın|ğı|ğın|k)\b': r'\1\2',  # amacı nı -> amacını, okuryazarlı k -> okuryazarlık
            r'\b(\w+i)\s+(ni|nin|ği|ğin|k)\b': r'\1\2',  # ilkeleri ni -> ilkelerini
            r'\b(\w+u)\s+(nu|nun|ğu|ğun|k)\b': r'\1\2',  # sorusu nun -> sorusunun
            r'\b(\w+ü)\s+(nü|nün|ğü|ğün|k)\b': r'\1\2',  # 
            r'\b(\w+a)\s+(na|nın|ğa|ğın|k)\b': r'\1\2',  # 
            r'\b(\w+e)\s+(ne|nin|ğe|ğin|k)\b': r'\1\2',  # 
            
            # Common word fragments
            r'\bv\s+e\b': 've',                          # v e -> ve
            r'\ba\s+çıklar\b': 'açıklar',               # a çıklar -> açıklar
            r'\bkon\s+ulan\b': 'konulan',               # kon ulan -> konulan
            
            # Compound word separations
            r'\b(\w+ları)\s+(ndan|nden)\b': r'\1\2',    # kaynakları ndan -> kaynaklarından
            r'\b(\w+lar)\s+(ı|i|ü|u)\b': r'\1\2',      # uygulama lar -> uygulamalar (context dependent)
            
            # Hyphen spacing fixes
            r'\s+-\s*': '-',                            # Tasarruf -yatırım -> Tasarruf-yatırım
            r'-\s+': '-',                               # word- other -> word-other
        }
        
        for pattern, replacement in turkish_word_fixes.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        # Rule 3: Fix double spaces (after word combination)
        corrected = re.sub(r'\s+', ' ', corrected)
        
        # Rule 4: Fix common Turkish word patterns
        common_fixes = {
            r'\bda ki\b': 'daki',
            r'\bde ki\b': 'deki', 
            r'\bta ki\b': 'taki',
            r'\bte ki\b': 'teki',
            r'\bila ki\b': 'bilaki',
        }
        
        for pattern, replacement in common_fixes.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        # Rule 5: Fix specific problematic words from PDF (case-insensitive)
        specific_fixes = {
            r'\bFinansa\b': 'Finansal',                 # Incomplete word fragment
            r'\buygulama\s+lar\b': 'uygulamalar',       # Specific compound word fix
        }
        
        for pattern, replacement in specific_fixes.items():
            corrected = re.sub(pattern, replacement, corrected, flags=re.IGNORECASE)
        
        # Rule 6: Strip and normalize whitespace
        corrected = corrected.strip()
        
        return corrected
    
    def _process_sentence_batch(self, sentences: List[str]) -> List[str]:
        """Process a batch of sentences for efficient correction."""
        corrected_sentences = []
        
        for sentence in sentences:
            try:
                corrected = self._correct_single_sentence(sentence)
                corrected_sentences.append(corrected)
            except Exception as e:
                logging.warning(f"Failed to correct sentence: {e}")
                corrected_sentences.append(sentence)  # Return original on error
        
        return corrected_sentences
    
    def _correct_single_sentence(self, sentence: str) -> str:
        """Correct a single sentence using BERT + fuzzy matching."""
        if not sentence.strip():
            return sentence
        
        # Identify problem areas
        problems = self._identify_problem_areas(sentence)
        
        if not problems:
            # Apply basic Turkish rules even if no problems detected
            return self._apply_turkish_rules(sentence)
        
        corrected = sentence
        offset = 0  # Track position changes due to corrections
        
        # Process each problem area
        for problem_text, start_pos, end_pos in problems:
            # Adjust positions based on previous corrections
            adjusted_start = start_pos + offset
            adjusted_end = end_pos + offset
            
            # Get BERT suggestions
            bert_suggestions = self._get_bert_suggestions(corrected, problem_text)
            
            # Apply semantic correction
            correction, confidence = self._apply_semantic_correction(problem_text, bert_suggestions)
            
            # Apply correction if confidence is high enough
            if confidence >= CONFIDENCE_THRESHOLD * 0.7 and correction != problem_text:
                # Replace in the corrected text
                before = corrected[:adjusted_start]
                after = corrected[adjusted_end:]
                corrected = before + correction + after
                
                # Update offset for next corrections
                offset += len(correction) - len(problem_text)
        
        # Apply final Turkish rules
        corrected = self._apply_turkish_rules(corrected)
        
        return corrected
    
    def correct_text(self, text: str) -> str:
        """Main function to correct Turkish text using BERT + semantic similarity."""
        if not text or not text.strip():
            return text
        
        start_time = time.time()
        
        try:
            # Segment into sentences
            sentences = self._segment_sentences(text)
            
            if not sentences:
                return self._apply_turkish_rules(text)
            
            # Process sentences in batches
            corrected_sentences = []
            for i in range(0, len(sentences), BATCH_SIZE):
                batch = sentences[i:i + BATCH_SIZE]
                corrected_batch = self._process_sentence_batch(batch)
                corrected_sentences.extend(corrected_batch)
            
            # Reconstruct text
            corrected_text = ' '.join(corrected_sentences)
            
            processing_time = time.time() - start_time
            logging.info(f"Text correction completed in {processing_time:.3f}s")
            
            return corrected_text
            
        except Exception as e:
            logging.error(f"Text correction failed: {e}")
            # Return original text with basic rules applied
            return self._apply_turkish_rules(text)


class SemanticMatcher:
    """Pure semantic similarity matching using sentence transformers."""
    
    def __init__(self):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            self.model = None
            return
        
        try:
            # Load lightweight multilingual model optimized for speed
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_cache = {}  # Cache for performance
        except Exception as e:
            self.model = None
    
    def _get_embedding(self, text: str):
        """Get cached embedding for text."""
        if not self.model or np is None:
            return None
        
        # Normalize text for caching
        normalized_text = text.strip().lower()
        
        if normalized_text not in self.embedding_cache:
            try:
                embedding = self.model.encode(normalized_text)
                self.embedding_cache[normalized_text] = embedding
            except Exception:
                return None
        
        return self.embedding_cache[normalized_text]
    
    def get_similarity(self, text1: str, text2: str) -> float:
        """Get semantic similarity between two texts."""
        if not self.model or np is None:
            return 0.0
        
        embedding1 = self._get_embedding(text1)
        embedding2 = self._get_embedding(text2)
        
        if embedding1 is None or embedding2 is None:
            return 0.0
        
        try:
            similarity = cosine_similarity([embedding1], [embedding2])[0][0]
            return float(similarity)
        except Exception:
            return 0.0
    
    def find_best_match(self, query: str, candidates: list, threshold: float = 0.75) -> tuple:
        """
        Find best semantic match for query in candidates.
        
        Args:
            query (str): Text to find matches for
            candidates (list): List of candidate texts
            threshold (float): Minimum similarity threshold (0.75 default)
            
        Returns:
            tuple: (best_match, similarity_score) or (None, 0.0) if no match
        """
        if not self.model or not candidates or np is None:
            return None, 0.0
        
        best_match = None
        best_score = 0.0
        
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return None, 0.0
        
        for candidate in candidates:
            candidate_embedding = self._get_embedding(candidate)
            if candidate_embedding is None:
                continue
            
            try:
                similarity = cosine_similarity([query_embedding], [candidate_embedding])[0][0]
                if similarity > best_score and similarity >= threshold:
                    best_score = similarity
                    best_match = candidate
            except Exception:
                continue
        
        return best_match, best_score
    
    def batch_similarity(self, query: str, candidates: list) -> list:
        """Get similarity scores for query against all candidates (batch processing)."""
        if not self.model or not candidates or np is None:
            return []
        
        try:
            # Batch encode all texts for efficiency
            all_texts = [query] + candidates
            embeddings = self.model.encode(all_texts)
            
            # Calculate similarities
            query_embedding = embeddings[0:1]
            candidate_embeddings = embeddings[1:]
            
            similarities = cosine_similarity(query_embedding, candidate_embeddings)[0]
            return [(candidates[i], float(similarities[i])) for i in range(len(candidates))]
        except Exception:
            return []


# Global instances
_corrector_instance = None
_semantic_matcher_instance = None

def get_corrector() -> TurkishBERTCorrector:
    """Get or create global corrector instance."""
    global _corrector_instance
    if _corrector_instance is None:
        _corrector_instance = TurkishBERTCorrector()
    return _corrector_instance

def get_semantic_matcher() -> SemanticMatcher:
    """Get or create global semantic matcher instance."""
    global _semantic_matcher_instance
    if _semantic_matcher_instance is None:
        _semantic_matcher_instance = SemanticMatcher()
    return _semantic_matcher_instance

def correct_turkish_text_with_bert(text: str) -> str:
    """
    Main function to correct Turkish text using BERT + semantic similarity.
    
    This function combines:
    - Turkish BERT model for context-aware suggestions
    - Semantic similarity for validation and refinement
    - Rule-based post-processing for Turkish-specific patterns
    
    Args:
        text (str): Input Turkish text to correct
        
    Returns:
        str: Corrected Turkish text
        
    Example:
        >>> correct_turkish_text_with_bert("day alı amacı nı tahvil , repo")
        "dayalı amacını tahvil, repo"
    """
    if not TRANSFORMERS_AVAILABLE:
        logging.warning("BERT correction not available. Applying basic rules only.")
        # Fallback to basic rule-based correction
        corrector = TurkishBERTCorrector()
        return corrector._apply_turkish_rules(text)
    
    corrector = get_corrector()
    return corrector.correct_text(text)

def semantic_find(query: str, content: str, threshold: float = 0.75) -> int:
    """
    Find semantic match position in content using BERT embeddings.
    
    This replaces the old fuzzy_find function with pure semantic similarity.
    
    Args:
        query (str): Text to search for
        content (str): Content to search in
        threshold (float): Minimum similarity threshold (0.75 default)
        
    Returns:
        int: Position of best match in content, or -1 if no match found
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        # Fallback to simple string search if semantic matching unavailable
        query_normalized = query.strip().upper()
        content_normalized = content.strip().upper()
        return content_normalized.find(query_normalized)
    
    matcher = get_semantic_matcher()
    if not matcher.model:
        # Fallback to simple string search
        query_normalized = query.strip().upper()
        content_normalized = content.strip().upper()
        return content_normalized.find(query_normalized)
    
    # Extract potential candidates from content (simple word-based chunking)
    words = content.split()
    query_words = query.split()
    query_length = len(query_words)
    
    if query_length == 0:
        return -1
    
    candidates = []
    positions = []
    
    # Create sliding window of candidates
    for i in range(len(words) - query_length + 1):
        candidate = ' '.join(words[i:i + query_length])
        candidates.append(candidate)
        # Calculate approximate position in original content
        position = content.find(candidate)
        positions.append(position)
    
    if not candidates:
        return -1
    
    # Find best semantic match
    best_match, best_score = matcher.find_best_match(query, candidates, threshold)
    
    if best_match:
        # Find position of best match in content
        for i, candidate in enumerate(candidates):
            if candidate == best_match:
                return positions[i]
    
    return -1

# Utility functions for testing and debugging
def test_correction_examples():
    """Test the correction system with example problems."""
    examples = [
        "day alı amacı nı",
        "tahvil , repo işlemleri",
        "bilgi sa yar sistemleri",
        "öğren me süre ci",
        "Geometrik Motif Çizi mi"
    ]
    
    print("Turkish BERT Text Correction Test Results:")
    print("=" * 50)
    
    for example in examples:
        corrected = correct_turkish_text_with_bert(example)
        print(f"Original:  {example}")
        print(f"Corrected: {corrected}")
        print("-" * 30)

if __name__ == "__main__":
    # Test the system
    test_correction_examples()