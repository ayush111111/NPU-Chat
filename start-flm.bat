@echo off
REM Start FastFlowLM NPU server with LFM2.5 + Whisper ASR
REM This single server handles LLM (lfm2.5-it:1.2b) and STT (whisper-v3-turbo) on NPU

echo [NPU-Chat] Starting FastFlowLM server...
echo [NPU-Chat] LLM:  lfm2.5-it:1.2b  (~35 tok/sec on XDNA 2 NPU)
echo [NPU-Chat] STT:  whisper-v3-turbo (NPU)
echo [NPU-Chat] Port: 52625
echo.

flm serve lfm2.5-it:1.2b --asr 1 --port 52625
