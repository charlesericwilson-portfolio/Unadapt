# UNADAPT

UNADAPT is an experimental Python/LangChain reimplementation of concepts from
[Adapt](https://github.com/charlesericwilson-portfolio/Echo_Adapt_v5).

The project has two goals:

1. Learn and evaluate LangChain/LangGraph by rebuilding functionality that already exists in Adapt.
2. Compare a mainstream AI framework against an agent runtime built from first principles.

This is not intended to prove that one approach is universally better than the other.
The goal is to implement comparable capabilities and document where each approach
reduces work, introduces constraints, or moves complexity elsewhere in the stack.

UNADAPT is intentionally being built incrementally. Comparisons below reflect
the functionality implemented and tested so far and will change as the project grows.

---

## Current Status

UNADAPT currently supports:

- Persistent conversational history during a running process
- Local OpenAI-compatible model serving through `ChatOpenAI`
- LangChain tool registration
- Structured tool dispatch
- Arbitrary one-shot terminal commands
- Experimental named persistent terminal sessions using `tmux`
- Multiple tool calls within a single task

The persistent terminal implementation is currently minimal. It demonstrates that
terminal state can survive between tool calls, but reliable command-boundary detection,
output capture, long-running command supervision, and other runtime behavior have not
yet been implemented.

---

## Architecture

The current execution path is approximately:

```text
Model
  ↓
Inference Server
  ↓
OpenAI-compatible structured tool call
  ↓
LangChain ChatOpenAI
  ↓
AIMessage.tool_calls
  ↓
UNADAPT dispatcher
  ↓
Python tool
  ↓
Operating System
```

LangChain handles much of the tool declaration and application-side tool-call plumbing.

UNADAPT remains responsible for the actual execution semantics of those tools.

For example, the current terminal tool ultimately executes commands using Python's
`subprocess` module. Persistent terminal sessions are implemented using `tmux`.

---

## Tool Calling

One of the first experiments in UNADAPT was testing local model tool calling through
LangChain.

This exposed an important distinction:

> An OpenAI-compatible chat-completions endpoint is not necessarily an
> OpenAI-compatible tool-calling endpoint.

LangChain's `ChatOpenAI` integration expects tool calls to arrive through the structured
tool-call representation exposed by the API.

Conceptually:

```text
Native model tool protocol
        ↓
Inference server / parser
        ↓
message.tool_calls
        ↓
LangChain
        ↓
AIMessage.tool_calls
        ↓
UNADAPT
```

During testing, a model could correctly determine both the tool and its arguments while
still failing to execute the tool because the generated action remained ordinary message
content rather than becoming the structured API representation expected by the
integration.

For example, outputs semantically equivalent to:

```json
{
  "name": "terminal",
  "arguments": {
    "command": "ifconfig"
  }
}
```

were not sufficient when they appeared only as assistant text.

The model understood the requested action, but the application did not receive a
structured tool call.

With GPT-OSS and llama.cpp chat parsing enabled, llama.cpp translated the model's native
tool representation into the OpenAI-style `message.tool_calls` structure. LangChain then
recognized the call and UNADAPT executed it normally.

This does **not** mean LangChain requires OpenAI models.

It means the selected LangChain integration, inference server, model protocol, and API
representation must agree on how a tool call crosses the model/application boundary.

---

## UNADAPT vs Adapt

The most obvious advantage observed so far is code size.

LangChain makes declaring tools and exposing them to a compatible model concise. Once
registered, UNADAPT can dispatch tools through a generic lookup rather than implementing
a separate application-side branch for every tool.

That is a real convenience.

The tradeoff observed so far is that this simplicity depends on a more specific interface
contract between the model, inference server, provider integration, and application.

### UNADAPT / LangChain

```text
model-native protocol
        ↓
server parser
        ↓
provider-compatible structured call
        ↓
LangChain abstraction
        ↓
Python function
```

Advantages observed so far:

- Less application code
- Concise tool declarations
- Generic tool registration and dispatch
- Existing provider integrations
- Straightforward happy path when the serving stack exposes the expected structured API

Constraints observed so far:

- Tool-call serialization must be understood by the serving/integration stack
- A semantically correct tool call is not enough if it is returned as ordinary content
- Local model behavior can therefore depend on inference-server parsing and chat-template configuration
- LangChain handles invocation plumbing but does not provide the execution semantics of complex tools

### Adapt

Adapt owns more of the model-to-runtime boundary directly.

The runtime is responsible for interpreting its supported action protocol and dispatching
the resulting operation.

This requires more runtime code, but gives Adapt direct control over that boundary.

Adapt also implements execution behavior outside the scope of basic tool registration,
including functionality such as persistent terminal sessions, command-output capture,
long-running process supervision, and other runtime state management.

---

## Less Code Does Not Mean Less System

One early observation from this experiment is that framework code can remove application
boilerplate without removing the underlying systems problem.

For example, registering a persistent terminal tool with LangChain is easy.

Building a reliable persistent terminal is not.

A minimal implementation can:

```text
send command
    ↓
wait
    ↓
capture tmux pane
    ↓
return output
```

But a reliable implementation must answer additional questions:

```text
Where did this command's output begin?

Has the command actually finished?

Which output belongs to this invocation?

Is the process still running?

Should it move into background supervision?

How is its eventual result returned to the model?
```

Those problems still require conventional runtime code regardless of how the tool was
registered with the model.

This distinction will be tracked throughout the project:

> **Framework plumbing and runtime capability are not the same thing.**

---

## Early Comparison

| Area | UNADAPT / LangChain | Adapt |
|---|---|---|
| Tool declaration | Very concise | More runtime code |
| Tool registration | Built-in abstraction | Runtime-owned |
| Tool dispatch | Generic | Runtime-owned |
| Provider abstraction | Existing ecosystem | Implemented by runtime |
| Tool-call representation | Integration/server contract | Runtime-controlled protocol |
| One-shot shell execution | Simple | Simple |
| Persistent shell state | Custom implementation required | Runtime implementation |
| Output boundary detection | Custom implementation required | Runtime implementation |
| Long-running supervision | Not yet implemented | Runtime implementation |
| Model protocol control | More dependent on integration stack | Greater runtime control |

This table represents the current experiment, not a final evaluation.

UNADAPT has implemented only a small subset of Adapt's functionality.

---

## What We've Learned So Far

LangChain has reduced the amount of application code required for the functionality
implemented so far.

The reduction is most noticeable around tool declaration, registration, provider
integration, and dispatch.

However, the abstraction is more structured than Adapt's runtime-owned model interface.
Local models must ultimately produce a tool-call representation that the selected
integration understands, either directly or through translation by the inference server.

Once execution reaches the Python tool itself, operating-system interaction, persistent
state, process management, output capture, and supervision remain application/runtime
responsibilities.

At this stage the comparison can be summarized as:

> **LangChain reduces plumbing when the stack conforms to its supported interfaces.
> Adapt writes more of that plumbing itself in exchange for owning more of the
> model-to-runtime boundary.**

Whether that tradeoff remains worthwhile as UNADAPT grows is one of the questions this
project is intended to test.

---

## Planned Experiments

Future versions will progressively reproduce additional Adapt capabilities, including:

- Semantic memory and retrieval
- Improved persistent terminal execution
- Reliable command-boundary detection
- Long-running command supervision
- JSON/structured tools
- Remote tool execution
- MCP integration
- Additional model/provider testing
- LangGraph orchestration experiments

Each feature will be compared against the corresponding Adapt implementation where
possible.

The comparison will consider more than line count.

Areas of interest include:

- Implementation complexity
- Framework-specific knowledge required
- Amount of project-owned code
- External dependencies
- Debugging surface
- Model dependence
- Inference-server dependence
- Tool-call format tolerance
- Execution reliability
- Context/token overhead
- Behavioral equivalence

---

## Why Build This?

Adapt was built largely from first principles before its author had significant experience
with mainstream agent frameworks.

UNADAPT reverses that process.

Instead of asking:

> "How would I build this with LangChain?"

the project asks:

> "What happens when functionality already implemented independently is rebuilt using
> LangChain?"

That provides a concrete baseline for evaluating what the framework actually replaces,
what it simplifies, what constraints it introduces, and what still has to be engineered
outside the framework.

The project is therefore both a learning exercise and an implementation comparison.

---

## Related Project

Adapt:

https://github.com/charlesericwilson-portfolio/Echo_Adapt_v5
