import os
import yaml
import argparse
from resources.config import config
from resources import extractor, chunker
from resources.rag import RAGPipelineCosine
from resources.split_md_by_page import split_md_by_page
from resources.retrieval_queries.sections import CREDIT_MEMO_SECTIONS
import time


def main(pdf_name: str):
    print("[INFO] Starting Credit Memo Pipeline...")
    start = time.time()
    # Step 1: Extract PDF → Markdown
    # Adjust filename as needed; you could also make this an argument.
    pdf_file = os.path.join(config.PDF_DIR, pdf_name)
    md_file = extractor.extract_pdf(pdf_file)
    file_name = pdf_name.replace(".pdf","")

    # Step 2: Chunk + embeddings
    processor = chunker.MarkdownChunker(file_name,output_dir=config.OUTPUT_DIR)
    chunks, embeddings = processor.create_embeddings_and_index(md_file)
    print(f"[INFO] Processed {len(chunks)} chunks.")

    # Step 3: Initialize RAG pipeline
    rag = RAGPipelineCosine(
        chroma_path=config.CHROMA_PATH,
        collection_name=f"markdown_chunks_{file_name}",
        llm_endpoint=config.LLM_ENDPOINT,
        llm_model=config.LLM_MODEL
    )

    results = {}
    split_page_file = split_md_by_page(md_file)
    summary_context=[]
    recommendation_context = []
    for section, groups in CREDIT_MEMO_SECTIONS.items():
        section_start = time.time()
        print(f"Making section:{section}")
        section_results = []
        for group in groups:
            if section=="Executive Summary":
                summary_context.append("""Loan Request and Proposed Structure
                    Sources and Uses of Funds
                    Sources of Funds
                    Proposed Term Loan: RM 7,500,000
                    Internal Accruals: RM 2,500,000
                    Total Sources: RM 10,000,000
                    Uses of Funds
                    New Plant Construction: RM 4,000,000
                    Acquisition of Competitor: RM 5,000,000
                    Working Capital Buffer: RM 1,000,000
                    Total Uses: RM 10,000,000
                    Proposed Loan Facility
                    Loan Amount: RM 7,500,000
                    Interest Rate: 10% p.a. (fixed)
                    Loan Term: 10 years
                    Repayment Schedule: Equal annual installments of principal and interest
                    Purpose of Funds
                    The funds will be utilized for capital expenditure related to the construction of a new plant, the strategic acquisition of a key competitor, and to maintain an adequate working capital buffer.
                    6. Collateral Analysis
                    Assets Pledged
                    Existing Plant & Machinery – Appraised Value: RM 6,000,000
                    Land Parcel (Industrial) – Appraised Value: RM 5,000,000
                    Accounts Receivable – Appraised Value: RM 2,000,000
                    Collateral Adequacy
                    Total Appraised Value: RM 13,000,000
                    Loan Amount: RM 7,500,000
                    Calculated Loan-to-Value (LTV) Ratio: ~65%""")
                user_query=group["user_query"]
                answer = rag.generate_answer(user_query,summary_context)
            elif section=="Recommendation and Conclusion":
                user_query=group["user_query"]
                answer = rag.generate_answer(user_query, recommendation_context)
            else:
                answer = rag.run(group,split_page_file)
                if group.get("include_for_summary"):
                    print(f"part of {section} included in summary")
                    summary_context.append(answer)
                elif group.get("include_for_recommendation"):
                    print(f"part of {section} included in recommendation")
                    recommendation_context.append(answer)
            section_results.append(answer)
        section_text="\n\n".join(section_results)
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
    args = parser.parse_args()

    main(pdf_name=args.pdf)