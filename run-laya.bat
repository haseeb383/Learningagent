@echo off
title Laya System-1 Model Server

echo ===================================================
echo [!] Starting Laya Local Memory Server...
echo [!] This window must stay open while testing.
echo ===================================================

:: Force the model to preload entirely into memory right now
set LAYA_PRELOAD=1

:: Change to "cuda" if you want to use an Nvidia GPU instead of CPU
set LAYA_DEVICE=cpu

:: Launch the server
laya-serve --host 127.0.0.1 --port 8000

echo.
echo [!] Server has shut down.
pause
