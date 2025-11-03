import os
import re
import json
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any
import numpy as np
import httpx
import chromadb
from resources.config import config
import tiktoken

# -------------------------------
# Sync embedding function
# -------------------------------
def get_embedding(text: str) -> List[float]:
    """Get embedding for a single text using Ollama"""
    url = f"{config.EMBEDDING_BASE_URL}/api/embeddings"
    payload = {"model": config.EMBEDDING_MODEL, "prompt": text, "options": {
                "num_ctx": 8192}}
    try:
        # Using httpx for consistency, but sync
        with httpx.Client(timeout=60) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()["embedding"]
    except Exception as e:
        logging.error(f"Error getting embedding: {e}, text: {text}")
        return [0.0] * 768  # fallback

# -------------------------------
# Async embedding function
# -------------------------------
_embedding_client: httpx.AsyncClient = None
 
def get_embedding_client():
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = httpx.AsyncClient(timeout=60)
    return _embedding_client
 
async def get_embedding_async(text: str) -> List[float]:
    """Get embedding asynchronously using Ollama"""
    url = f"{config.EMBEDDING_BASE_URL}/api/embeddings"
    payload = {"model": config.EMBEDDING_MODEL, "prompt": text}
    client = get_embedding_client()
    try:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json().get("embedding", [0.0] * 768)
    except Exception as e:
        logging.error(f"Error getting async embedding: {e}")
        return [0.0] * 768
 
