@echo off
REM Start FastFlowLM NPU server with LFM2.5 + Whisper ASR
REM This single server handles LLM (qwen3.5:2b) and STT (whisper-v3-turbo) on NPU

echo [NPU-Chat] Starting FastFlowLM server...
echo [NPU-Chat] LLM:  qwen3.5:2b  (XDNA 2 NPU)
echo [NPU-Chat] STT:  whisper-v3-turbo (NPU)
echo [NPU-Chat] EMB:  embed-gemma:300m (NPU)
echo [NPU-Chat] Port: 52625
echo [NPU-Chat] Concurrency: 5 concurrent, queue depth 40 (~200 req/min)
echo.

REM -s 5  = 5 concurrent socket connections per model
REM -q 40 = queue up to 40 pending requests before rejecting (handles 200 req/min bursts)
flm serve qwen3.5:2b --asr 1 --emb 1 --port 52625 -s 5 -q 40
