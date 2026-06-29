"""Ollama LLM client with normal and streaming generation."""
import json, logging, time, requests
from backend.config import OLLAMA_BASE_URL, OLLAMA_MODEL
logger=logging.getLogger(__name__); GENERATE_API=f"{OLLAMA_BASE_URL}/api/generate"; MAX_RETRIES=2; RETRY_DELAY_SECONDS=1.5
OPTIONS={"temperature":0.1,"top_p":0.8,"top_k":20,"num_predict":360,"num_ctx":4096,"repeat_penalty":1.05}
def generate_response(prompt:str, temperature:float=0.2, max_retries:int=MAX_RETRIES)->str:
    if not prompt or not prompt.strip(): raise ValueError("Prompt cannot be empty")
    payload={"model":OLLAMA_MODEL,"prompt":prompt,"stream":False,"options":OPTIONS}; last=RuntimeError("Unknown error")
    for attempt in range(1,max_retries+2):
        try:
            r=requests.post(GENERATE_API,json=payload,timeout=60); r.raise_for_status(); ans=r.json().get("response","").strip()
            if not ans: raise RuntimeError("Ollama returned an empty response")
            return ans
        except (requests.exceptions.Timeout,requests.exceptions.ConnectionError) as e:
            last=RuntimeError("Cannot connect to Ollama. Is 'ollama serve' running?"); time.sleep(RETRY_DELAY_SECONDS) if attempt<=max_retries else None
        except Exception as e: raise RuntimeError(str(e))
    raise last
def stream_response(prompt:str):
    if not prompt or not prompt.strip(): raise ValueError("Prompt cannot be empty")
    payload={"model":OLLAMA_MODEL,"prompt":prompt,"stream":True,"options":OPTIONS}
    with requests.post(GENERATE_API,json=payload,timeout=90,stream=True) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line: continue
            data=json.loads(line); token=data.get("response","")
            if token: yield token
            if data.get("done"): break
