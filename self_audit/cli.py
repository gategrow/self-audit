#!/usr/bin/env python3
"""Self-audit CLI: four-dimension quality check for AI output.

Usage:
    self-audit --text "response" --requirements "fix bug" "add tests"
    cat response.txt | self-audit --verbose
    self-audit --file response.txt --json
    self-audit --version
"""
from __future__ import annotations

import argparse
import json
import re
import sys

try:
    from self_audit import __version__
except ImportError:
    __version__ = "unknown"


def check_completeness(text, requirements):
    missing = [r for r in requirements if r.lower() not in text.lower()]
    return {"passed": len(missing) == 0, "issues": missing}


def check_consistency(text):
    """Detect internal contradictions: claims that are undermined by evidence in the same text.

    Each (pattern, description) pair catches a specific contradiction class.
    """
    patterns = [
        # Claims no changes but evidence of edits
        (r'(?:no\s+changes?\s+needed|nothing\s+to\s+change|looks?\s+good).{0,100}(?:edit|write|modify)',
         "Claims no changes needed but editing occurred"),
        # "All pass except X" — the qualifier contradicts "all"
        (r'(?:all|everything).{0,50}(?:pass(?:es|ed)?|works?|done).{0,50}(?:except|but|however|although)',
         "Claims all pass with exceptions"),
        # "Didn't change X" followed by editing X
        (r"(?:didn['’]t|haven['’]t|hasn['’]t)\s+(?:change|modify|touch|alter).{0,200}(?:edit|write|modify)",
         "Claims nothing was changed but editing occurred"),
        # "Only/JUST one change" but context shows multiple edits
        (r'(?:only|just|single)\s+(?:one\s+)?(?:change|edit|fix|line).{0,200}(?:(?:second|another|also|additional)\s+(?:change|edit|fix))',
         "Claims single change but another edit is mentioned"),
        # "Already done/fixed" but still performing edits
        (r'(?:already|previously)\s+(?:done|fixed|handled|implemented|addressed).{0,200}(?:edit|write|add|modify)',
         "Claims already done but still making edits"),
        # "Simple/trivial change" but description reveals complexity
        (r'(?:simple|trivial|minor|small|quick)\s+(?:change|fix|edit|patch).{0,200}(?:refactor|rewrite|restructure|overhaul)',
         "Downplays change as simple but refactor/rewrite mentioned"),
    ]
    findings = [d for p, d in patterns if re.search(p, text, re.IGNORECASE)]
    return {"passed": len(findings) == 0, "issues": findings}


def check_groundedness(text):
    """Detect speculative, ungrounded claims — reasoning that lacks evidence."""
    patterns = [
        # Hedge + success claim (no evidence)
        r'(?:should|ought\s+to|probably)\s+work',
        r'(?:should|ought\s+to|probably)\s+be\s+fine',
        r'(?:should|ought\s+to|probably)\s+pass',
        # Belief-based conclusion without verification
        r'(?:I|we)\s+(?:think|believe|assume)\s+(?:it|this|that)\s+(?:works?|is?\s+correct|is?\s+ready)',
        # Theoretical reasoning without empirical check
        r'(?:in\s+theory|theoretically|on\s+paper)\s.{0,50}(?:should|would|could|ought)',
        # Vague "seems/appears" without specifics
        r'(?:seems?\s+to\s+(?:be\s+)?|appears?\s+to\s+(?:be\s+)?)(?:work(?:ing)?|fine|correct|ready|good|ok)',
        # "Probably/likely" without qualification
        r'(?:probably|likely|most\s+likely)\s+(?:works?|fine|correct|ready|done|solved)',
    ]
    findings = []
    for p in patterns:
        findings.extend(re.findall(p, text, re.IGNORECASE)[:3])
    return {"passed": len(findings) == 0, "issues": findings}


def check_honesty(text):
    """Detect over-claiming: statements that assert verification or quality that the text itself undermines."""
    patterns = [
        # "I verified/tested" but admits not actually running/checking
        r"I'?ve?\s+(?:verified|tested|checked|confirmed).{0,50}(?:without|but|however).{0,30}(?:actual(?:ly)?|really|running)",
        # "Production ready" but TODOs/stubs still present
        r'(?:production\s*ready|battle\s*tested|rock\s*solid).{0,100}(?:TODO|FIXME|stub|placeholder)',
        # Classic dodge — "works on my machine"
        r'works?\s+(?:on|in)\s+(?:my|our)\s+(?:machine|computer|local|dev|environment)',
        # "Couldn't reproduce" with no investigation details
        r"(?:couldn['’]t|cannot|can['’]t)\s+reproduce.{0,200}(?!(?:log|trace|error|stack|debug|investigat|detail|specific))",
        # "I reviewed/read [file]" as verification but cites nothing from it
        r"I'?ve?\s+(?:read|reviewed|looked\s+at)\s+(?:the\s+)?(?:file|code|output|log|diff).{0,200}(?!(?:line|says|shows|contains|states|function|class|method|var|import|def))",
        # "Manually verified/tested" but no description of what was done
        r'(?:manually|by\s+hand)\s+(?:tested|verified|checked|confirmed).{0,200}(?!(?:step|procedure|process|how|method|way|ran?\s+|executed|opened|clicked))',
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
