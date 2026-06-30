# self-audit

[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)]()

Text-level consistency audit for AI output. Checks four dimensions against regex patterns — zero dependencies, stdlib only. **Not a correctness verifier.** It catches self-contradictions and ungrounded claims, not logic bugs.

## Install

```bash
pip install git+https://github.com/gategrow/self-audit.git
```

## Usage

```bash
# Pipe mode
cat agent_output.txt | self-audit --verbose

# Inline mode
self-audit --text "The bug is fixed. Should work. Ready." --requirements "fix bug" "add tests"

# File mode with JSON
self-audit --file response.txt --json

# Check version
self-audit --version
```

## What it checks

| Dimension | Question | Method |
|-----------|----------|--------|
| Completeness | Did I answer everything? | Substring match against requirements |
| Consistency | Did I contradict myself? | Regex: claims vs evidence mismatch |
| Groundedness | Did I show evidence? | Regex: hedging, speculation patterns |
| Honesty | Am I honest about limits? | Regex: over-claiming, unverified assertions |

## Limitations

- **Not a correctness check** — it doesn't run code, execute tests, or verify outputs against ground truth
- **Regex only** — catches surface-level patterns (contradictions, hedging, unverified claims), not deep semantic issues
- **No LLM** — cannot understand context or intent. A statement like "this should work" with no verification will be flagged regardless of whether it actually does work

## Exit codes

- `0` — All four pass
- `1` — At least one failed

## License

MIT