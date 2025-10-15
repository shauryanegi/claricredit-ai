from fastapi import FastAPI, UploadFile, Form
import os
import yaml
from resources import chunker
from resources.config import config
from resources.rag import RAGPipelineCosine

app = FastAPI(title="Credit Memo RAG App")

# Utility: load prompts from YAML
def load_prompts(file_path: str) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# Global RAG instance (reused across queries)
rag = RAGPipelineCosine(
    chroma_path=config.CHROMA_PATH,
    collection_name="markdown_chunks",
    llm_endpoint=config.LLM_ENDPOINT,
    llm_model=config.LLM_MODEL,
)

@app.post("/index")
async def index_markdown(md_file: UploadFile):
    """Index a markdown file into ChromaDB."""
    file_path = os.path.join(config.OUTPUT_DIR, md_file.filename)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    # Save uploaded file
    with open(file_path, "wb") as f:
        f.write(await md_file.read())

    # Chunk + embed
    processor = chunker.MarkdownChunker(output_dir=config.OUTPUT_DIR)
    chunks, embeddings = processor.create_embeddings_and_index(file_path)

    return {"status": "indexed", "chunks": len(chunks), "file": file_path}

@app.post("/query")
async def query_pipeline(query: str = Form(...), n_results: int = Form(5)):
    """Run a single ad-hoc query against the indexed Markdown."""
    docs_with_meta = rag.retrieve(query, n_results=n_results)
    context_docs = [doc for doc, meta in docs_with_meta]
    answer = rag.generate_answer(query, context_docs)
    return {"query": query, "answer": answer}

@app.post("/memo")
async def generate_credit_memo(n_results: int = Form(5)):
    """Run all credit memo prompts and return results."""
    prompts_file = os.path.join("resources", "prompts", "credit_memo_prompts.yaml")
    prompts = load_prompts(prompts_file)

    results = {}
    for section, prompt in prompts.items():
        docs_with_meta = rag.retrieve(prompt, n_results=n_results)
        context_docs = [doc for doc, meta in docs_with_meta]
        answer = rag.generate_answer(prompt, context_docs)
        results[section] = {"question": prompt, "answer": answer}

    return {"memo": results}
