import re


DESTRUCTIVE_PRIMITIVES = {
    "mkfs",
    "wipefs",
    "shred",
    "fdisk",
    "parted",
    "dd",
    "rm",
}


def is_command_safe(command: str, denylist: list[str]) -> tuple[bool, str | None]:
    """
    Check a shell command against UNADAPT's basic safety policy.

    Returns:
        (True, None) if allowed.
        (False, reason) if blocked.
    """

    lower_command = command.lower()

    # Layer 1:
    # Direct denylist substring matching.
    for blocked in denylist:
        if blocked.lower() in lower_command:
            return False, f"Command contains blocked pattern: {blocked}"

    # Layer 2:
    # Remove common characters used for basic command obfuscation.
    normalized = re.sub(r"""['"\\$()]""", "", lower_command)

    # Layer 3:
    # Inspect chained commands independently.
    #
    # Handles things such as:
    # command1 && command2
    # command1 || command2
    # command1 ; command2
    # command1 | command2
    # multi-line commands
    subcommands = re.split(r"[;&|\n]+", command)

    for raw_subcommand in subcommands:
        subcommand = raw_subcommand.strip()

        if not subcommand:
            continue

        try:
            import shlex

            tokens = shlex.split(subcommand)
        except ValueError:
            tokens = subcommand.split()

        if not tokens:
            continue

        executable = tokens[0].lower()

        # Direct executable denylist check.
        for blocked in denylist:
            if executable == blocked.lower():
                return (
                    False,
                    f"Chained subcommand '{tokens[0]}' is blocked by safety policy.",
                )

        # Destructive executable check.
        if executable in DESTRUCTIVE_PRIMITIVES:
            return (
                False,
                f"Destructive binary '{tokens[0]}' blocked in command chain.",
            )

    # Layer 4:
    # Catch simple attempts to disguise destructive binaries.
    for primitive in DESTRUCTIVE_PRIMITIVES:
        patterns = (
            f"{primitive} ",
            f"{primitive}-",
            f"{primitive}/",
        )

        if any(pattern in normalized for pattern in patterns):
            return (
                False,
                f"Obfuscated execution of '{primitive}' detected.",
            )

        if normalized.endswith(primitive):
            return (
                False,
                f"Obfuscated execution of '{primitive}' detected.",
            )

    return True, None
