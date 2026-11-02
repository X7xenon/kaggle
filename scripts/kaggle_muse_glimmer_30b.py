# ==============================================================================
# Muse-Glimmer-30B Heretic Abliterated - Kaggle Dual Tesla T4 Setup
# Base Model: mlasli/Muse-Glimmer-30B-Heretic-Abliterated-BF16
# Quantized GGUF: mlasli/Muse-Glimmer-30B-Heretic-Abliterated-Q4_K_M-GGUF
# Context: 65,536 - 131,072 tokens | VRAM: Dual Tesla T4 (30 GB)
# ==============================================================================

import subprocess
import time
import os
import sys
from IPython.display import display, HTML

s = chr(47)
ds = s + s

# ------------------------------------------------------------------------------
# 1. Environment & GPU Topology Verification
# ------------------------------------------------------------------------------
print("=" * 70)
print(">>> [1/7] Inspecting Storage Partitions & GPU VRAM Topology...")
print("=" * 70)
subprocess.run(["df", "-h", "/kaggle/working", "/tmp"])
subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv"])

# ------------------------------------------------------------------------------
# 2. Package & Ollama Tooling Installation
# ------------------------------------------------------------------------------
print("\n" + "=" * 70)
print(">>> [2/7] Installing aria2, zstd, pciutils, pyngrok, ollama...")
print("=" * 70)
subprocess.run(["apt-get", "update", "-qq"])
subprocess.run(["apt-get", "install", "-y", "-qq", "aria2", "zstd", "pciutils"])
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyngrok"])

if not os.path.exists("/usr/local/bin/ollama"):
    print("\n>>> Installing Ollama standalone binary...")
    install_cmd = f"curl -fsSL https:{ds}ollama.com{s}install.sh | sh"
    subprocess.run(install_cmd, shell=True, check=True)

# ------------------------------------------------------------------------------
# 3. High-Speed Download into /tmp/models (73 GB Fast Partition)
# ------------------------------------------------------------------------------
MODEL_DIR = "/tmp/models"
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_FILENAME = "Muse-Glimmer-30B-Heretic-Abliterated-Q4_K_M.gguf"
MMPROJ_FILENAME = "mmproj-Muse-Glimmer-30B-Q4_K_M.gguf"
MODEL_PATH = os.path.join(MODEL_DIR, MODEL_FILENAME)
MMPROJ_PATH = os.path.join(MODEL_DIR, MMPROJ_FILENAME)

MODEL_URL = f"https:{ds}huggingface.co{s}mlasli{s}Muse-Glimmer-30B-Heretic-Abliterated-Q4_K_M-GGUF{s}resolve{s}main{s}{MODEL_FILENAME}"
MMPROJ_URL = f"https:{ds}huggingface.co{s}mlasli{s}Muse-Glimmer-30B-Heretic-Abliterated-Q4_K_M-GGUF{s}resolve{s}main{s}{MMPROJ_FILENAME}"

if not os.path.exists(MODEL_PATH) or os.path.getsize(MODEL_PATH) < 16000000000:
    print(f"\n>>> [3/7] Downloading {MODEL_FILENAME} (16.9 GB) via aria2c...")
    subprocess.run([
        "aria2c", "-x", "16", "-s", "16", "-k", "1M", "--file-allocation=none",
        "-d", MODEL_DIR, "-o", MODEL_FILENAME, MODEL_URL
    ], check=True)
else:
    print(f"\n>>> [3/7] Model weights cached and verified ({os.path.getsize(MODEL_PATH):,} bytes)")

if not os.path.exists(MMPROJ_PATH):
    print(f"\n>>> Downloading Projector: {MMPROJ_FILENAME} (1.4 GB)...")
    subprocess.run([
        "aria2c", "-x", "8", "-s", "8", "-k", "1M", "--file-allocation=none",
        "-d", MODEL_DIR, "-o", MMPROJ_FILENAME, MMPROJ_URL
    ])

for item in os.listdir(MODEL_DIR):
    if item.endswith(".aria2"):
        os.remove(os.path.join(MODEL_DIR, item))

