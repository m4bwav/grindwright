"""Print the newest eval run's scores and each failed grader's evidence, one line each."""
import glob
import json

path = sorted(glob.glob("evals/results/*/aggregate-result.json"))[-1]
data = json.load(open(path, encoding="utf-8"))
print(path, data.get("costUsd"))
for case in data["cases"]:
    print(case["name"], "turns", case["maxTurns"], "with", case["aggregates"].get("with") if isinstance(case["aggregates"], dict) else "")
    for run in case["arms"]["with"][:3]:
        for grader in run["graders"]:
            if not grader["passed"]:
                print("  FAIL", grader["name"], "|", str(grader.get("evidence") or grader.get("explanation"))[:300].replace("\n", " "))
