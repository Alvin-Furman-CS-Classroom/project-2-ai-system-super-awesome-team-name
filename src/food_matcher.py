"""
Food Name Matcher: Uses word embeddings to find similar food names.

We implement word embeddings via the sentence-transformers library (e.g. SentenceTransformer
with model 'all-MiniLM-L6-v2'). Food names are encoded into dense vectors; similarity is
computed with cosine similarity for efficient nearest-neighbor search. If sentence-transformers
is not installed, the matcher falls back to token-based matching.
"""

import re
from typing import List, Tuple, Optional, Set
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not installed. Install with: pip install sentence-transformers")


class FoodMatcher:
    """
    Food name matching using word embeddings from the sentence-transformers library.
    
    When use_embeddings is True and sentence-transformers is installed, encodes all food
    names with a SentenceTransformer model (word/sentence embeddings) and performs
    nearest-neighbor search via cosine similarity.

    To avoid generic terms (e.g. "sauce") dominating results, we apply a
    lightweight token-based re-ranking that boosts candidates matching the
    query's "core" tokens (e.g. "apple" in "apple sauce"). Otherwise falls
    back to token-based matching.
    """
    
    _TOKEN_RE = re.compile(r"[a-z0-9]+")
    _STOPWORDS: Set[str] = {
        "and",
        "with",
        "on",
        "in",
        "of",
        "for",
        "to",
        "the",
        "a",
        "an",
    }
    # Terms that are common across many foods and can hijack semantic similarity.
    _GENERIC_MODIFIERS: Set[str] = {
        "sauce",
        "sauces",
        "juice",
        "puree",
        "pureed",
        "gravy",
    }
    # When the user queries "... sauce", prefer interpreting it like "... pureed"
    # when core tokens still match (e.g. "apple sauce" -> "apple pureed").
    _PREFERRED_TOKENS_BY_QUERY_TOKEN: dict[str, Set[str]] = {
        "sauce": {"pureed", "puree"},
        "sauces": {"pureed", "puree"},
    }

    @classmethod
    def _tokenize(cls, text: str) -> Set[str]:
        return set(cls._TOKEN_RE.findall((text or "").lower()))

    @classmethod
    def _extract_core_and_preferred_tokens(
        cls, query_lower: str
    ) -> tuple[Set[str], Set[str]]:
        tokens = cls._tokenize(query_lower) - cls._STOPWORDS
        # "Core" = tokens excluding generic modifiers (so "sauce" can't win alone).
        core_tokens = {t for t in tokens if t not in cls._GENERIC_MODIFIERS}

        preferred_tokens: Set[str] = set()
        if core_tokens:
            for t in tokens:
                preferred_tokens |= cls._PREFERRED_TOKENS_BY_QUERY_TOKEN.get(t, set())

        return core_tokens, preferred_tokens

    def __init__(self, food_names: List[str], 
                 model_name: str = "all-MiniLM-L6-v2",
                 use_embeddings: bool = True):
        """Initialize food matcher.
        
        Args:
            food_names: List of all food names in knowledge base.
            model_name: sentence-transformers model name for word embeddings.
                        Default: "all-MiniLM-L6-v2" (~80MB).
            use_embeddings: If True, use sentence-transformers for word embeddings; if False
                           or library missing, fall back to simple substring matching.
        
        Raises:
            ImportError: If sentence-transformers not installed and use_embeddings=True.
        """
        self.food_names = food_names
        self.use_embeddings = use_embeddings and SENTENCE_TRANSFORMERS_AVAILABLE

        # Precompute token sets for token-based re-ranking / fallback scoring.
        self._food_token_sets: List[Set[str]] = [self._tokenize(name) for name in food_names]
        
        if self.use_embeddings:
            print(f"Loading embedding model: {model_name}...")
            self.model = SentenceTransformer(model_name)
            print("Pre-computing food name embeddings...")
            # Pre-compute embeddings for all foods
            self.food_embeddings = self.model.encode(
                food_names,
                show_progress_bar=False,
                convert_to_numpy=True,
                batch_size=32
            )
            # Normalize for fast cosine similarity
            self._normalized_embeddings = (
                self.food_embeddings / np.linalg.norm(self.food_embeddings, axis=1, keepdims=True)
            )
            print(f"Embeddings computed for {len(food_names)} foods.")
        else:
            self.model = None
            self.food_embeddings = None
            if use_embeddings:
                print("Warning: Falling back to token-based matching.")
    
    def find_nearest_neighbors(self, query: str, top_k: int = 5, 
                              offset: int = 0) -> List[Tuple[str, float]]:
        """Find nearest neighbors using word-embedding (sentence-transformers) similarity.
        
        Args:
            query: User's food name query.
            top_k: Number of results to return.
            offset: Skip first N results (for "next 5" functionality).
        
        Returns:
            List of (food_name, score) tuples, sorted by best score first.
            When embeddings are enabled, `score` is an adjusted cosine similarity
            that is re-ranked using query "core" tokens (so generic terms like
            "sauce" don't dominate results).
        """
        query_lower = query.lower().strip()
        core_tokens, preferred_tokens = self._extract_core_and_preferred_tokens(query_lower)
        core_len = len(core_tokens)
        preferred_len = len(preferred_tokens)
        
        if self.use_embeddings:
            # Narrow types for static checkers: self.model is only set when embeddings are enabled.
            assert self.model is not None
            # Encode query
            query_embedding = self.model.encode([query_lower], convert_to_numpy=True)[0]
            query_normalized = query_embedding / np.linalg.norm(query_embedding)
            
            # Compute cosine similarity (fast vectorized operation)
            similarities = np.dot(self._normalized_embeddings, query_normalized)

            # Token-based re-ranking:
            # - boost candidates that match query core tokens
            # - optionally prefer interpreting generic modifiers (e.g. sauce -> pureed)
            CORE_SCORE_WEIGHT = 1.5
            PREFERRED_SCORE_WEIGHT = 0.5
            CORE_MISS_PENALTY = 0.75

            adjusted_scores = similarities.astype(np.float32, copy=True)
            if core_len > 0:
                for i, token_set in enumerate(self._food_token_sets):
                    core_hit_count = len(core_tokens.intersection(token_set))
                    core_score = core_hit_count / core_len
                    preferred_score = (
                        len(token_set.intersection(preferred_tokens)) / preferred_len
                        if preferred_len > 0
                        else 0.0
                    )
                    penalty = CORE_MISS_PENALTY if core_hit_count == 0 else 0.0
                    adjusted_scores[i] = (
                        adjusted_scores[i]
                        + (CORE_SCORE_WEIGHT * core_score)
                        + (PREFERRED_SCORE_WEIGHT * preferred_score)
                        - penalty
                    )
            
            # Get top-k results (using argpartition for efficiency)
            total_results = min(top_k + offset, len(self.food_names))
            top_indices = np.argpartition(adjusted_scores, -total_results)[-total_results:]
            top_indices = top_indices[np.argsort(adjusted_scores[top_indices])[::-1]]
            
            # Apply offset and limit to top_k
            result_indices = top_indices[offset:offset + top_k]
            
            results = [
                (self.food_names[i], float(adjusted_scores[i]))
                for i in result_indices
            ]
            
            return results
        else:
            # Fallback: token-based matching (same core/preferred idea).
            CORE_SCORE_WEIGHT = 1.5
            PREFERRED_SCORE_WEIGHT = 0.5

            matches: List[Tuple[str, float]] = []
            for food, token_set in zip(self.food_names, self._food_token_sets):
                if core_len > 0:
                    core_hit_count = len(core_tokens.intersection(token_set))
                    if core_hit_count == 0:
                        continue  # Anchor matching: generic terms shouldn't return unrelated foods.
                    core_score = core_hit_count / core_len
                else:
                    core_score = 0.0

                preferred_score = (
                    len(token_set.intersection(preferred_tokens)) / preferred_len
                    if preferred_len > 0
                    else 0.0
                )

                score = (CORE_SCORE_WEIGHT * core_score) + (PREFERRED_SCORE_WEIGHT * preferred_score)
                matches.append((food, float(score)))

            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[offset:offset + top_k]
