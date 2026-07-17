# NumGather 2.0

Phone-number intelligence CLI for SecHunt-OS — country, carrier, number type, timezones, India MSC circle lookup, plus optional **Ollama** local-LLM reasoning.

## Features

| Capability | Description |
|---|---|
| Validation | Possible / valid checks via Google libphonenumber |
| Identity | Country, ISO region, country code, national number |
| Type | Mobile, fixed line, VoIP, toll-free, premium, … |
| Carrier | ISP / network name when available |
| Timezones | Likely timezone(s) for the number |
| Formats | E.164, international, national, RFC3966 |
| India MSC DB | Circle + operator from local prefix database |
| Rule insights | Portability hints, type notes, uncertainty flags |
| **Ollama** | Local LLM reasoning over the full report (incl. reasoning models) |
| Batch / JSON | File of numbers, machine-readable output |

## Install

**Linux / macOS**

```bash
git clone https://github.com/0xsh4n/NumGather.git
cd NumGather
chmod +x setup.sh
./setup.sh
# or: pip3 install -r requirements.txt
```

**Windows**

```bat
git clone https://github.com/0xsh4n/NumGather.git
cd NumGather
setup.bat
:: optional interactive run after install:
setup.bat --run
```

### Optional: Ollama (reasoning)

1. Install [Ollama](https://ollama.com)
2. Pull a model:

```bash
ollama pull llama3.2
# reasoning-oriented examples:
ollama pull deepseek-r1
ollama pull qwen2.5
```

3. Ensure the daemon is up (`ollama serve` if needed).

Environment overrides:

| Variable | Default | Meaning |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | API base URL |
| `OLLAMA_MODEL` | `llama3.2` | Default model |
| `OLLAMA_TIMEOUT` | `120` | Request timeout (seconds) |

## Usage

Always include the country prefix (`+<code>`).

```bash
# Interactive
python3 NumGather.py

# Direct lookup
python3 NumGather.py +919874512362

# Full intelligence + Ollama reasoning
python3 NumGather.py +14155552671 --ollama

# Reasoning model + streaming
python3 NumGather.py +919876543210 -o -m deepseek-r1 --stream

# JSON for scripts
python3 NumGather.py +447911123456 --json

# Batch file (one number per line; # comments ok)
python3 NumGather.py --batch numbers.txt -o

# List local Ollama models
python3 NumGather.py --list-models
```

### CLI flags

```
number                 Phone number (optional if interactive / --batch)
-r, --region REGION    Default region if no +country_code (IN, US, …)
-o, --ollama           Enable Ollama reasoning
-m, --model NAME       Ollama model name
--host URL             Ollama base URL
--stream               Stream LLM tokens
--list-models          Show models on Ollama host
-j, --json             JSON output
-b, --batch FILE       Analyze many numbers
--no-color             Disable ANSI colors
-q, --quiet            Skip banner
-V, --version          Print version
```

## Example output (structure)

Deterministic report covers validity, country/carrier, type, timezones, formats, India circle (when `+91`), and rule-based insights. With `-o`, Ollama adds a reasoned OSINT-style analysis grounded in those facts (no invented subscriber PII).

## Project layout

```
NumGather.py       CLI entry (v2.0)
lookup.py          Intelligence engine
ollama_client.py   Ollama chat / streaming client
areadatabase.py    India MSC prefix database
requirements.txt   Dependencies
setup.sh           Install helper (Unix)
setup.bat          Install helper (Windows)
```

## Notes

- Carrier names reflect numbering-plan / library data — **MNP** (portability) can make ISP differ from the original MSC prefix.
- Ollama never replaces validation; if Ollama is down, the deterministic report still prints.
- This tool does **not** perform live HLR dips or personal tracking.

## Credits

Made by **H1DD3N_SH4D0W** for SecHunt-OS · [GitHub](https://github.com/0xsh4n/NumGather)
