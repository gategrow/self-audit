"""Tests for self_audit.cli — one test class per dimension.

Run:
    python -m pytest tests/ -v
    python tests/test_cli.py  # lightweight: just runs the test functions directly
"""
from __future__ import annotations

import sys
import os

# Allow running as script without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from self_audit.cli import check_completeness, check_consistency, check_groundedness, check_honesty


# ── Completeness ─────────────────────────────────────────────────────────────
# NOTE: check_completeness uses raw substring matching (r.lower() in text.lower()).
# Test requirements must appear as contiguous substrings in the test text.

class TestCompleteness:
    """Requirement coverage detection via substring matching."""

    def test_all_requirements_present(self):
        text = "fix bug #123 and add tests for auth module"
        result = check_completeness(text, ["fix bug", "add tests"])
        assert result["passed"] is True, f"Expected pass, got {result}"
        assert result["issues"] == [], f"Expected no issues, got {result['issues']}"

    def test_missing_requirement(self):
        text = "I fix bug #42."
        result = check_completeness(text, ["fix bug", "add tests"])
        assert result["passed"] is False
        assert "add tests" in result["issues"]

    def test_empty_requirements(self):
        text = "Any text here."
        result = check_completeness(text, [])
        assert result["passed"] is True
        assert result["issues"] == []

    def test_case_insensitive_match(self):
        text = "Fix BUG and ADD tests"
        result = check_completeness(text, ["fix bug", "add tests"])
        assert result["passed"] is True

    def test_partial_word_match(self):
        """Substring match: 'test' is a substring of 'testing'."""
        text = "Added testing infrastructure."
        result = check_completeness(text, ["test"])
        assert result["passed"] is True, f"'test' should match substring in 'testing', got {result}"


# ── Consistency ──────────────────────────────────────────────────────────────

class TestConsistency:
    """Internal contradiction detection."""

    def test_no_changes_needed_but_edit(self):
        text = "No changes needed here. Let me edit the file to fix the bug."
        result = check_consistency(text)
        assert not result["passed"], f"Should detect contradiction, got {result}"

    def test_all_pass_with_exceptions(self):
        text = "All tests passed except the integration test."
        result = check_consistency(text)
        assert not result["passed"]

    def test_didnt_change_but_modified(self):
        text = "I haven't changed the config file, just modified the logging level."
        result = check_consistency(text)
        assert not result["passed"], f"Expected fail for 'haven't change... modified': {result}"

    def test_already_done_but_editing(self):
        text = "This was already fixed in the previous PR. Let me add error handling."
        result = check_consistency(text)
        assert not result["passed"], f"Expected fail for 'already fixed... add': {result}"

    def test_simple_change_but_refactor(self):
        text = "Just a simple fix — I'll refactor the whole auth module."
        result = check_consistency(text)
        assert not result["passed"]

    def test_consistent_text_passes(self):
        text = "Added error handling to the login function. The tests cover the new error paths."
        result = check_consistency(text)
        assert result["passed"], f"Consistent text should pass, got {result['issues']}"

    def test_only_one_change_with_second_edit(self):
        text = "Only one change needed. The second edit is just formatting."
        result = check_consistency(text)
        assert not result["passed"], f"Expected fail for 'only one change... second edit': {result}"


# ── Groundedness ─────────────────────────────────────────────────────────────

class TestGroundedness:
    """Speculative/unverified claim detection."""

    def test_should_work(self):
        text = "This should work now."
        result = check_groundedness(text)
        assert not result["passed"]

    def test_probably_fine(self):
        text = "It's probably fine."
        result = check_groundedness(text)
        assert not result["passed"]

    def test_i_think_its_correct(self):
        text = "I think this is correct now."
        result = check_groundedness(text)
        assert not result["passed"]

    def test_in_theory(self):
        text = "In theory this should handle all edge cases."
        result = check_groundedness(text)
        assert not result["passed"]

    def test_seems_to_work(self):
        text = "The fix seems to work."
        result = check_groundedness(text)
        assert not result["passed"]

    def test_grounded_text_passes(self):
        text = "I ran pytest and all 14 tests passed. The output confirms the fix."
        result = check_groundedness(text)
        assert result["passed"], f"Grounded text should pass, got {result['issues']}"

    def test_likely_works(self):
        text = "This likely works because I tested it."
        result = check_groundedness(text)
        assert not result["passed"]


