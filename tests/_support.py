"""Shared test fixtures.

A throwaway tools directory holds git-committed stand-in rulesets, so the
prompt-track harnesses run offline and in CI without the pinned upstream
clones. No test reads the repository's .env or reaches the network: the
harnesses' key file is pointed at a temporary path and urlopen is replaced
by a fake in every test that could call it.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAKE_KEY = "sk-ant-TESTONLY-not-a-real-key"

FAKE_TOOLS = Path(tempfile.mkdtemp(prefix="registerbench-tools-"))
_RULESETS = {
    "stop-slop": ["SKILL.md", "references/phrases.md",
                  "references/structures.md", "references/examples.md"],
    "no-ai-slop": ["SKILL.md", "eval.md"],
    "the-antislop": ["SKILL.md"],
    "avoid-ai-writing": ["SKILL.md"],
}


def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid",
                    *args], cwd=cwd, check=True, capture_output=True)


for _repo, _files in _RULESETS.items():
    _d = FAKE_TOOLS / _repo
    for _rel in _files:
        (_d / _rel).parent.mkdir(parents=True, exist_ok=True)
        (_d / _rel).write_text(f"# {_repo} {_rel}\nStand-in ruleset for tests.\n", encoding="utf-8")
    _git(_d, "init", "-q")
    _git(_d, "add", ".")
    _git(_d, "commit", "-q", "-m", "fixture")

os.environ["REGISTERBENCH_TOOLS_DIR"] = str(FAKE_TOOLS)
os.environ.pop("REGISTERBENCH_API_KEY", None)
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, str(REPO / "runners" / "prompt_track"))

import run_prompt_batch as rb  # noqa: E402
import run_prompt_tool as rt  # noqa: E402


def load_score():
    """Import scripts/score.py as a module. It reads the register from argv at
    import time, so argv is pinned while it loads."""
    saved = sys.argv
    sys.argv = ["score.py", "finance-audit"]
    try:
        spec = importlib.util.spec_from_file_location("registerbench_score", REPO / "scripts" / "score.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.argv = saved
    return mod


class FakeResponse:
    def __init__(self, payload, raw=False):
        self.body = payload if raw else json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.body


def refuse_network(req, timeout=None):
    raise AssertionError(f"unexpected network call to {req.full_url}")
