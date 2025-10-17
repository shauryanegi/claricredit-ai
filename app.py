import json
import logging
import os
import base64
import asyncio
import concurrent.futures
import shutil

from resources.config import config
from resources import chunker, extractor
from resources.rag import RAGPipelineCosine
from resources.split_md_by_page import split_md_by_page
from pydantic import BaseModel
from fastapi import FastAPI
from typing import Optional
from sse_starlette.sse import EventSourceResponse
from resources.retrieval_queries.sections import CREDIT_MEMO_SECTIONS, SECTION_ORDER

# Initialize logger
logger = logging.getLogger("app")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="Credit Memo Generator")


class PayloadRequest(BaseModel):
    req_id: str
    doc_base64: list[str]
    financial_data: Optional[dict[str, str]]


class PayloadResponse(BaseModel):
    req_id: str
    credit_memo: str
    success: bool
    error_message: str | None = None


class ProcessMessage(BaseModel):
    req_id: str
    message: str


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
            future_to_task[
                executor.submit(rag.generate_answer, summary_group[1]["user_query"], summary_context)] = summary_group

        if recommendation_group:
            future_to_task[executor.submit(rag.generate_answer, recommendation_group[1]["user_query"],
                                           recommendation_context)] = recommendation_group

        for future in concurrent.futures.as_completed(future_to_task):
            section, group = future_to_task[future]
            try:
                answer = future.result()
                results[section].append(answer)
                logging.info(f"Completed section: {section}")
            except Exception as exc:
                logging.error(f'Section "{section}" generated an exception: {exc}')
    return results

@app.post("/credit-memo")
async def generate_credit_memo(request: PayloadRequest):
    async def event_stream():
        try:
            req_id = request.req_id
            doc_base64 = request.doc_base64
            financial_data = request.financial_data

            logger.info(f"Received request with req_id: {req_id}")
            if not req_id or not doc_base64:
                yield {"error_message":"Invalid input request", "success":False}
                return


            os.makedirs(config.PDF_DIR, exist_ok=True)
            pdf_file_path = os.path.join(config.PDF_DIR, f"cache_{req_id}")
            os.makedirs(pdf_file_path, exist_ok=True)


            for i, b64_doc in enumerate(doc_base64):
                file_path = os.path.join(pdf_file_path, f"credit_doc_{req_id}_{i}.pdf")
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(b64_doc))

            yield {
                "event": "message",
                "data": json.dumps(
                    ProcessMessage(
                        req_id=req_id, message="Data Received, starting text extraction"
                    ).model_dump()
                ),
            }

            try:
                md_file = []
                for i, file_name in enumerate(os.listdir(pdf_file_path)):
                    if file_name.lower().endswith(".pdf"):
                        print(os.path.join(pdf_file_path,file_name))
                        md_file.append(extractor.extract_pdf(os.path.join(pdf_file_path,file_name)))
                yield {
                    "event": "message",
                    "data": json.dumps(
                        ProcessMessage(
                            req_id=req_id, message="Text extraction completed, starting embedding creation"
                        ).model_dump()
                    ),
                }
            except Exception as e:
                logger.error(f"Error occurred while extracting text: {e}")
                yield {json.dumps(PayloadResponse(req_id=req_id, credit_memo="", success=True, error_message="Error occurred while extracting text").model_dump())}
                return

            try:
                 file_name = str(os.path.basename(md_file[0]).replace(".md", ""))
                 processor = chunker.MarkdownChunker(file_name, output_dir=config.OUTPUT_DIR)
                 chunks, embeddings = await processor.create_embeddings_and_index_async(md_file[0])
                 logging.info(f"Processed {file_name} with {len(chunks)} chunks.")
                 yield {
                     "event": "message",
                     "data": json.dumps(
                         ProcessMessage(
                             req_id=req_id, message="embeddings created successfully, starting report generation"
                         ).model_dump()
                     ),
                 }
            except Exception as e:
                logger.error(f"Error occurred while creating embeddings: {e}")
                yield json.dumps(
                    PayloadResponse(req_id=req_id, credit_memo="", success=True, error_message="Error occurred while creating embeddings").model_dump()
                )
                return

            try:
                rag = RAGPipelineCosine(
                    collection_name=f"markdown_chunks_{file_name}",
                    llm_endpoint=config.LLM_ENDPOINT,
                    llm_model=config.LLM_MODEL
                )
                split_page_file = split_md_by_page(md_file[0])

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

                yield {
                    "event": "message",
                    "data": json.dumps(
                        ProcessMessage(
                            req_id=req_id, message="Report generation completed"
                        ).model_dump()
                    ),
                }
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"Error occurred generating report: {e}")
                yield {PayloadResponse(req_id=req_id, credit_memo="", success=True, error_message="Error occurred while generating report").model_dump()}
                return

            try:
                output_path = os.path.join(pdf_file_path, f"report_{req_id}_{file_name}.md")
                with open(output_path, "w", encoding="utf-8") as f:
                    for section in SECTION_ORDER:
                        # for section in CREDIT_MEMO_SECTIONS:
                        if section not in results:
                            logging.debug(f"'{section}' not in results, check section name")
                        else:
                            answers = results[section]
                            if answers:
                                if section == "Executive Summary":
                                    # Remove first line if it contains 'executive summary'

                                    cleaned_answers = []
                                    for ans in answers:
                                        # Remove first line if it contains 'executive summary'
                                        lines = ans.splitlines()
                                        if lines and "executive summary" in lines[0].lower():
                                            print("removed", lines[0])
                                            lines = lines[1:]
                                        ans = "\n".join(lines).strip()
                                        cleaned_answers.append(ans)
                                        answers = cleaned_answers
                            f.write(f"## {section.replace('_', ' ').title()}\n\n")
                            f.write("\n\n".join(filter(None, answers)) + "\n\n")
                logging.info(f"Credit memo saved to {output_path}")
                yield {
                    "event": "message",
                    "data": json.dumps(
                        ProcessMessage(
                            req_id=req_id, message="Credit memo generated successfully"
                        ).model_dump()
                    )
                }
            except Exception as e:
                logger.error(f"Error occurred while finalizing report: {e}")
                yield json.dumps(
                    PayloadResponse(req_id=req_id, credit_memo="", success=False, error_message="Error occurred while finalizing report").model_dump()
                )
                return

            with open(output_path, "rb") as file:
                md_file_encoded = base64.b64encode(file.read()).decode("utf-8")

            yield {json.dumps(PayloadResponse(req_id=req_id, credit_memo=md_file_encoded, success=True, error_message=None).model_dump())}
        except Exception as e:
            logger.exception(f" Error occurred while execution: {e}")
            yield {
                json.dumps(
                    PayloadResponse(
                        req_id=request.req_id,
                        credit_memo="",
                        success=False,
                        error_message="Error occurred while execution",
                    ).model_dump()
                )
            }
        finally:
            shutil.rmtree(pdf_file_path)
            logging.info(f"Deleted temporary files in {pdf_file_path}")

    return EventSourceResponse(event_stream())
