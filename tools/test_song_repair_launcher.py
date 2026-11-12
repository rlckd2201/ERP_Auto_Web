"""Run the compiled recovery launcher with harmless PowerShell fixtures.

The real script is executed only with a deliberately invalid PC/user identity,
so the target guard must reject it before any repair or registry operation.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def run_launcher(exe, outputs):
    args = [str(exe), "--no-pause"]
    for folder in outputs:
        args += ["--output-dir", str(folder)]
    env = dict(os.environ, COMPUTERNAME="TEST-NOT-SONG", USERNAME="TEST-NOT-SONG")
    run = subprocess.run(args, env=env, capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=45)
    files = list(outputs[-1].glob("*.json"))
    check(len(files) == 1, f"Expected one result JSON; exit={run.returncode}; output={run.stdout} {run.stderr}")
    report = json.loads(files[0].read_text(encoding="utf-8-sig"))
    check(report["launcher_version"] == 2, "Wrong launcher version")
    check(Path(report["result_file"]) == files[0], "Reported result location differs")
    check(Path(report["log_file"]).is_file(), "Execution log missing")
    return run, report, Path(report["log_file"]).read_text(encoding="utf-8-sig")


def fixture_exe(folder, source, package):
    folder.mkdir(parents=True)
    script = folder / "repair.ps1"
    script.write_text(source, encoding="utf-8-sig")
    compiler = Path(os.environ["SystemRoot"]) / "Microsoft.NET/Framework64/v4.0.30319/csc.exe"
    exe = folder / "fixture.exe"
    args = [str(compiler), "/nologo", "/target:exe", "/r:System.Web.Extensions.dll",
            f"/out:{exe}", f"/resource:{script},repair.ps1",
            f"/resource:{package / 'resources/repair-common.ps1'},repair-common.ps1",
            f"/resource:{package / 'resources/server105-trust.pem'},server105-trust.pem",
            str(ROOT / "tools/AccountingWebSongRepair.cs")]
    run = subprocess.run(args, capture_output=True, text=True, timeout=30)
    check(run.returncode == 0, run.stdout + run.stderr)
    return exe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    package = args.package.resolve()
    workspace = Path(tempfile.mkdtemp(prefix="song_launcher_test_"))
    passed = []
    actual = package / "AccountingWebSongRepair.exe"

    run, report, log = run_launcher(actual, [workspace / "실행 결과's"])
    check(run.returncode == 1 and report["status"] == "needs_support", "Real entry did not fail closed")
    check(report["repair_version"] == 2 and report["computer"] == "TEST-NOT-SONG"
          and report["user"] == "TEST-NOT-SONG", "Real PowerShell entry did not run")
    check("only for" in report["error"] and report["steps"] == [], "Wrong identity reached repair steps")
    check("송명학" in log and "결과 파일:" in log, "Korean child output was not captured")
    passed.append("real EXE -> PowerShell5.1 -> common library -> target guard -> JSON/log, Unicode paths")

    fixtures = {
        "early_zero_exit": "param([string]$ResultPath)\nWrite-Output 'EARLY_RETURN'; exit 0\n",
        "nonzero_exit": "param([string]$ResultPath)\nWrite-Error 'FIXTURE_ERROR'; exit 17\n",
        "parse_error": "param([string]$ResultPath)\nif (\n",
        "dependency_failure": "param([string]$ResultPath)\n$ErrorActionPreference='Stop'\n. (Join-Path $PSScriptRoot 'absent-library.ps1')\n",
    }
    for name, source in fixtures.items():
        exe = fixture_exe(workspace / name, source, package)
        run, report, log = run_launcher(exe, [workspace / name / "results"])
        check(run.returncode != 0 and report["status"] == "needs_support", f"{name} falsely succeeded")
        check("before completing" in report["error"] and len(log) > 20, f"{name} left no failure evidence")
        check("\ufffd" not in log, f"{name} corrupted startup error text")
        if name == "early_zero_exit":
            check(report["powershell_exit_code"] == 0 and "EARLY_RETURN" in log, "Old early-return failure not detected")
        if name == "nonzero_exit":
            check(report["powershell_exit_code"] == 17 and "FIXTURE_ERROR" in log, "Child failure lost")
        passed.append(name + " retains JSON and execution log")

    source = """param([string]$ResultPath)
@{repair_version=2;status='fixture_completed';completed_at=(Get-Date -Format o);steps=@()} | ConvertTo-Json | Set-Content -LiteralPath $ResultPath -Encoding UTF8
exit 0
"""
    exe = fixture_exe(workspace / "complete", source, package)
    run, report, _ = run_launcher(exe, [workspace / "complete/results"])
    check(run.returncode == 0 and report["status"] == "fixture_completed", "Completed child report overwritten")
    passed.append("completed child report preserved")

    blocked = workspace / "not_a_directory"
    blocked.write_text("fixture", encoding="utf-8")
    run, report, _ = run_launcher(actual, [blocked, workspace / "fallback"])
    check(run.returncode == 1 and report["repair_version"] == 2, "Fallback lost real entry result")
    check(len(report["output_fallback_errors"]) == 1, "Preferred-folder failure not recorded")
    passed.append("unwritable preferred folder falls back with recorded reason")

    for name in passed:
        print("PASS " + name)
    result = {"passed": len(passed), "cases": passed, "evidence_directory": str(workspace),
              "repair_executed": False, "target_identity_deliberately_invalid": True}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"All {len(passed)} compiled-launcher tests passed; no PC repair performed.")


if __name__ == "__main__":
    main()
