from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI


def build_summarizer(config, max_tokens: int):
    return ChatOpenAI(
        model=config.summarizer.model,
        base_url=config.summarizer.base_url,
        api_key=config.summarizer.api_key,
        temperature=0.2,
        max_tokens=max_tokens,
    )


def summarize_tool_output(
    raw_output: str,
    config,
    summarizer=None,
) -> str:
    """
    Summarize tool output only when it exceeds the configured character
    threshold. Otherwise return it unchanged.
    """

    if not config.summarizer.enabled:
        return raw_output

    if len(raw_output) <= config.summarizer.max_raw_output_chars:
        return raw_output

    if summarizer is None:
        summarizer = build_summarizer(
            config,
            config.summarizer.tool_summary_max_tokens,
        )

    messages = [
        SystemMessage(
            content=(
                "You are a precise tool-output summarizer. "
                "Preserve important facts, values, errors, filenames, paths, "
                "commands, identifiers, and results. Remove redundant or "
                "unnecessary detail. Do not invent information."
            )
        ),
        HumanMessage(content=raw_output),
    ]

    try:
        response = summarizer.invoke(messages)

        content = response.content

        if isinstance(content, str) and content.strip():
            return content.strip()

        return raw_output

    except Exception as error:
        print(
            f"[SUMMARIZER ERROR] Tool output summarization failed: {error}"
        )
        return raw_output


def summarize_context(
    messages,
    config,
    summarizer=None,
):
    """
    Compact conversation history when total message content exceeds the
    configured context threshold.

    Preserves:
    - original system message
    - generated conversation summary
    - most recent messages
    """

    if not config.summarizer.enabled:
        return messages

    total_chars = sum(
        len(str(message.content))
        for message in messages
        if getattr(message, "content", None) is not None
    )

    if total_chars <= config.summarizer.context_trigger_chars:
        return messages

    if not messages:
        return messages

    if summarizer is None:
        summarizer = build_summarizer(
            config,
            config.summarizer.context_summary_max_tokens,
        )

    original_system = messages[0]

    conversation_text = []

    for message in messages[1:]:
        role = message.__class__.__name__
        content = getattr(message, "content", "")

        conversation_text.append(
            f"{role}:\n{content}"
        )

    summary_input = "\n\n".join(conversation_text)

    summary_messages = [
        SystemMessage(
            content=(
                "Summarize the conversation so far. Preserve important facts, "
                "decisions, user preferences, goals, tool results, unresolved "
                "tasks, and technical context. Remove unnecessary repetition. "
                "Output only the summary."
            )
        ),
        HumanMessage(content=summary_input),
    ]

    try:
        response = summarizer.invoke(summary_messages)

        summary = response.content

        if not isinstance(summary, str) or not summary.strip():
            return messages

    except Exception as error:
        print(
            f"[SUMMARIZER ERROR] Context summarization failed: {error}"
        )
        return messages

    # Keep the most recent four messages, matching Adapt's general behavior.
    recent_messages = messages[1:][-4:]

    new_messages = [
        original_system,
        SystemMessage(
            content=f"Previous conversation summary:\n{summary.strip()}"
        ),
        *recent_messages,
    ]

    return new_messages
