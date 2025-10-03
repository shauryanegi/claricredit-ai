import chromadb
from typing import List
from resources.embeddings import get_embedding
from resources.llm_adapter import LocalLLMAdapter
from resources.config.system_prompt import SYSTEM_PROMPT

class RAGPipelineCosine:
    def __init__(self, chroma_path: str, collection_name: str,
                 llm_endpoint: str, llm_model: str):
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        self.collection = self.chroma_client.get_or_create_collection(collection_name)
        self.llm = LocalLLMAdapter(endpoint=llm_endpoint, model=llm_model)

    def retrieve(self, query: str, n_results: int = 5):
        query_emb = get_embedding(query)
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
            {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}\n\nAnswer:"}
        ]
        return self.llm.chat(messages, max_tokens=512)

    def run(self, group) -> str:
        user_query=group["user_query"]
        semantic_queries=group["semantic_queries"]
        all_docs=[]
        seen = set()
        for dictionary in semantic_queries:
            query=dictionary["query"]
            n_results=dictionary["k"]
            docs_with_meta = self.retrieve(query, n_results=n_results)
            for doc, meta in docs_with_meta:
                # print(meta) 
                key=(meta['page'],meta['length'])
                if key not in seen:   # deduplicate based on page
                    seen.add(key)
                    all_docs.append(doc)  
                else:
                    print(f"{key} repeated")

        # print("\n=== Retrieved Docs Preview ===")
        # for d in all_docs:
        #     print(d[:300].replace("\n", " ") + " ...")
        return self.generate_answer(user_query, all_docs)
