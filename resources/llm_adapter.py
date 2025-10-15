import json
import requests
from resources.config import config

class LocalLLMAdapter:
    def __init__(self, endpoint: str, model: str, timeout: int = config.LLM_TIMEOUT):
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout

    def chat(self, messages, tools=None, max_tokens=512, temperature=0.0):
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            "think": False
        }
        if tools:
            payload["tools"] = tools

        def safe_json_parse(resp_text: str):
            try:
                return json.loads(resp_text)
            except json.JSONDecodeError:
                first_line = resp_text.splitlines()[0]
                return json.loads(first_line)

        try:
            resp = requests.post(self.endpoint, json=payload, timeout=self.timeout)
            data = safe_json_parse(resp.text)
        except Exception as e:
            print(f"First attempt failed: {e}")
            try:
                resp = requests.post(self.endpoint, json=payload, timeout=self.timeout)
                data = safe_json_parse(resp.text)
            except Exception as e2:
                print(f"Second attempt failed: {e2}")
                return ""

        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        elif "message" in data and "content" in data["message"]:
            return data["message"]["content"]
        return data.get("output") or data.get("result") or str(data)
