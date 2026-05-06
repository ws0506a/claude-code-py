"""Shell execution tool."""
import subprocess
from ..confirm import confirm

_TIMEOUT = 60


def execute_shell(command: str, timeout: int = _TIMEOUT) -> str:
    detail = f"$ {command}\ntimeout: {timeout}s"
    if not confirm("execute_shell", detail):
        return "User declined to run the command."
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s."
    except Exception as e:
        return f"Error: {e}"
    parts = [f"exit_code: {result.returncode}"]
    if result.stdout:
        parts.append(f"stdout:\n{result.stdout}")
    if result.stderr:
        parts.append(f"stderr:\n{result.stderr}")
    return "\n".join(parts)
