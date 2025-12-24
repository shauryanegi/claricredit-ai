import chromadb
import logging
from typing import List, Optional, Tuple
from resources.embeddings import get_embedding
from resources.llm_adapter import LocalLLMAdapter
from resources.config.system_prompt import SYSTEM_PROMPT,ADDITIONAL_INSTRUCTIONS
from collections import OrderedDict
import json

# Optional: Import reranker (falls back gracefully if not available)
try:
    from resources.reranker import get_reranker
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    logging.warning("Reranker not available. Install sentence-transformers for better retrieval.")

class RAGPipelineCosine:
    """
    RAG Pipeline with optional Cross-Encoder Re-ranking.
    
    🎯 WHAT'S NEW (for interview):
    - retrieve() now has optional `rerank=True` parameter
    - Uses Cross-Encoder to re-order results by true relevance
    - This is the "hybrid retrieval" mentioned in your resume!
    """
    
    def __init__(self, collection_name: str,
                 llm_endpoint: str, llm_model: str,
                 use_reranker: bool = True):
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(collection_name)
        self.llm = LocalLLMAdapter(endpoint=llm_endpoint, model=llm_model)
        self.use_reranker = use_reranker and RERANKER_AVAILABLE
        
        if self.use_reranker:
            logging.info("Cross-Encoder reranker enabled for hybrid retrieval")

    def retrieve(self, query: str, n_results: int = 5, filter=None, 
                 rerank: bool = True, rerank_top_k: Optional[int] = None) -> List[Tuple[str, dict]]:
        """
        Retrieve documents with optional Cross-Encoder re-ranking.
        
        Args:
            query: Search query
            n_results: Number of candidates to retrieve initially
            filter: Optional filter (e.g., type='table')
            rerank: Whether to apply Cross-Encoder re-ranking
            rerank_top_k: How many to keep after reranking (default: n_results)
            
        Returns:
            List of (document, metadata) tuples
            
        How Re-ranking Works:
        1. ChromaDB returns top-N by embedding similarity (fast, rough)
        2. Cross-Encoder scores each (query, doc) pair carefully
        3. Results are re-ordered by Cross-Encoder scores
        
        This is your "hybrid retrieval" for the interview!
        """
        query_emb = get_embedding(query)
        
        # Step 1: Get initial candidates (over-fetch if reranking)
        fetch_count = n_results * 2 if (rerank and self.use_reranker) else n_results
        
        if filter:
            results = self.collection.query(
                query_embeddings=[query_emb],
                n_results=fetch_count,
                where={"type": filter}
            )
        else:
            results = self.collection.query(
                query_embeddings=[query_emb],
                n_results=fetch_count
            )            
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        docs_with_meta = list(zip(docs, metas))
        
        # Step 2: Optional Cross-Encoder re-ranking
        if rerank and self.use_reranker and len(docs_with_meta) > 1:
            reranker = get_reranker()
            top_k = rerank_top_k or n_results
            
            # Re-rank and return top results
            reranked = reranker.rerank_with_metadata(query, docs_with_meta, top_k=top_k)
            docs_with_meta = [(doc, meta) for doc, meta, _ in reranked]
            logging.info(f"Re-ranked {len(docs)} candidates → top {top_k}")
        
        return docs_with_meta

    def generate_answer(self, query: str, context_docs: List[str], fin_data: str) -> str:
        context = "\n\n".join(context_docs)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            # {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}\n\nAnswer:"}
            {"role": "user", "content": f"Context:\n{context}\n{fin_data}\n\n{query}\n{ADDITIONAL_INSTRUCTIONS}"}
        ]
        return self.llm.chat(messages, max_tokens=1024)

    def run(self, group,split_page_file,financial_data) -> str:
        user_query=group["user_query"]
        semantic_queries=group["semantic_queries"]
        full_page=group["full_page"]
        fin_data_needed = group["fin_data_needed"]
        if full_page:
            all_docs=[]
            seen = set()
            for dictionary in semantic_queries:
                query=dictionary["query"]
                n_results=dictionary["k"]
                filter=dictionary.get("filter")
                docs_with_meta = self.retrieve(query, n_results=n_results,filter=filter)
                for doc, meta in docs_with_meta:
                    # logging.debug(meta) 
                    # key=(meta['page'],meta['length'])
                    page=meta['page']
                    logging.info(f"Choosing full page- {page}")
                    if meta["type"]=="loan":
                        all_docs.append(doc)
                        # logging.debug(f"doc={doc}")
                    
                    elif page not in seen:   # deduplicate based on page
                        seen.add(page)
                        # all_docs.append(doc)  
                        with open(split_page_file, "r", encoding="utf-8") as f:
                            full_pages = json.load(f)
                        all_docs.append(full_pages[page-1])
                    # else:
                        # logging.debug(f"Page {page} repeated")
        else:
            retrieved_docs_with_meta = []
            for sem_q in semantic_queries:
                query = sem_q["query"]
                n_results = sem_q["k"]
                filter=sem_q.get("filter")
                docs_with_meta = self.retrieve(query, n_results=n_results,filter=filter)
                retrieved_docs_with_meta.extend(docs_with_meta)

            all_docs = list(OrderedDict.fromkeys([doc for doc, meta in retrieved_docs_with_meta]))
        if fin_data_needed:
            fin_data = financial_data
        else:
            fin_data = ""
        return self.generate_answer(user_query, all_docs, fin_data)
