import os
import yaml
import argparse
from resources.config import config
from resources import extractor, chunker
from resources.rag import RAGPipelineCosine
from resources.split_md_by_page import split_md_by_page
from resources.retrieval_queries.sections import CREDIT_MEMO_SECTIONS
import time


def load_prompts(file_path: str) -> dict:
    """Load YAML prompts as a dictionary of {section: prompt_text}."""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(pdf_name: str, n_results: int = 5):
    print("[INFO] Starting Credit Memo Pipeline...")
    start = time.time()
    # Step 1: Extract PDF → Markdown
    # Adjust filename as needed; you could also make this an argument.
    pdf_file = os.path.join(config.PDF_DIR, pdf_name)
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
    split_page_file = split_md_by_page(md_file)
    for section, groups in CREDIT_MEMO_SECTIONS.items():
        section_start = time.time()
        print(f"Making section:{section}")
        section_results = []
        for group in groups:
            answer = rag.run(group, split_page_file)
            section_results.append(answer)
        section_text = "\n\n".join(section_results)
        results[section] = section_text
        section_end = time.time()
        print(f"[INFO] Section '{section}' completed in {section_end - section_start:.2f} seconds.")

    # Step 5: Save results
    filename = os.path.basename(pdf_file).replace(".pdf", "")
    output_path = os.path.join(config.OUTPUT_DIR, f"credit_memo_{filename}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        for section, answer in results.items():
            f.write(f"## {section.replace('_', ' ').title()}\n\n")
            f.write(answer + "\n\n")
    print(f"\n[INFO] Credit memo saved to {output_path}")
    end = time.time()
    print(f"[INFO] Total time taken: {end - start:.2f} seconds.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Credit Memo Generator")
    parser.add_argument("--pdf", type=str, help="Name of the PDF file in the files directory", required=True)
    parser.add_argument("--n_results", type=int, default=5, help="Number of retrieved docs per query")
    args = parser.parse_args()

    main(pdf_name=args.pdf, n_results=args.n_results)