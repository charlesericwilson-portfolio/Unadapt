import subprocess
import time

from langchain_core.tools import tool


@tool
def terminal(command: str) -> str:
    """Execute a shell command in the terminal and return its output."""

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout

        if result.stderr:
            output += result.stderr

        if not output:
            output = "(command completed with no output)"

        return output

    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."

@tool
def session(name: str, command: str) -> str:
    """Execute a command in a persistent named tmux session."""

    exists = subprocess.run(
        ["tmux", "has-session", "-t", name],
        capture_output=True,
    )

    if exists.returncode != 0:
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", name],
            check=True,
        )

    subprocess.run(
        ["tmux", "send-keys", "-t", name, command, "Enter"],
        check=True,
    )

    time.sleep(1)

    result = subprocess.run(
        ["tmux", "capture-pane", "-p", "-t", name],
        capture_output=True,
        text=True,
        check=True,
    )

    return result.stdout


@tool
def end_session(name: str) -> str:
    """Terminate a persistent named tmux session."""

    result = subprocess.run(
        ["tmux", "kill-session", "-t", name],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return result.stderr or f"Session '{name}' does not exist."

    return f"Session '{name}' terminated."
