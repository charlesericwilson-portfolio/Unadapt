from pathlib import Path

from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
)

from unadapt.graph import graph


SYSTEM_PROMPT = Path(
    "prompts/system.txt"
).read_text()


messages = [
    SystemMessage(
        content=SYSTEM_PROMPT
    )
]


print("UNADAPT - LangGraph")
print("Type 'exit' or 'quit' to stop.\n")


while True:
    user_input = input("You: ")

    if user_input.lower() in [
        "exit",
        "quit",
    ]:
        break

    messages.append(
        HumanMessage(
            content=user_input
        )
    )

    result = graph.invoke(
        {
            "messages": messages
        }
    )

    messages = result["messages"]

    final_message = messages[-1]

    print(
        f"Echo: {final_message.content}\n"
    )
