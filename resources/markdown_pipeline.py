import os
import yaml
import argparse
from datetime import datetime
from resources.config import config
from resources import chunker
from resources.rag import RAGPipelineCosine
from resources.retrieval_queries.sections import CREDIT_MEMO_SECTIONS
from resources.split_md_by_page import split_md_by_page
import time

def load_prompts(file_path: str) -> dict:
    """Load YAML prompts as a dictionary of {section: prompt_text}."""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def run_pipeline(md_file: str, n_results: int = 5, query: str = None):
    start = time.time()
    print(f"[INFO] Starting pipeline with Markdown file: {md_file}")

    # Step 1: Chunk + embeddings
    file_name=os.path.basename(md_file).replace(".md","")
    processor = chunker.MarkdownChunker(file_name,output_dir=config.OUTPUT_DIR)
    chunks, embeddings = processor.create_embeddings_and_index(md_file)
    print(f"[INFO] Processed {len(chunks)} chunks.")

    # Step 2: Initialize RAG pipeline
    rag = RAGPipelineCosine(
        chroma_path=config.CHROMA_PATH,
        collection_name=f"markdown_chunks_{file_name}",
        llm_endpoint=config.LLM_ENDPOINT,
        llm_model=config.LLM_MODEL,
    )

    results = {}

    if query:
        # Run single ad-hoc query
        print(f"\n[INFO] Running single query: {query}")
        answer = rag.run(query, n_results=n_results)
        results["single_query"] = {"question": query, "answer": answer}
        print(f"\n=== ANSWER ===\n{answer}")
    else:
        split_page_file=split_md_by_page(md_file)
        for section, groups in CREDIT_MEMO_SECTIONS.items():
            section_start = time.time()
            print(f"Making section:{section}")
            section_results = []
            for group in groups:
                answer = rag.run(group,split_page_file)
                section_results.append(answer)
            section_text="\n\n".join(section_results)
            results[section] = section_text
            section_end = time.time()
            print(f"[INFO] Section '{section}' completed in {section_end - section_start:.2f} seconds.")

    # Step 3: Save results with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if query:
        filename = f"single_query_result_{timestamp}.md"
    else:
        filename = f"credit_memo_from_md_{timestamp}.md"

    output_path = os.path.join(config.OUTPUT_DIR, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        for section, ans in results.items():
            f.write(f"## {section.replace('_', ' ').title()}\n\n")
            f.write(f"\n{ans}\n\n")

    print(f"\n[INFO] Results saved to {output_path}")
    end = time.time()
    print(f"[INFO] Pipeline completed in {end - start:.2f} seconds.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Credit Memo from Markdown")
    parser.add_argument("--md", type=str, required=True, help="Path to markdown file")
    parser.add_argument("--n_results", type=int, default=5, help="Number of retrieved docs per query")
    parser.add_argument("--query", type=str, help="Run a single ad-hoc query instead of full memo")
    args = parser.parse_args()

    run_pipeline(md_file=args.md, n_results=args.n_results, query=args.query)
