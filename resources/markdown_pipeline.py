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
        summary_context=[]
        for section, groups in CREDIT_MEMO_SECTIONS.items():
            section_start = time.time()
            print(f"Making section:{section}")
            section_results = []
            for group in groups:
                if section=="Executive Summary":
                    summary_context.append("""Recommendation
Approval with Conditions
Rationale: The loan approval is supported by company’s strong liquidity (current ratio of
2.1) and its moderate risk rating (4). The Debt-to-EBITDA ratio of 1.5 is acceptable for
infrastructure projects, though it is slightly elevated. A Loan-to-Value (LTV) of 65% reduces
the risk of equity dilution.
Conditions:
• Debt Covenants: The borrower is to maintain a debt-to-EBITDA ratio below 1.2x to
mitigate leverage risk.
• Use of Funds: Loan proceeds are to be strictly used for the approved capital expenditure
and acquisition, with compliance verified by third-party audits.
• Regular Monitoring: Quarterly financial reporting and stress tests are required to
assess liquidity under adverse scenarios.
• Interest Rate: The proposed 10% rate is competitive, but the borrower may be in a
position to negotiate a slightly lower rate given their strong liquidity.""")
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
                else:
                    answer = rag.run(group,split_page_file)
                    if group.get("include_for_summary"):
                        print(f"part of {section} included in summary")
                        summary_context.append(answer)
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
