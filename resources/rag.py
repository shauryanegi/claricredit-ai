import chromadb
import logging
from typing import List
from resources.embeddings import get_embedding
from resources.llm_adapter import LocalLLMAdapter
from resources.config.system_prompt import SYSTEM_PROMPT,ADDITIONAL_INSTRUCTIONS
from collections import OrderedDict
import json

class RAGPipelineCosine:
    def __init__(self, chroma_path: str, collection_name: str,
                 llm_endpoint: str, llm_model: str):
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.chroma_client.get_or_create_collection(collection_name)
        self.llm = LocalLLMAdapter(endpoint=llm_endpoint, model=llm_model)

    def retrieve(self, query: str, n_results: int = 5, filter=None):
        query_emb = get_embedding(query)
        if filter:
            results = self.collection.query(
                query_embeddings=[query_emb],
                n_results=n_results,
                where={"type": filter}
            )
        else:
            results = self.collection.query(
                query_embeddings=[query_emb],
                n_results=n_results
            )            
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        return list(zip(docs, metas))

    def generate_answer(self, query: str, context_docs: List[str]) -> str:
        context = "\n\n".join(context_docs)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            # {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}\n\nAnswer:"}
            {"role": "user", "content": f"Context:\n{context}\n\n{query}\n{ADDITIONAL_INSTRUCTIONS}"}
        ]
        return self.llm.chat(messages, max_tokens=512)

    def run(self, group,split_page_file) -> str:
        user_query=group["user_query"]
        semantic_queries=group["semantic_queries"]
        full_page=group["full_page"]
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

        return self.generate_answer(user_query, all_docs)
