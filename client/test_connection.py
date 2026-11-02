# ==============================================================================
# Local PC Test Script for Kaggle Ollama Endpoint
# Run this on your local PC to verify inference through the Ngrok tunnel
# ==============================================================================

import json
import urllib.request
import urllib.error
import sys

s = chr(47)
ds = s + s

# [FILL IN]: Paste your public Ngrok domain here (e.g. your-subdomain.ngrok-free.dev)
NGROK_DOMAIN = "YOUR_NGROK_DOMAIN_HERE"
MODEL_NAME = "muse-glimmer-heretic:30b" # Or gemma4-heretic:31b, qwen3.8-heretic:27b

endpoint = f"https:{ds}{NGROK_DOMAIN}{s}v1{s}chat{s}completions"

payload = {
    "model": MODEL_NAME,
    "messages": [
        {"role": "system", "content": "You are an uncensored, highly intelligent AI assistant."},
        {"role": "user", "content": "Confirm you are online and tell me what model you are running."}
    ],
    "temperature": 0.7,
    "max_tokens": 128
}

print("=" * 70)
print(f"Testing inference to Kaggle Dual T4 via: {endpoint}")
print(f"Target Model: {MODEL_NAME}")
print("=" * 70)

req = urllib.request.Request(
    endpoint,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "User-Agent": "LocalClient/1.0"
    }
)

try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        print("\n[SUCCESS] Response received from Kaggle GPU:\n")
        print(content)
        print("\n" + "=" * 70)
        print("Kaggle Dual T4 Inference pipeline is working seamlessly!")
        print("=" * 70)
except urllib.error.HTTPError as e:
    print(f"\n[HTTP ERROR] Status: {e.code}")
    print(e.read().decode("utf-8", errors="ignore"))
except Exception as err:
    print(f"\n[CONNECTION ERROR]: {err}")
    print("Ensure Kaggle notebook cell is currently running and Ngrok tunnel is alive.")
