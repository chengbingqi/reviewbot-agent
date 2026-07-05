import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TypedDict


class ToolResult(TypedDict):
    tool: str
    status: str
    returncode: int | None
    stdout: str
    stderr: str
    message: str


def _run_tool(command: list[str], timeout_seconds: int) -> ToolResult:
    tool_name = command[0]
    if shutil.which(tool_name) is None:
        return {
            "tool": tool_name,
            "status": "skipped",
            "returncode": None,
            "stdout": "",
            "stderr": "",
            "message": f"{tool_name} is not installed or not on PATH.",
        }

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "tool": tool_name,
            "status": "failed",
            "returncode": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "message": f"{tool_name} timed out after {timeout_seconds} seconds.",
        }
    except OSError as exc:
        return {
            "tool": tool_name,
            "status": "failed",
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "message": f"{tool_name} failed to start.",
        }

    status = "pass" if completed.returncode == 0 else "fail"
    return {
        "tool": tool_name,
        "status": status,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "message": f"{tool_name} finished with return code {completed.returncode}.",
    }


def scan_python_code(code: str, timeout_seconds: int = 20) -> dict[str, ToolResult]:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".py", delete=False, encoding="utf-8"
        ) as temp_file:
            temp_file.write(code)
            temp_path = Path(temp_file.name)

        return {
            "ruff": _run_tool(["ruff", "check", str(temp_path)], timeout_seconds),
            "bandit": _run_tool(["bandit", "-q", "-f", "txt", str(temp_path)], timeout_seconds),
        }
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _safe_relative_path(path: str) -> Path:
    candidate = Path(path.replace("\\", "/"))
    safe_parts = [
        part
        for part in candidate.parts
        if part not in {"", ".", ".."} and not part.endswith(":")
    ]
    return Path(*safe_parts) if safe_parts else Path("snippet.py")


def _rewrite_temp_paths(result: ToolResult, temp_dir: Path) -> ToolResult:
    prefix = str(temp_dir)
    rewritten = result.copy()
    for key in ("stdout", "stderr"):
        rewritten[key] = rewritten[key].replace(prefix + "\\", "").replace(prefix + "/", "")
    return rewritten


def scan_python_files(
    files: list[dict[str, str]], timeout_seconds: int = 20
) -> dict[str, ToolResult]:
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        wrote_any = False
        for item in files:
            rel_path = _safe_relative_path(item["path"])
            if rel_path.suffix != ".py":
                rel_path = rel_path.with_suffix(".py")
            target = temp_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item["content"], encoding="utf-8")
            wrote_any = True

        if not wrote_any:
            return {
                "ruff": {
                    "tool": "ruff",
                    "status": "skipped",
                    "returncode": None,
                    "stdout": "",
                    "stderr": "",
                    "message": "No Python files were provided.",
                },
                "bandit": {
                    "tool": "bandit",
                    "status": "skipped",
                    "returncode": None,
                    "stdout": "",
                    "stderr": "",
                    "message": "No Python files were provided.",
                },
            }

        return {
            "ruff": _rewrite_temp_paths(
                _run_tool(["ruff", "check", str(temp_dir)], timeout_seconds), temp_dir
            ),
            "bandit": _rewrite_temp_paths(
                _run_tool(["bandit", "-q", "-r", "-f", "txt", str(temp_dir)], timeout_seconds),
                temp_dir,
            ),
        }
