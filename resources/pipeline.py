import os
import yaml
import argparse
import time
import logging
import asyncio
import concurrent.futures
from resources.config import config
from resources import extractor, chunker
from resources.rag import RAGPipelineCosine
from resources.split_md_by_page import split_md_by_page
from resources.retrieval_queries.sections import CREDIT_MEMO_SECTIONS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_rag_tasks_in_parallel(rag, parallel_tasks, summary_group, recommendation_group, split_page_file):
    results = {section: [] for section in CREDIT_MEMO_SECTIONS}
    summary_context = []
    recommendation_context = []

    with concurrent.futures.ThreadPoolExecutor() as executor:
        logging.info(f"Using {executor._max_workers} worker threads for parallel execution.")
        future_to_task = {executor.submit(rag.run, task[1], split_page_file): task for task in parallel_tasks}

        for future in concurrent.futures.as_completed(future_to_task):
            section, group = future_to_task[future]
            try:
                answer = future.result()
                
                original_index = CREDIT_MEMO_SECTIONS[section].index(group)
                while len(results[section]) <= original_index:
                    results[section].append(None)
                results[section][original_index] = answer

                if group.get("include_for_summary"):
                    summary_context.append(answer)
                if group.get("include_for_recommendation"):
                    recommendation_context.append(answer)
                
                logging.info(f"Completed prompt for section: {section}")

            except Exception as exc:
                logging.error(f'Section "{section}" generated an exception: {exc}')

    # Run dependent tasks (Summary and Recommendation)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_task = {}
        if summary_group:
            summary_context.insert(0, """Loan Request and Proposed Structure
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
            future_to_task[executor.submit(rag.generate_answer, summary_group[1]["user_query"], summary_context)] = summary_group

        if recommendation_group:
            future_to_task[executor.submit(rag.generate_answer, recommendation_group[1]["user_query"], recommendation_context)] = recommendation_group
        
        for future in concurrent.futures.as_completed(future_to_task):
            section, group = future_to_task[future]
            try:
                answer = future.result()
                results[section].append(answer)
                logging.info(f"Completed section: {section}")
            except Exception as exc:
                logging.error(f'Section "{section}" generated an exception: {exc}')
    return results

async def main(pdf_name: str):
    logging.info("Starting Credit Memo Pipeline...")
    start_time = time.time()

    # Step 1: Extract PDF → Markdown
    pdf_file = os.path.join(config.PDF_DIR, pdf_name)
    md_file = extractor.extract_pdf(pdf_file)
    file_name = pdf_name.replace(".pdf", "")

    # Step 2: Chunk + embeddings
    processor = chunker.MarkdownChunker(file_name, output_dir=config.OUTPUT_DIR)
    chunks, embeddings = await processor.create_embeddings_and_index_async(md_file)
    logging.info(f"Processed {len(chunks)} chunks.")

    # Step 3: Initialize RAG pipeline
    rag = RAGPipelineCosine(
        chroma_path=config.CHROMA_PATH,
        collection_name=f"markdown_chunks_{file_name}",
        llm_endpoint=config.LLM_ENDPOINT,
        llm_model=config.LLM_MODEL
    )

    split_page_file = split_md_by_page(md_file)

    # Step 4: Separate tasks for parallel execution
    parallel_tasks = []
    summary_group = None
    recommendation_group = None
    
    for section, groups in CREDIT_MEMO_SECTIONS.items():
        if section == "Executive Summary":
            summary_group = (section, groups[0])
        elif section == "Recommendation and Conclusion":
            recommendation_group = (section, groups[0])
        else:
            for group in groups:
                parallel_tasks.append((section, group))

    # Step 5: Run RAG tasks in a separate thread to avoid blocking the event loop
    results = await asyncio.to_thread(
        run_rag_tasks_in_parallel,
        rag,
        parallel_tasks,
        summary_group,
        recommendation_group,
        split_page_file
    )

    # Step 7: Save results
    output_path = os.path.join(config.OUTPUT_DIR, f"credit_memo_{file_name}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        for section in CREDIT_MEMO_SECTIONS:
            answers = results[section]
            if answers:
                f.write(f"## {section.replace('_', ' ').title()}\n\n")
                f.write("\n\n".join(filter(None, answers)) + "\n\n")

    logging.info(f"Credit memo saved to {output_path}")
    end_time = time.time()
    logging.info(f"Total time taken: {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Credit Memo Generator")
    parser.add_argument("--pdf", type=str, help="Name of the PDF file in the files directory", required=True)
    args = parser.parse_args()

    asyncio.run(main(pdf_name=args.pdf))
