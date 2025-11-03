import os
import yaml
import argparse
import time
import logging
import asyncio
import concurrent.futures
from datetime import datetime
from resources.config import config
from resources import chunker
from resources.rag import RAGPipelineCosine
from resources.retrieval_queries.sections import CREDIT_MEMO_SECTIONS
from resources.split_md_by_page import split_md_by_page

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_prompts(file_path: str) -> dict:
    """Load YAML prompts as a dictionary of {section: prompt_text}."""
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

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

async def run_pipeline(md_file: str, n_results: int = 5, query: str = None):
    start_time = time.time()
    logging.info(f"Starting pipeline with Markdown file: {md_file}")

    # Step 1: Chunk + embeddings
    file_name = os.path.basename(md_file).replace(".md", "")
    processor = chunker.MarkdownChunker(file_name, output_dir=config.OUTPUT_DIR)
    chunks, embeddings = await processor.create_embeddings_and_index_async(md_file)
    logging.info(f"Processed {len(chunks)} chunks.")

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
        logging.info(f"Running single query: {query}")
        docs_with_meta = rag.retrieve(query, n_results=n_results)
        context_docs = [doc for doc, meta in docs_with_meta]
        answer = rag.generate_answer(query, context_docs)
        results["single_query"] = {"question": query, "answer": answer}
        logging.info(f"ANSWER: {answer}")
    else:
        # Full memo generation (parallelized)
        split_page_file = split_md_by_page(md_file)
        
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

        results = await asyncio.to_thread(
            run_rag_tasks_in_parallel,
            rag,
            parallel_tasks,
            summary_group,
            recommendation_group,
            split_page_file
        )

    # Step 3: Save results with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if query:
        filename = f"single_query_result_{timestamp}.md"
        output_path = os.path.join(config.OUTPUT_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"## {results['single_query']['question']}\n\n")
            f.write(f"\n{results['single_query']['answer']}\n\n")
    else:
        filename = f"credit_memo_from_md_{timestamp}.md"
        output_path = os.path.join(config.OUTPUT_DIR, filename)
        with open(output_path, "w", encoding="utf-8") as f:
            for section in CREDIT_MEMO_SECTIONS:
                answers = results.get(section)
                if answers:
                    f.write(f"## {section.replace('_', ' ').title()}\n\n")
                    f.write("\n\n".join(filter(None, answers)) + "\n\n")

    logging.info(f"Results saved to {output_path}")
    end_time = time.time()
    logging.info(f"Pipeline completed in {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Credit Memo from Markdown")
    parser.add_argument("--md", type=str, required=True, help="Path to markdown file")
    parser.add_argument("--n_results", type=int, default=5, help="Number of retrieved docs per query")
    parser.add_argument("--query", type=str, help="Run a single ad-hoc query instead of full memo")
    args = parser.parse_args()

    asyncio.run(run_pipeline(md_file=args.md, n_results=args.n_results, query=args.query))