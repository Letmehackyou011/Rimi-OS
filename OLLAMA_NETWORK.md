# Ollama Network Connection

The web console and CLI can connect to Ollama on the same machine or another host on the Rimi OS/Kali LAN.

## Expose Ollama on Linux/Rimi OS

Run Ollama with a LAN bind address:

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

For a systemd installation, set `OLLAMA_HOST=0.0.0.0:11434` in the Ollama service environment and restart the service. Open TCP port `11434` only on the trusted management network.

## Expose Ollama on Windows PowerShell

```powershell
$env:OLLAMA_HOST = "0.0.0.0:11434"
ollama serve
```

Use the Windows Firewall to restrict inbound TCP `11434` to the Rimi OS/Kali host or trusted subnet. Do not expose Ollama directly to the public internet; the Ollama endpoint has no built-in authentication boundary for this application.

## Configure the application

In the web console, open **Settings** and enter:

- Host or IP: for example `192.168.1.20`
- Port: usually `11434`
- Model: `hf.co/llmfan46/gemma-4-E4B-it-ultra-uncensored-heretic-GGUF:Q5_K_M`

Use **Test connection**, then **Save endpoint**. The setting is stored in `runtime-config.json` and used by LangChain scans, the assistant page, and the CLI.

## CLI

```powershell
python cli.py --endpoint http://192.168.1.20:11434 models
python cli.py --endpoint http://192.168.1.20:11434 --model hf.co/llmfan46/gemma-4-E4B-it-ultra-uncensored-heretic-GGUF:Q5_K_M chat
```

The CLI also accepts a strict authorization file for queued assessments:

```powershell
python cli.py scan 192.168.1.20 --scope-file scope.json
```

The CLI does not expose arbitrary remote shell execution. Scan commands remain constrained by the JSON scope and the allowlisted tool runner.
