from pathlib import Path
from unadapt.tools import terminal, session, end_session

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

from unadapt.tools import terminal


SYSTEM_PROMPT = Path("prompts/system.txt").read_text()

model = ChatOpenAI(
    model="echo",
    base_url="http://localhost:8080/v1",
    api_key="not-needed",
)

tools = [terminal, session, end_session]
tools_by_name = {tool.name: tool for tool in tools}

model_with_tools = model.bind_tools(tools)

messages = [
    SystemMessage(content=SYSTEM_PROMPT)
]

print("UNADAPT")
print("Type 'exit' or 'quit' to stop.\n")

while True:
    user_input = input("You: ")

    if user_input.lower() in ["exit", "quit"]:
        break

    messages.append(HumanMessage(content=user_input))

    while True:
        response = model_with_tools.invoke(messages)

        messages.append(response)

        if not response.tool_calls:
            print(f"Echo: {response.content}\n")
            break

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            tool = tools_by_name[tool_name]
            result = tool.invoke(tool_args)

            messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                )
            )
