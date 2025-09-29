import os
import yaml
import argparse
from resources.config import config
from resources import extractor, chunker
from resources.rag import RAGPipelineCosine

def load_prompts(file_path: str) -> dict:
    """Load YAML prompts as a dictionary of {section: prompt_text}."""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main(n_results: int = 5):
    print("[INFO] Starting Credit Memo Pipeline...")

    # Step 1: Extract PDF → Markdown
    # Adjust filename as needed; you could also make this an argument.
    pdf_file = os.path.join(config.PDF_DIR, "Gamuda.pdf")
    md_file = extractor.extract_pdf(pdf_file)

    # Step 2: Chunk + embeddings
    processor = chunker.MarkdownChunker(output_dir=config.OUTPUT_DIR)
    chunks, embeddings = processor.create_embeddings_and_index(md_file)
    print(f"[INFO] Processed {len(chunks)} chunks.")

    # Step 3: Initialize RAG pipeline
    rag = RAGPipelineCosine(
        chroma_path=config.CHROMA_PATH,
        collection_name="markdown_chunks",
        llm_endpoint=config.LLM_ENDPOINT,
        llm_model=config.LLM_MODEL
    )

    # Step 4: Load prompts
    prompts_file = os.path.join("resources", "prompts", "credit_memo_prompts.yaml")
    prompts = load_prompts(prompts_file)

    results = {}
    for section, prompt in prompts.items():
        print(f"\n[INFO] Running section: {section}")
        answer = rag.run(prompt, n_results=n_results)
        results[section] = answer
        print(f"\n=== {section.upper()} ===\n{answer}")

    # Step 5: Save results
    output_path = os.path.join(config.OUTPUT_DIR, "credit_memo.md")
    with open(output_path, "w", encoding="utf-8") as f:
        for section, answer in results.items():
            f.write(f"## {section.replace('_', ' ').title()}\n\n")
            f.write(answer + "\n\n")
    print(f"\n[INFO] Credit memo saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Credit Memo Generator")
    parser.add_argument("--n_results", type=int, default=5, help="Number of retrieved docs per query")
    args = parser.parse_args()

    main(n_results=args.n_results)
