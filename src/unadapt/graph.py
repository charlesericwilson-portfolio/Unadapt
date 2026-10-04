from typing import Annotated, TypedDict

from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
)
from langchain_openai import ChatOpenAI

from langgraph.graph import (
    StateGraph,
    START,
    END,
)
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from unadapt.config import load_config
from unadapt.tools import (
    terminal,
    session,
    end_session,
    append_memory,
    read_memory,
)


config = load_config("config.toml")


class AgentState(TypedDict):
    messages: Annotated[
        list[BaseMessage],
        add_messages,
    ]


tools = [
    terminal,
    session,
    end_session,
    append_memory,
    read_memory,
]


model = ChatOpenAI(
    model=config.model.model,
    base_url=config.model.base_url,
    api_key=config.model.api_key,
    temperature=config.model.temperature,
    max_tokens=config.model.max_tokens,
)


model_with_tools = model.bind_tools(tools)


def agent_node(state: AgentState):
    response = model_with_tools.invoke(
        state["messages"]
    )

    return {
        "messages": [response]
    }


def should_continue(state: AgentState):
    last_message = state["messages"][-1]

    if getattr(
        last_message,
        "tool_calls",
        None,
    ):
        return "approval"

    return END


def approval_node(state: AgentState):
    last_message = state["messages"][-1]

    tool_calls = getattr(
        last_message,
        "tool_calls",
        [],
    )

    print("\n--- TOOL APPROVAL REQUIRED ---")

    for tool_call in tool_calls:
        print(
            f"\nTool: {tool_call['name']}"
        )

        print(
            f"Arguments: {tool_call['args']}"
        )

    while True:
        choice = input(
            "\nApprove tool call(s)? [y/n]: "
        ).strip().lower()

        if choice in {"y", "yes"}:
            return {}

        if choice in {"n", "no"}:
            rejection_messages = []

            for tool_call in tool_calls:
                rejection_messages.append(
                    ToolMessage(
                        content=(
                            "Tool execution was rejected "
                            "by the human operator."
                        ),
                        tool_call_id=tool_call["id"],
                    )
                )

            return {
                "messages": rejection_messages
            }

        print("Please enter y or n.")


def approval_route(state: AgentState):
    last_message = state["messages"][-1]

    # If approval_node added ToolMessages,
    # the human rejected execution.
    if isinstance(last_message, ToolMessage):
        return "agent"

    # Otherwise approval returned no state change,
    # meaning execution was approved.
    return "tools"


tool_node = ToolNode(tools)


builder = StateGraph(AgentState)


builder.add_node(
    "agent",
    agent_node,
)

builder.add_node(
    "approval",
    approval_node,
)

builder.add_node(
    "tools",
    tool_node,
)


builder.add_edge(
    START,
    "agent",
)


builder.add_conditional_edges(
    "agent",
    should_continue,
    {
        "approval": "approval",
        END: END,
    },
)


builder.add_conditional_edges(
    "approval",
    approval_route,
    {
        "tools": "tools",
        "agent": "agent",
    },
)


builder.add_edge(
    "tools",
    "agent",
)


graph = builder.compile()
