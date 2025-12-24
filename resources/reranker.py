"""
Cross-Encoder Re-ranking Module
================================

🎯 WHAT IS THIS?
----------------
Think of search like finding a restaurant:
1. STEP 1 (Bi-Encoder/Embeddings): Google Maps shows you 20 restaurants nearby
   - Fast but rough matching
   
2. STEP 2 (Cross-Encoder): You read reviews of those 20 to pick the best 5
   - Slower but much more accurate

This module does Step 2 - takes the rough matches and re-orders them carefully.

📊 WHY IS THIS BETTER?
---------------------
- Bi-Encoder: Compares query & document SEPARATELY, then matches
- Cross-Encoder: Looks at query AND document TOGETHER (like reading both side by side)

The Cross-Encoder sees: "Does THIS specific query match THIS specific document?"
Much smarter than just "do their embeddings look similar?"
"""

import logging
from typing import List, Tuple
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class ReRanker:
    """
    Re-ranks retrieved documents using a Cross-Encoder model.
    
    Simple Usage:
    -------------
    reranker = ReRanker()
    
    # You have 10 documents from ChromaDB
    documents = ["doc1 text", "doc2 text", ...]
    
    # Get the best 3, properly ranked
    best_docs = reranker.rerank("What is the revenue?", documents, top_k=3)
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize the re-ranker.
        
        Model Options (from fastest to most accurate):
        - "cross-encoder/ms-marco-TinyBERT-L-2-v2"  # Fastest, OK accuracy
        - "cross-encoder/ms-marco-MiniLM-L-6-v2"   # Good balance ✓ DEFAULT
        - "cross-encoder/ms-marco-MiniLM-L-12-v2"  # Better accuracy, slower
        
        For financial documents, the default is usually good enough.
        """
        logger.info(f"Loading Cross-Encoder model: {model_name}")
        self.model = CrossEncoder(model_name)
        self.model_name = model_name
        logger.info("Cross-Encoder loaded successfully")
    
    def rerank(
        self, 
        query: str, 
        documents: List[str], 
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Re-rank documents by relevance to the query.
        
        Args:
            query: The search question (e.g., "What is the debt ratio?")
            documents: List of text chunks from ChromaDB
            top_k: How many best documents to return
            
        Returns:
            List of (document_text, relevance_score) tuples, best first
            
        Example:
            >>> reranker.rerank("revenue growth", ["doc about revenue", "doc about employees"], top_k=1)
            [("doc about revenue", 0.92)]
        """
        if not documents:
            return []
        
        # Create pairs of (query, document) for the model to score
        # The model will look at each pair and say "how relevant is this document to this query?"
        pairs = [[query, doc] for doc in documents]
        
        # Get relevance scores (higher = more relevant)
        scores = self.model.predict(pairs)
        
        # Combine documents with their scores
        doc_score_pairs = list(zip(documents, scores))
        
        # Sort by score (highest first) and take top_k
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Re-ranked {len(documents)} documents, returning top {top_k}")
        
        return doc_score_pairs[:top_k]
    
    def rerank_with_metadata(
        self,
        query: str,
        docs_with_meta: List[Tuple[str, dict]],
        top_k: int = 5
    ) -> List[Tuple[str, dict, float]]:
        """
        Re-rank while preserving metadata (page numbers, types, etc.)
        
        This is useful when you need to know WHERE the best info came from.
        
        Args:
            query: Search question
            docs_with_meta: List of (document_text, metadata_dict) from ChromaDB
            top_k: How many to return
            
        Returns:
            List of (document_text, metadata, score) tuples
        """
        if not docs_with_meta:
            return []
        
        documents = [doc for doc, _ in docs_with_meta]
        metadatas = [meta for _, meta in docs_with_meta]
        
        pairs = [[query, doc] for doc in documents]
        scores = self.model.predict(pairs)
        
        # Combine all three: doc, metadata, score
        combined = list(zip(documents, metadatas, scores))
        combined.sort(key=lambda x: x[2], reverse=True)
        
        return combined[:top_k]


# Singleton instance for reuse (loading model is slow, do it once)
_reranker_instance = None

def get_reranker() -> ReRanker:
    """Get or create the global re-ranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = ReRanker()
    return _reranker_instance
