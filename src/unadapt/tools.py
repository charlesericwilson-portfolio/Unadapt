import subprocess
import time

from langchain_core.tools import tool
from unadapt.safety import is_command_safe
from unadapt.memory import SemanticMemory
from unadapt.config import load_config

config = load_config("config.toml")

memory = SemanticMemory(config)

SESSION_POLL_INTERVAL_SECONDS = 0.5
SESSION_FOREGROUND_TIMEOUT_SECONDS = 30

@tool
def terminal(command: str) -> str:
    """Execute a shell command in the terminal and return its output."""

    safe, reason = is_command_safe(
        command,
        config.safety.denylist,
    )

    if not safe:
        return f"Safety block: {reason}"

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

    safe, reason = is_command_safe(
        command,
        config.safety.denylist,
    )

    if not safe:
        return f"Safety block: {reason}"

    exists = subprocess.run(
        ["tmux", "has-session", "-t", name],
        capture_output=True,
    )

    if exists.returncode != 0:
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", name],
            check=True,
        )

    marker_id = time.time_ns()

    marker_start = f"===UNADAPT_START_{marker_id}==="
    marker_end = f"===UNADAPT_END_{marker_id}==="

    # Start marker
    subprocess.run(
        [
            "tmux",
            "send-keys",
            "-t",
            name,
            f"echo '{marker_start}'",
            "Enter",
        ],
        check=True,
    )

    time.sleep(0.2)

    # Actual command
    subprocess.run(
        [
            "tmux",
            "send-keys",
            "-t",
            name,
            command.strip(),
            "Enter",
        ],
        check=True,
    )

    time.sleep(0.2)

    # End marker
    subprocess.run(
        [
            "tmux",
            "send-keys",
            "-t",
            name,
            f"echo '{marker_end}'",
            "Enter",
        ],
        check=True,
    )

    started = time.monotonic()

    while True:
        result = subprocess.run(
            [
                "tmux",
                "capture-pane",
                "-p",
                "-S",
                "-",
                "-t",
                name,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        lines = result.stdout.splitlines()

        # Search backward for this invocation's END marker.
        end_index = None

        for index in range(len(lines) - 1, -1, -1):
            if lines[index].strip() == marker_end:
                end_index = index
                break

        if end_index is not None:
            # Search backward from END for this invocation's START marker.
            start_index = None

            for index in range(end_index - 1, -1, -1):
                if lines[index].strip() == marker_start:
                    start_index = index
                    break

            if start_index is not None:
                output = "\n".join(
                    lines[start_index + 1:end_index]
                ).strip()

                if not output:
                    output = "(command completed with no output)"

                return output

        if (
            time.monotonic() - started
            >= SESSION_FOREGROUND_TIMEOUT_SECONDS
        ):
            return (
                f"SESSION '{name}' command is still running after "
                f"{SESSION_FOREGROUND_TIMEOUT_SECONDS} seconds."
            )

        time.sleep(SESSION_POLL_INTERVAL_SECONDS)


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

@tool
def append_memory(
    category: str,
    content: str,
) -> str:
    """
    Save important information to long-term semantic memory.

    Use this when information should be remembered across
    conversations or future tasks.
    """

    return memory.append(
        category=category,
        content=content,
    )


@tool
def read_memory(
    query: str,
    limit: int = 5,
) -> str:
    """
    Search long-term semantic memory for information relevant
    to the current task.

    Use this when past information may help answer the user
    or complete the current task.
    """

    return memory.read(
        query=query,
        limit=limit,
    )
