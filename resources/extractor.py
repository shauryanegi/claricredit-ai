import requests
import base64
import os
import time
import logging
from resources.config import config

def image_to_base64(file_path: str) -> str:
    """Convert a PDF or image file to base64 string."""
    logging.debug(f"Reading file: {file_path}")
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        logging.debug(f"File size: {len(data)} bytes")
        encoded = base64.b64encode(data).decode("utf-8")
        logging.debug(f"Encoded base64 length: {len(encoded)}")
        return encoded
    except Exception as e:
        raise RuntimeError(f"Failed to read/encode file: {e}")

def extract_pdf(pdf_path: str, retries: int = 3, timeout: int = 300) -> str:
    """
    Send PDF to Marker API and save markdown output.
    Retries multiple times with long timeout before giving up.
    """
    start_time = time.time()
    base_url = config.LLM_ENDPOINT.split("/api")[0]
    url = f"{base_url}/api/v1/marker-text-extraction"
    logging.info(f"Using Marker API: {url}")

    req_data = {
        "req_id": "123",
        "doc_base64": image_to_base64(pdf_path),
        "json_output": False,
    }

    last_error = None
    for attempt in range(1, retries + 1):
        logging.info(f"Attempt {attempt}/{retries} → sending request...")
        try:
            logging.debug(f"Sending POST request with payload size: {len(req_data['doc_base64'])} chars")
            response = requests.post(url, json=req_data, timeout=timeout)
            logging.debug(f"Response received: status {response.status_code}")
            response.raise_for_status()

            resp_json = response.json()

            # Extract only the 'data' key
            md_text = resp_json.get("data", "")

            # Save to markdown if successful
            filename = os.path.basename(pdf_path).replace(".pdf", ".md")
            output_path = os.path.join(config.OUTPUT_DIR, filename)
            os.makedirs(config.OUTPUT_DIR, exist_ok=True)

            logging.debug(f"Writing response text to {output_path}")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md_text)

            logging.info(f"Saved extracted markdown to {output_path}")
            end_time = time.time()
            logging.info(f"Extraction completed in {end_time - start_time:.2f} seconds.")
            return output_path

        except requests.exceptions.Timeout:
            logging.error(f"Attempt {attempt} timed out after {timeout} seconds.")
            last_error = "Timeout"
        except requests.exceptions.RequestException as e:
            last_error = e
            logging.warning(f"Attempt {attempt} failed: {e}")

        if attempt < retries:
            wait = 5 * attempt  # exponential backoff: 5s, 10s, ...
            logging.info(f"Retrying in {wait}s...")
            time.sleep(wait)

    end_time = time.time()
    logging.error(f"All attempts failed after {end_time - start_time:.2f} seconds.")
    
    logging.critical(f"All {retries} attempts failed. Last error: {last_error}")
    raise RuntimeError(f"All {retries} attempts failed. Last error: {last_error}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    pdf_file = os.path.join(config.PDF_DIR, "Gamuda.pdf")
    logging.info(f"Starting PDF extraction for: {pdf_file}")
    extract_pdf(pdf_file, retries=3, timeout=300)