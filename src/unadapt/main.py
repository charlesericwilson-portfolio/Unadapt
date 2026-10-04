from pathlib import Path

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI

from unadapt.config import load_config
from unadapt.summarizer import (
    build_summarizer,
    summarize_context,
    summarize_tool_output,
)
from unadapt.tools import (
    terminal,
    session,
    end_session,
    append_memory,
    read_memory,
)


# Load application config.
config = load_config("config.toml")


# Load the main system prompt.
SYSTEM_PROMPT = Path("prompts/system.txt").read_text()


# Main agent model.
model = ChatOpenAI(
    model=config.model.model,
    base_url=config.model.base_url,
    api_key=config.model.api_key,
    temperature=config.model.temperature,
    max_tokens=config.model.max_tokens,
)


# Optional dedicated summarizer model.
summarizer = None

# Register tools.
tools = [
    terminal,
    session,
    end_session,
    append_memory,
    read_memory,
]

tools_by_name = {
    tool.name: tool
    for tool in tools
}


# Bind tool definitions to the main model.
model_with_tools = model.bind_tools(tools)


# Conversation state.
messages = [
    SystemMessage(content=SYSTEM_PROMPT)
]


print("UNADAPT")
print("Type 'exit' or 'quit' to stop.\n")


while True:
    user_input = input("You: ")

    if user_input.lower() in ["exit", "quit"]:
        break

    messages.append(
        HumanMessage(content=user_input)
    )

    # Agent loop:
    #
    # model
    #   ↓
    # tool calls?
    #   ├── yes → execute tools → feed results back → model again
    #   └── no  → final answer
    while True:
        response = model_with_tools.invoke(messages)

        messages.append(response)

        # No tool calls means the model has completed the current task.
        if not response.tool_calls:

            # Compact conversation history if it has grown beyond
            # the configured threshold.
            messages = summarize_context(
                messages,
                config,
                summarizer,
            )

            print(f"Echo: {response.content}\n")
            break

        # Execute every tool call returned by the model.
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            tool = tools_by_name.get(tool_name)

            if tool is None:
                result = f"Tool error: Unknown tool '{tool_name}'."

            else:
                try:
                    result = tool.invoke(tool_args)

                except Exception as error:
                    result = (
                        f"Tool error while executing "
                        f"'{tool_name}': {error}"
                    )

            # All tool types pass through the same summarization path.
            tool_output = summarize_tool_output(
                str(result),
                config,
                summarizer,
            )

            messages.append(
                ToolMessage(
                    content=tool_output,
                    tool_call_id=tool_call["id"],
                )
            )
