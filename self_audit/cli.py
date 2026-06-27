#!/usr/bin/env python3
"""Self-audit CLI: four-dimension quality check for AI output.

Usage:
    self-audit --text "response" --requirements "fix bug" "add tests"
    cat response.txt | self-audit --verbose
    self-audit --file response.txt --json
    self-audit --version
"""
import argparse
import json
import re
import sys

from self_audit import __version__


def check_completeness(text, requirements):
    missing = [r for r in requirements if r.lower() not in text.lower()]
    return {"passed": len(missing) == 0, "issues": missing}


def check_consistency(text):
    patterns = [
        (r'(?:no\s+changes?\s+needed|nothing\s+to\s+change|looks?\s+good).{0,100}(?:edit|write|modify)',
         "Claims no changes needed but editing occurred"),
        (r'(?:all|everything).{0,50}(?:pass(?:es|ed)?|works?|done).{0,50}(?:except|but|however|although)',
         "Claims all pass with exceptions"),
    ]
    findings = [d for p, d in patterns if re.search(p, text, re.IGNORECASE)]
    return {"passed": len(findings) == 0, "issues": findings}


def check_groundedness(text):
    patterns = [
        r'(?:should|ought\s+to|probably)\s+work',
        r'(?:should|ought\s+to|probably)\s+be\s+fine',
        r'(?:should|ought\s+to|probably)\s+pass',
        r'(?:I|we)\s+(?:think|believe|assume)\s+(?:it|this|that)\s+(?:works?|is?\s+correct|is?\s+ready)',
    ]
    findings = []
    for p in patterns:
        findings.extend(re.findall(p, text, re.IGNORECASE)[:3])
    return {"passed": len(findings) == 0, "issues": findings}


def check_honesty(text):
    patterns = [
        r"I'?ve?\s+(?:verified|tested|checked|confirmed).{0,50}(?:without|but|however).{0,30}(?:actual(?:ly)?|really|running)",
        r'(?:production\s*ready|battle\s*tested|rock\s*solid).{0,100}(?:TODO|FIXME|stub|placeholder)',
    ]
    findings = []
    for p in patterns:
        findings.extend(re.findall(p, text, re.IGNORECASE)[:2])
    return {"passed": len(findings) == 0, "issues": findings}


def main():
    p = argparse.ArgumentParser(description="Four-dimension AI output quality audit")
    p.add_argument("--text", help="Text to audit")
    p.add_argument("--file", help="File to audit")
    p.add_argument("--requirements", nargs="*", default=[], help="Expected requirements")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    p.add_argument("--verbose", action="store_true", help="Show suggestions")
    p.add_argument("--version", action="version", version=f"self-audit {__version__}")
    args = p.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = sys.stdin.read()

    if not text.strip():
        print("ERROR: No text provided", file=sys.stderr)
        sys.exit(1)

    results = {
        "completeness": check_completeness(text, args.requirements),
        "consistency": check_consistency(text),
        "groundedness": check_groundedness(text),
        "honesty": check_honesty(text),
    }

    all_pass = all(r["passed"] for r in results.values())

    if args.json:
        print(json.dumps({"passed": all_pass, "dimensions": results}, indent=2))
    else:
        for dim, result in results.items():
            status = "OK" if result["passed"] else "FIXED"
            detail = ""
            if args.verbose and not result["passed"] and result["issues"]:
                detail = f"  [{result['issues'][0]}]"
            print(f"{dim.capitalize():15s}: {status}{detail}")
        print(f"\n{'PASS' if all_pass else 'FAIL'}")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
