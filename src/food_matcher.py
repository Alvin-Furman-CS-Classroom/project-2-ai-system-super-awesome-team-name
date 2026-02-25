"""
Food Name Matcher: Uses word embeddings to find similar food names.

We implement word embeddings via the sentence-transformers library (e.g. SentenceTransformer
with model 'all-MiniLM-L6-v2'). Food names are encoded into dense vectors; similarity is
computed with cosine similarity for efficient nearest-neighbor search. If sentence-transformers
is not installed, the matcher falls back to simple substring matching.
"""

from typing import List, Tuple, Optional
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
    nearest-neighbor search via cosine similarity. Otherwise falls back to substring matching.
    """
    
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
                print("Warning: Falling back to simple substring matching.")
    
    def find_nearest_neighbors(self, query: str, top_k: int = 5, 
                              offset: int = 0) -> List[Tuple[str, float]]:
        """Find nearest neighbors using word-embedding (sentence-transformers) similarity.
        
        Args:
            query: User's food name query.
            top_k: Number of results to return.
            offset: Skip first N results (for "next 5" functionality).
        
        Returns:
            List of (food_name, similarity_score) tuples, sorted by similarity descending.
            Similarity scores are between 0 and 1 (cosine similarity).
        """
        query_lower = query.lower().strip()
        
        if self.use_embeddings:
            # Encode query
            query_embedding = self.model.encode([query_lower], convert_to_numpy=True)[0]
            query_normalized = query_embedding / np.linalg.norm(query_embedding)
            
            # Compute cosine similarity (fast vectorized operation)
            similarities = np.dot(self._normalized_embeddings, query_normalized)
            
            # Get top-k results (using argpartition for efficiency)
            total_results = min(top_k + offset, len(self.food_names))
            top_indices = np.argpartition(similarities, -total_results)[-total_results:]
            top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]
            
            # Apply offset and limit to top_k
            result_indices = top_indices[offset:offset + top_k]
            
            results = [
                (self.food_names[i], float(similarities[i]))
                for i in result_indices
            ]
            
            return results
        else:
            # Fallback: simple substring matching
            query_lower = query.lower()
            matches = []
            for food in self.food_names:
                if query_lower in food.lower():
                    # Simple score: length of match / length of food name
                    score = len(query_lower) / len(food.lower())
                    matches.append((food, score))
            
            # Sort by score descending
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[offset:offset + top_k]