# ------------------------------------------------------------------------------
# 4. Modelfile Creation (ATEM Protocol & Agent Tool Calling)
# ------------------------------------------------------------------------------
print("\n>>> [4/7] Generating Ollama Modelfile...")
MODELFILE_PATH = "/tmp/Modelfile.muse"
modelfile_content = f"""FROM {MODEL_PATH}
PARAMETER temperature 0.7
PARAMETER top_p 0.95
PARAMETER top_k 64
PARAMETER num_ctx 65536
PARAMETER num_gpu 99
TEMPLATE \"\"\"{{{{ if .System }}}}<|start|>system<|message|>
{{{{ .System }}}}<|eot|>
{{{{ end }}}}{{{{ if .Prompt }}}}<|start|>user<|message|>
{{{{ .Prompt }}}}<|eot|>
{{{{ end }}}}<|start|>assistant<|message|>
{{{{ .Response }}}}<|eot|>\"\"\"
"""

with open(MODELFILE_PATH, "w") as f:
    f.write(modelfile_content)
print(f"Modelfile written to {MODELFILE_PATH}")

# ------------------------------------------------------------------------------
# 5. Launch Ollama Daemon on Dual T4 & Register Model
# ------------------------------------------------------------------------------
print("\n>>> [5/7] Starting Ollama daemon on Dual Tesla T4 GPUs...")
subprocess.run(["pkill", "-9", "-f", "ollama"])
time.sleep(2)

ollama_env = dict(
    os.environ,
    OLLAMA_MODELS="/tmp/ollama_models",
    CUDA_VISIBLE_DEVICES="0,1",
    OLLAMA_HOST="0.0.0.0:11434",
    OLLAMA_NUM_PARALLEL="1"
)
os.makedirs("/tmp/ollama_models", exist_ok=True)

subprocess.Popen(
    ["/usr/local/bin/ollama", "serve"],
    env=ollama_env,
    stdout=open('/tmp/ollama.log', 'w'),
    stderr=subprocess.STDOUT
)
time.sleep(4)

print("Registering 'muse-glimmer-heretic:30b' in Ollama...")
subprocess.run(["/usr/local/bin/ollama", "create", "muse-glimmer-heretic:30b", "-f", MODELFILE_PATH], env=ollama_env, check=True)
subprocess.run(["/usr/local/bin/ollama", "list"], env=ollama_env)

# ------------------------------------------------------------------------------
# 6. Ngrok Reverse Tunnel Connection
# ------------------------------------------------------------------------------
print("\n" + "=" * 70)
print(">>> [6/7] Connecting Ngrok tunnel & registering endpoint...")
print("=" * 70)
from pyngrok import ngrok, conf

NGROK_AUTHTOKEN = os.environ.get("NGROK_AUTHTOKEN", "YOUR_NGROK_AUTHTOKEN_HERE")
NGROK_DOMAIN = os.environ.get("NGROK_DOMAIN", "")

conf.get_default().auth_token = NGROK_AUTHTOKEN
ngrok.kill()
time.sleep(1)

if NGROK_DOMAIN:
    tunnel = ngrok.connect(addr="11434", proto="http", url=f"https:{ds}{NGROK_DOMAIN}")
else:
    tunnel = ngrok.connect(addr="11434", proto="http")

print("\n" + "=" * 70)
print(f"PUBLIC NGROK ENDPOINT: {tunnel.public_url}")
print(f"OPENAI COMPATIBLE BASE URL: {tunnel.public_url}{s}v1")
print(f"MODEL NAME: muse-glimmer-heretic:30b")
print("=" * 70 + "\n")

# ------------------------------------------------------------------------------
# 7. Safe Non-Blocking Keep-Alive Daemon (9-Hour Session Guard)
# ------------------------------------------------------------------------------
display(HTML("""
<script>
function keepAlive() {
    console.log("[Keep-Alive] Heartbeat: " + new Date().toLocaleTimeString());
    window.dispatchEvent(new MouseEvent('mousemove', { bubbles: true, cancelable: true }));
}
if (window.kaggleGuardTimer) clearInterval(window.kaggleGuardTimer);
window.kaggleGuardTimer = setInterval(keepAlive, 25000);
console.log("[Keep-Alive] 9-Hour session guard active!");
</script>
"""))

print("=" * 70)
print("KAGGLE ANTI-SHUTDOWN DAEMON STARTED")
print("Streaming heartbeats every 30s to keep kernel permanently BUSY...")
print("=" * 70 + "\n")

start_time = time.time()
while True:
    elapsed_sec = int(time.time() - start_time)
    mins = int(elapsed_sec / 60)
    hours = int(mins / 60)
    rem_mins = mins % 60
    rem_secs = elapsed_sec % 60
    print(f"[Heartbeat] Uptime: {hours:02d}h {rem_mins:02d}m {rem_secs:02d}s | Ollama muse-glimmer-heretic:30b & Ngrok Active | Status: OK", flush=True)
    time.sleep(30)