# -------------------------------
# Markdown Chunker
# -------------------------------
class MarkdownChunker:
    def __init__(self, file_name:str = "default", output_dir: str = config.OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(
            name=f"markdown_chunks_{file_name}",
            metadata={"hnsw:space": "cosine"}
        )
        self.chunks: List[Dict[str, Any]] = []
 
    def count_tokens(self, text: str) -> int:
        enc = tiktoken.get_encoding(config.DEFAULT_ENCODING)
        return len(enc.encode(text))
    def split_text_by_tokens(self, text: str, max_tokens: int) -> list[str]:
        """Split long text into smaller text chunks without losing words."""
        enc = tiktoken.get_encoding(config.DEFAULT_ENCODING)
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return [text]

        sub_texts = []
        for i in range(0, len(tokens), max_tokens):
            sub_text = enc.decode(tokens[i:i + max_tokens])
            sub_texts.append(sub_text.strip())
        return sub_texts
    def extract_chunks_from_markdown(self, md_content: str) -> List[Dict[str, Any]]:
        chunks = []
        page_pattern = r"\{(\d+)\}-+"
        pages = re.split(page_pattern, md_content, flags=re.MULTILINE)
        if len(pages) <= 1:
            pages = re.split(r'\n\n\n+', md_content)
        if len(pages) <= 1:
            chunk_size = config.CHUNK_SIZE
            pages = [md_content[i:i+chunk_size] for i in range(0, len(md_content), chunk_size)]
        for page_idx, page_content in enumerate(pages):
            if not page_content.strip():
                continue
            table_pattern = r'(\|.*\|(?:\n\|.*\|)*)'
            tables = re.findall(table_pattern, page_content, re.MULTILINE)
            text_content = re.sub(table_pattern, '', page_content, flags=re.MULTILINE)
            text_content = re.sub(r'\n\s*\n', '\n\n', text_content).strip()
            if text_content and len(text_content.strip()) > 50:
                text_chunks = self.split_text_by_tokens(text_content, config.MAX_TOKENS)
                for sub_text in text_chunks:
                    chunks.append({
                        'chunk_id': len(chunks),
                        'page': (page_idx + 1) // 2,
                        'type': 'text',
                        'content': sub_text,
                        #'tokens': count_tokens(sub_text),
                        'length': len(sub_text)
                    })
            for table_idx, table in enumerate(tables):
                if len(table.strip()) > 20:
                    table_chunks = self.split_text_by_tokens(table, config.MAX_TOKENS)
                    for sub_table in table_chunks:
                        chunks.append({
                            'chunk_id': len(chunks),
                            'page': (page_idx + 1) // 2,
                            'type': 'table',
                            'table_index': table_idx + 1,
                            'content': sub_table,
                            #'tokens': count_tokens(sub_table),
                            'length': len(sub_table)
                        })
        return chunks
 
    def clean_marker_md(self, raw_text: str, remove_images: bool = False) -> str:
        text = raw_text.replace("\\n", "")
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'<IR>', '', text)
        text = re.sub(r'(#+)\s*\*\*(.*?)\*\*', r'\1 \2', text)
        if remove_images:
            text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def create_embeddings_and_index(self, md_file_path: str):
        logging.info(f"Processing: {md_file_path}")
        with open(md_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        md_content = self.clean_marker_md(md_content)
        
        chunks = self.extract_chunks_from_markdown(md_content)
        logging.info(f"Extracted {len(chunks)} chunks")
        
        embeddings = [get_embedding(c['content']) for c in chunks]
        embeddings = np.array(embeddings)
        
        self.save_embeddings(embeddings, chunks, md_file_path)
        self.store_in_chromadb(chunks, embeddings)
        
        self.chunks = chunks
        return chunks, embeddings
 
    async def create_embeddings_and_index_async(self, md_file_path: str):
        logging.info(f"Processing async: {md_file_path}")
        with open(md_file_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        md_content = self.clean_marker_md(md_content)
        
        chunks = self.extract_chunks_from_markdown(md_content)
        logging.info(f"Extracted {len(chunks)} chunks")
 
        all_embeddings = []
        for i in range(0, len(chunks), config.BATCH_SIZE):
            batch = chunks[i:i + config.BATCH_SIZE]
            batch_embeddings = await asyncio.gather(*(get_embedding_async(c['content']) for c in batch))
            all_embeddings.extend(batch_embeddings)

        embeddings= np.array(all_embeddings)
        #embeddings = np.array(embeddings)
 
        self.save_embeddings(embeddings, chunks, md_file_path)
        self.store_in_chromadb(chunks, embeddings)
        
        self.chunks = chunks
        return chunks, embeddings
 
    def save_embeddings(self, embeddings: np.ndarray, chunks: List[Dict], source_file: str):
        embed_file = os.path.join(self.output_dir, "embeddings.npy")
        np.save(embed_file, embeddings)
        metadata = {
            "source_file": source_file,
            "created_at": datetime.now().isoformat(),
            "total_chunks": len(chunks),
            "text_chunks": len([c for c in chunks if c['type'] == 'text']),
            "table_chunks": len([c for c in chunks if c['type'] == 'table']),
            "embedding_model": config.EMBEDDING_MODEL,
            "embedding_dimension": embeddings.shape[1] if embeddings.size > 0 else 0,
            "chunks": []
        }
        for i, chunk in enumerate(chunks):
            chunk_meta = {
                "chunk_id": chunk['chunk_id'],
                "page": chunk['page'],
                "type": chunk['type'],
                "length": chunk['length'],
                "preview": chunk['content'][:200] + "..." if len(chunk['content']) > 200 else chunk['content'],
                "full_content": chunk['content'],
                "embedding_index": i
            }
            if chunk['type'] == 'table':
                chunk_meta['table_index'] = chunk.get('table_index', 1)
            metadata["chunks"].append(chunk_meta)
        meta_file = os.path.join(self.output_dir, "chunks_metadata.json")
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
 
    def store_in_chromadb(self, chunks: List[Dict], embeddings: np.ndarray):
        ids = [f"chunk_{c['chunk_id']}" for c in chunks]
        documents = [c['content'] for c in chunks]
        metadatas = [
            {"page": c['page'], "type": c['type'], "length": c['length'], "table_index": c.get('table_index', 0)}
            for c in chunks
        ]
        try:
            self.collection.delete(where={})
        except:
            pass
        self.collection.add(
            embeddings=embeddings.tolist(),
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
 
    async def search_async(self, query: str, n_results: int = 5, filter_type: str = None):
        query_embedding = await get_embedding_async(query)
        where_clause = {"type": filter_type} if filter_type else None
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_clause
        )
        return results
 
async def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    md_file = f"{config.OUTPUT_DIR}/Gamuda.md"
    processor = MarkdownChunker(output_dir=config.OUTPUT_DIR)
    chunks, embeddings = await processor.create_embeddings_and_index_async(md_file)
    results = await processor.search_async("financial data", n_results=3)
    logging.info(results)
 
if __name__ == "__main__":
    asyncio.run(main())