# ── Honesty ──────────────────────────────────────────────────────────────────

class TestHonesty:
    """Over-claiming / false confidence detection."""

    def test_verified_without_actually_running(self):
        text = "I've verified the fix without actually running the tests."
        result = check_honesty(text)
        assert not result["passed"], f"Should detect unverified verification, got {result}"

    def test_production_ready_with_todos(self):
        text = "This is production ready. TODO: add error handling."
        result = check_honesty(text)
        assert not result["passed"]

    def test_works_on_my_machine(self):
        text = "The build passes — works on my machine."
        result = check_honesty(text)
        assert not result["passed"], f"Should flag 'works on my machine': {result}"

    def test_couldnt_reproduce_no_details(self):
        text = "I couldn't reproduce the bug."
        result = check_honesty(text)
        assert not result["passed"], f"Should flag unreproducible without details: {result}"

    def test_couldnt_reproduce_with_details_passes(self):
        text = "I couldn't reproduce the bug. Log shows timeout at line 42, stack trace attached."
        result = check_honesty(text)
        assert result["passed"], f"Reproduce with details should pass: {result['issues']}"

    def test_i_read_file_without_citing(self):
        text = "I've reviewed the code and it looks fine."
        result = check_honesty(text)
        assert not result["passed"], f"Should flag file review without citing content: {result}"

    def test_i_read_file_with_citation_passes(self):
        text = "I've reviewed the code. The function parse_input at line 42 validates all args."
        result = check_honesty(text)
        assert result["passed"], f"File review with citation should pass: {result['issues']}"

    def test_manually_tested_without_details(self):
        text = "I manually tested the feature."
        result = check_honesty(text)
        assert not result["passed"], f"Should flag manual test without procedure: {result}"

    def test_honest_text_passes(self):
        text = "I ran pytest tests/test_auth.py -v. All 14 tests passed. Build log: https://ci.example.com/42"
        result = check_honesty(text)
        assert result["passed"], f"Honest text should pass, got {result['issues']}"


# ── Integration ──────────────────────────────────────────────────────────────

class TestIntegration:
    """Combined scenarios."""

    def test_clean_output_passes_all(self):
        text = """I fix bug by adding a 5s timeout to the HTTP client.
I ran pytest tests/ -v and all 23 tests passed.
Output confirms: 23 passed in 1.42s.
The error was at auth.py line 47 where requests.get(url) had no timeout parameter."""
        requirements = ["fix bug", "pytest"]
        r = {
            "completeness": check_completeness(text, requirements),
            "consistency": check_consistency(text),
            "groundedness": check_groundedness(text),
            "honesty": check_honesty(text),
        }
        all_pass = all(d["passed"] for d in r.values())
        assert all_pass, f"Clean output should pass all dimensions: {r}"

    def test_sloppy_output_fails_multiple(self):
        text = """I think this should work. No changes needed.
I already fixed everything. Just a simple change.
It's production ready. TODO: write tests.
Works on my machine."""
        r = {
            "consistency": check_consistency(text),
            "groundedness": check_groundedness(text),
            "honesty": check_honesty(text),
        }
        failed = [dim for dim, result in r.items() if not result["passed"]]
        assert len(failed) >= 2, f"Sloppy output should fail >=2 dimensions, failed: {failed}"


if __name__ == "__main__":
    # Lightweight runner — no pytest required
    import traceback

    total = passed = failed = 0
    for name, obj in list(globals().items()):
        if name.startswith("Test") and isinstance(obj, type):
            for attr in dir(obj):
                if attr.startswith("test_"):
                    total += 1
                    try:
                        getattr(obj(), attr)()
                        passed += 1
                        print(f"  PASS  {name}.{attr}")
                    except Exception as e:
                        failed += 1
                        print(f"  FAIL  {name}.{attr}: {e}")

    print(f"\n{passed}/{total} passed" + (f", {failed} failed" if failed else ""))
    sys.exit(1 if failed else 0)
