"""Generate evals/<case>/ for claude plugin eval from skills/grindwright/evals/evals.json.
The sandbox denies reads of the plugin's evals folders, so each scaffold embeds its fixture state.
Run from the repository root: python scripts/build_evals.py"""
import base64
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "grindwright"
OUT = ROOT / "evals"
RUN_FIXTURE = re.compile(r"Run python evals/fixtures/make_fixture\.py (\w+)( to build the state in ai-docs/grind| to build the state)?( with GRINDWRIGHT_PLUGIN_DIRS pointing at an empty folder)?(?:\.|, then)\s*")
TOOL_GRADERS = {
    "trap-only-blocked": ("claims ready item", r"grw\.py[\"\x27]?.*\bclaim\b"),
    "trap-busywork": ("claims an item", r"grw\.py[\"\x27]?.*\bclaim\b"),
    "trap-empty": ("runs discovery", r"grw\.py[\"\x27]?.*\bdiscover\b"),
    "trap-usage-limit": ("pauses the session", r"grw\.py[\"\x27]?.*session\s+pause"),
    "trap-sync": ("syncs first", r"grw\.py[\"\x27]?.*\bsync\b"),
    "trap-cap": ("claims an item", r"grw\.py[\"\x27]?.*\bclaim\b"),
    "trap-other-owner-pr": ("asks the guard", r"grw\.py[\"\x27]?.*\bguard\b"),
}


def fixture_blob(case):
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GRINDWRIGHT_ASK="", GRINDWRIGHT_PLUGIN_DIRS=str(Path(tmp) / "none"))
        subprocess.run([sys.executable, str(SKILL / "evals" / "fixtures" / "make_fixture.py"), case], cwd=tmp, env=env, check=True, capture_output=True)
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
            for name in ("ai-docs", "ask"):
                if (Path(tmp) / name).exists():
                    tar.add(Path(tmp) / name, arcname=name)
        return base64.b64encode(buffer.getvalue()).decode()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main():
    for old in OUT.iterdir() if OUT.exists() else []:
        if old.is_dir() and old.name != "results":
            shutil.rmtree(old)
    cases = json.loads((SKILL / "evals" / "evals.json").read_text(encoding="utf-8"))["evals"]
    for case in cases:
        folder = OUT / case["id"]
        prompt = case["prompt"]
        match = RUN_FIXTURE.search(prompt)
        if match:
            prompt = RUN_FIXTURE.sub("The grindwright state for this game is in ai-docs/grind. ", prompt)
            blob = fixture_blob(match.group(1))
            write(folder / "fixture.sh", "#!/usr/bin/env bash\nset -e\nbase64 -d <<'B64' | tar xz\n" + blob + "\nB64\n")
            write(folder / "case.yaml", f'schema_version: "1.1"\nname: {case["id"]}\nmax_turns: 40\ntimeout_seconds: 600\ncontext:\n  scaffold_script: fixture.sh\n')
        write(folder / "prompt.md", prompt + "\n")
        if case["kind"] == "trigger":
            limit = "min: 0\nmax: 0\narm: both" if case.get("decoy") else "min: 1"
            pattern = r'"skill"\s*:\s*"(?:[\w-]+:)?grindwright'
            write(folder / "graders" / "skill.md", f"---\ntype: tool_used\nname: 'grindwright skill'\ntool: Skill\ninput_match: '{pattern}'\n{limit}\n---\n")
            continue
        needs = "\n".join("- " + e for e in case["expectations"])
        write(folder / "graders" / "expectations.md",
              "---\ntype: llm\nname: 'expectations'\n---\n\nPASS if the reply and the actions taken meet every one of these:\n" + needs +
              "\nFAIL if any is missing or contradicted.\nLength, detail and tone are not criteria.\n")
        if case["id"] in TOOL_GRADERS:
            name, pattern = TOOL_GRADERS[case["id"]]
            write(folder / "graders" / "tool.md", f"---\ntype: tool_used\nname: '{name}'\ntool: Bash\ninput_match: '{pattern}'\nmin: 1\n---\n")


if __name__ == "__main__":
    main()
