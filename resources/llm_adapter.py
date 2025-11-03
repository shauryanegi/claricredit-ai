import json
import requests
import logging
from resources.config import config

class LocalLLMAdapter:
    def __init__(self, endpoint: str, model: str, timeout: int = config.LLM_TIMEOUT):
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout

    def chat(self, messages, tools=None, max_tokens=512, temperature=0.0):
        logging.info(f"Sending chat request to {self.endpoint} with model {self.model}")
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "think": False,
            "options": {
                "num_ctx": 12288
            }
        }
        if tools:
            payload["tools"] = tools

        def safe_json_parse(resp_text: str):
            try:
                return json.loads(resp_text)
            except json.JSONDecodeError as e:
                logging.error(f"JSONDecodeError: {e}. Trying to parse first line.")
                first_line = resp_text.splitlines()[0]
                try:
                    return json.loads(first_line)
                except json.JSONDecodeError as e2:
                    logging.error(f"Failed to parse even the first line of JSON: {e2}")
                    return {}

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = safe_json_parse(resp.text)
        except requests.exceptions.RequestException as e:
            logging.warning(f"First attempt failed: {e}")
            try:
                resp = requests.post(self.endpoint, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = safe_json_parse(resp.text)
            except requests.exceptions.RequestException as e2:
                logging.error(f"Second attempt failed: {e2}")
                return ""

        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        elif "message" in data and "content" in data["message"]:
            return data["message"]["content"]
        
        logging.warning(f"Could not find standard content fields in LLM response.")
        return data.get("output") or data.get("result") or str(data)
