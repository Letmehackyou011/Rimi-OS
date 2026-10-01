"""Rimi OS local CLI for Ollama chat and controlled scan operations."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import httpx

from config.settings import settings
from utils.ollama_client import OllamaClient, OllamaConnection, endpoint_from_host


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="rimi", description="Rimi OS security assistant")
    root.add_argument("--endpoint", default=settings.OLLAMA_ENDPOINT, help="Ollama URL, for example http://192.168.1.20:11434")
    root.add_argument("--model", default=settings.OLLAMA_MODEL, help="Installed Ollama model name")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("models", help="list models exposed by Ollama")
    chat = commands.add_parser("chat", help="chat with an Ollama model")
    chat.add_argument("prompt", nargs="?", help="one prompt; omit for interactive chat")
    scan = commands.add_parser("scan", help="queue a scoped assessment through the local API")
    scan.add_argument("target")
    scan.add_argument("--scope-file", required=True, help="strict JSON scope document")
    scan.add_argument("--api", default="http://127.0.0.1:8000")
    return root


async def run(args: argparse.Namespace) -> int:
    connection = OllamaConnection(endpoint=args.endpoint, model=args.model)
    client = OllamaClient(connection)
    if args.command == "models":
        print(json.dumps(await client.health(), indent=2))
        return 0
    if args.command == "chat":
        messages: list[dict[str, str]] = []
        prompts = [args.prompt] if args.prompt else []
        if not prompts:
            print(f"Connected to {connection.endpoint} using {connection.model}. Type /exit to quit.")
        while True:
            prompt = prompts.pop(0) if prompts else input("rimi> ")
            if prompt.strip().lower() in {"/exit", "/quit"}:
                return 0
            messages.append({"role": "user", "content": prompt})
            response = await client.chat(messages)
            message = response.get("message", {})
            content = message.get("content", "")
            print(content)
            messages.append({"role": "assistant", "content": content})
            if args.prompt:
                return 0
    if args.command == "scan":
        scope = json.loads(open(args.scope_file, encoding="utf-8").read())
        async with httpx.AsyncClient(timeout=30) as api:
            response = await api.post(f"{args.api.rstrip('/')}/api/scan/start", json={"target": args.target, "scope": scope, "mode": scope["mode"], "llm_provider": "ollama", "llm_model": connection.model})
            response.raise_for_status()
            print(json.dumps(response.json(), indent=2))
        return 0
    return 1


def main() -> None:
    try:
        raise SystemExit(asyncio.run(run(parser().parse_args())))
    except (httpx.HTTPError, ValueError, OSError, KeyboardInterrupt) as exc:
        print(f"rimi: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
