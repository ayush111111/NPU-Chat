#!/usr/bin/env python3
"""Benchmark FastFlowLM NPU inference: prefill vs decode throughput + memory.

Usage:  python bench.py [--model qwen3.5:2b] [--port 52625] [--runs 3]

Reads the per-request timing block FastFlowLM returns in `usage`:
  prefill_duration_ttft, prefill_speed_tps, decoding_duration, decoding_speed_tps
"""
import argparse, json, statistics, subprocess, sys, urllib.request

# Prompt sizes to sweep. Prefill throughput is overhead-dominated below ~500
# tokens, so short prompts understate it badly.
PROMPT_TOKENS = [128, 512, 2048, 8192]
FILLER = "The quick brown fox jumps over the lazy dog. "  # ~10 tokens


def post(port, payload, timeout=600):
    req = urllib.request.Request(
        f"http://localhost:{port}/v1/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def run(port, model, prompt_tokens, max_tokens):
    prompt = (FILLER * (prompt_tokens // 10 + 1))[: prompt_tokens * 4]
    body = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt + "\n\nSummarise the above in detail."}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stream": False,
    }
    return post(port, body)["usage"]


def npu_memory():
    """Memory used by the flm.exe server process, in GB.

    The XDNA NPU has no dedicated VRAM - weights live in shared system RAM.
    Working set alone understates it (Windows trims pages of an idle server),
    so report committed private bytes too; that is the real footprint.
    """
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "$p = Get-Process flm -ErrorAction SilentlyContinue; "
         "if ($p) { '{0} {1}' -f ($p | Measure-Object WorkingSet64 -Sum).Sum, "
         "($p | Measure-Object PrivateMemorySize64 -Sum).Sum }"],
        capture_output=True, text=True,
    ).stdout.split()
    if len(out) != 2:
        return None
    return int(out[0]) / 1e9, int(out[1]) / 1e9


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3.5:2b")
    ap.add_argument("--port", type=int, default=52625)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--max-tokens", type=int, default=128)
    a = ap.parse_args()

    print(f"model={a.model}  runs={a.runs}  max_tokens={a.max_tokens}\n")
    print(f"{'prompt tok':>10} {'gen tok':>8} {'TTFT s':>8} "
          f"{'prefill t/s':>12} {'decode t/s':>11}")
    print("-" * 54)

    for n in PROMPT_TOKENS:
        pre, dec, ttft, ptok, ctok = [], [], [], [], []
        for i in range(a.runs):
            try:
                u = run(a.port, a.model, n, a.max_tokens)
            except Exception as e:
                print(f"{n:>10}  failed: {e}")
                break
            # First run warms caches; drop it when we have spares.
            if i == 0 and a.runs > 1:
                continue
            pre.append(u["prefill_speed_tps"])
            dec.append(u["decoding_speed_tps"])
            ttft.append(u["prefill_duration_ttft"])
            ptok.append(u["prompt_tokens"])
            ctok.append(u["completion_tokens"])
        if pre:
            print(f"{statistics.mean(ptok):>10.0f} {statistics.mean(ctok):>8.0f} "
                  f"{statistics.mean(ttft):>8.3f} {statistics.mean(pre):>12.1f} "
                  f"{statistics.mean(dec):>11.1f}")

    mem = npu_memory()
    if mem:
        print(f"\nflm.exe memory: {mem[0]:.2f} GB resident / {mem[1]:.2f} GB "
              f"committed (shared system RAM, no dedicated VRAM)")
    else:
        print("\nflm.exe not running")


if __name__ == "__main__":
    sys.exit(main())
