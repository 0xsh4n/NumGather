#!/usr/bin/env python3
"""
NumGather 2.0 — intelligent phone-number OSINT CLI.

Features:
  • Deep libphonenumber analysis (validity, type, carrier, timezone, formats)
  • India MSC circle / operator database
  • Optional Ollama local-LLM reasoning (incl. reasoning models)
"""

from __future__ import annotations

import argparse
import json
import sys

# Avoid Windows cp1252 crashes on Unicode output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pyfiglet

import lookup
import ollama_client
from lookup import VERSION, analyze_number, format_report

BANNER_FONT = "banner"


def print_banner() -> None:
    pyfiglet.print_figlet("Num Gather", BANNER_FONT)
    print(f"  NumGather v{VERSION} - phone intelligence + Ollama reasoning")
    print("  by H1DD3N_SH4D0W for SecHunt-OS")
    print("  https://github.com/0xsh4n/NumGather")
    print()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="NumGather",
        description="NumGather 2.0 — phone number intelligence & Ollama reasoning",
    )
    p.add_argument(
        "number",
        nargs="?",
        help="Phone number with country code (e.g. +919876543210). "
        "If omitted, interactive prompt is used.",
    )
    p.add_argument(
        "-r",
        "--region",
        default=None,
        help="Default ISO region if number has no +country_code (e.g. IN, US)",
    )
    p.add_argument(
        "-o",
        "--ollama",
        action="store_true",
        help="Run Ollama LLM reasoning over the intelligence report",
    )
    p.add_argument(
        "-m",
        "--model",
        default=None,
        help=f"Ollama model (default: env OLLAMA_MODEL or {ollama_client.DEFAULT_MODEL})",
    )
    p.add_argument(
        "--host",
        default=None,
        help=f"Ollama base URL (default: env OLLAMA_HOST or {ollama_client.DEFAULT_HOST})",
    )
    p.add_argument(
        "--stream",
        action="store_true",
        help="Stream Ollama response tokens to the terminal",
    )
    p.add_argument(
        "--list-models",
        action="store_true",
        help="List models available on the Ollama host and exit",
    )
    p.add_argument(
        "-j",
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit machine-readable JSON (includes ollama_analysis if -o)",
    )
    p.add_argument(
        "-b",
        "--batch",
        metavar="FILE",
        help="Analyze one number per line from FILE",
    )
    p.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors",
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Skip banner",
    )
    p.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"NumGather {VERSION}",
    )
    return p


def run_ollama(report: dict, args: argparse.Namespace) -> str | None:
    host = args.host
    model = args.model
    if not ollama_client.is_available(host):
        msg = (
            f"Ollama is not reachable at "
            f"{(host or ollama_client.DEFAULT_HOST)}. "
            "Start it with `ollama serve`, then pull a model "
            f"(e.g. `ollama pull {model or ollama_client.DEFAULT_MODEL}`)."
        )
        if args.as_json:
            report["ollama_error"] = msg
            return None
        print(f"\n[!] {msg}", file=sys.stderr)
        return None

    print("\n-- Ollama Reasoning --")
    print(f"Model: {model or ollama_client.DEFAULT_MODEL}")
    print()

    try:
        if args.stream and not args.as_json:
            chunks = ollama_client.reason(
                report, model=model, host=host, stream=True
            )
            parts: list[str] = []
            for piece in chunks:
                sys.stdout.write(piece)
                sys.stdout.flush()
                parts.append(piece)
            print()
            return "".join(parts)

        text = ollama_client.reason(report, model=model, host=host, stream=False)
        assert isinstance(text, str)
        if not args.as_json:
            print(text)
        return text
    except RuntimeError as exc:
        if args.as_json:
            report["ollama_error"] = str(exc)
            return None
        print(f"[!] {exc}", file=sys.stderr)
        return None


def process_one(number: str, args: argparse.Namespace) -> dict:
    report = analyze_number(number, region=args.region)

    if not args.as_json:
        print(format_report(report, color=not args.no_color))

    if args.ollama:
        analysis = run_ollama(report, args)
        if analysis is not None:
            report["ollama_analysis"] = analysis

    return report


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.quiet and not args.as_json:
        print_banner()

    if args.list_models:
        host = args.host
        if not ollama_client.is_available(host):
            print(
                f"[!] Ollama not reachable at {(host or ollama_client.DEFAULT_HOST)}",
                file=sys.stderr,
            )
            return 1
        models = ollama_client.list_models(host)
        if not models:
            print("No models found. Try: ollama pull llama3.2")
            return 0
        print("Available Ollama models:")
        for name in models:
            print(f"  - {name}")
        return 0

    # Batch mode
    if args.batch:
        try:
            with open(args.batch, encoding="utf-8") as fh:
                numbers = [
                    line.strip()
                    for line in fh
                    if line.strip() and not line.strip().startswith("#")
                ]
        except OSError as exc:
            print(f"[!] Cannot read batch file: {exc}", file=sys.stderr)
            return 1

        results = [process_one(n, args) for n in numbers]
        if args.as_json:
            print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0 if all(r.get("valid") or r.get("possible") for r in results) else 2

    # Single number: CLI arg or interactive
    number = args.number
    if not number:
        if not args.as_json:
            print("Include country code, e.g. Indian: +919874563210")
        try:
            number = input("Enter mobile number: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 130

    report = process_one(number, args)
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))

    if report.get("error"):
        return 1
    if not report.get("valid") and not report.get("possible"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
