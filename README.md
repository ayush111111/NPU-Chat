# NPU-Chat

Local AI chat stack running entirely on the **XDNA 2 NPU** via [FastFlowLM](https://fastflowlm.com). Combines Open WebUI (chat), Langflow (agent builder), and NPU-accelerated inference — no GPU required.

## Stack

| Service | URL | Purpose |
|---|---|---|
| Open WebUI | http://localhost:3000 | Chat interface |
| Langflow | http://localhost:7860 | Agent / flow builder |
| FastFlowLM | http://localhost:52625 | NPU inference server |

**Models (all on NPU, `NPU2` format):**

| Model | Role | Params | Quant | Weights | Context |
|---|---|---|---|---|---|
| `qwen3.5:2b` | LLM | 2B | Q4_1 | 3.2 GB | 32768 |
| `whisper-v3:turbo` | Speech-to-text | 1B | Q4_1 | 0.62 GB | 448 |
| `embed-gemma:300m` | Embeddings (RAG) | 300M | none | 0.62 GB | 2048 |

Run `flm list --filter installed --json` for the full set.

## Prerequisites

- [FastFlowLM](https://fastflowlm.com) installed and on `PATH`
- Docker Desktop

## Quick Start

**1. Start the NPU server**
```bat
start-flm.bat
```
or manually:
```
flm serve qwen3.5:2b --asr 1 --emb 1 --port 52625 -s 5 -q 40
```

**2. Start Docker services**
```
docker compose up -d
```

**3. Open** http://localhost:3000 to chat.

## Langflow Setup

In any Langflow flow, add an **OpenAI** component and set:
- Base URL: `http://host.docker.internal:52625/v1`
- API Key: `dummy-key`
- Model: `qwen3.5:2b`

## Commands

```bash
docker compose logs -f   # tail logs
docker compose down      # stop all services
```

## Performance

Measured on XDNA 2 NPU with `qwen3.5:2b` (Q4_1), 128 generated tokens per run:

| Prompt tokens | TTFT | Prefill tok/s | Decode tok/s |
|---|---|---|---|
| 135 | 0.71 s | 190 | 22.1 |
| 476 | 0.98 s | 485 | 20.8 |
| 1842 | 2.53 s | 731 | 21.6 |
| 7304 | 8.08 s | 905 | 19.9 |

**Prefill ~900 tok/s, decode ~20 tok/s** — a ~45:1 ratio (compute-bound vs
memory-bound). Prefill figures below ~2k tokens are dominated by ~0.7 s of fixed
TTFT overhead and understate the real rate; quote the 8k row. Decode drops ~10%
at 8k context as KV-cache reads grow.

**Memory:** 4.84 GB committed (0.60 GB resident — Windows trims an idle server's
working set, so committed private bytes is the honest number). The NPU has no
dedicated VRAM; weights sit in shared system RAM. Add ~0.6 GB each for the ASR
and embedding models.

### Reproducing

FastFlowLM returns timings in the `usage` block of every
`/v1/chat/completions` response, so no external instrumentation is needed:

```json
"usage": {
  "prompt_tokens": 21, "completion_tokens": 25,
  "prefill_duration_ttft": 0.770, "prefill_speed_tps": 27.3,
  "decoding_duration": 1.168,     "decoding_speed_tps": 21.4
}
```

`bench.py` sweeps prompt lengths, discards the warm-up run and averages:

```bash
python bench.py --model qwen3.5:2b --runs 3
```
