# UNADAPT

UNADAPT is an experimental Python implementation of agent-runtime concepts from
[Adapt](https://github.com/charlesericwilson-portfolio/Echo_Adapt_v5), built using
LangChain and LangGraph.

The project was created to answer a practical question:

> What does an established AI-agent framework actually replace when compared
> with a runtime built independently from first principles?

The purpose is not to prove that frameworks are universally good or bad.

Instead, UNADAPT implements comparable capabilities and documents where
LangChain/LangGraph reduce implementation work, where they introduce useful
abstractions, and where the underlying runtime engineering still remains the
responsibility of the application.

---

## Current Status

UNADAPT currently includes:

- Config-driven model configuration
- Local OpenAI-compatible model serving through `ChatOpenAI`
- LangChain structured tool registration and dispatch
- Arbitrary one-shot terminal commands
- Named persistent terminal sessions using `tmux`
- Marker-based command-boundary detection
- Polling-based terminal output capture
- Configurable command safety filtering
- Tool-output summarization
- Conversation/context summarization
- Semantic memory using embeddings and Chroma
- Model-driven memory read/write tools
- Multiple tool calls within a task
- A conventional Python agent loop
- An equivalent LangGraph agent loop
- Human approval before LangGraph tool execution

The current implementation intentionally stops short of reproducing every Adapt
feature.

The goal is to compare architectural approaches, not to create a line-for-line
port.

---

## Architecture

UNADAPT currently has two orchestration paths.

### Conventional Loop

```text
User
  ↓
Model
  ↓
Structured tool call?
  ├─ no → final response
  │
  └─ yes
       ↓
     Tool dispatch
       ↓
     Tool execution
       ↓
     ToolMessage
       ↓
     Model
```

### LangGraph Loop

```text
START
  ↓
Agent
  ↓
Tool call?
  ├─ no → END
  │
  └─ yes
       ↓
   Human Approval
       ↓
   approved?
   ├─ yes → Tools → Agent
   └─ no  → rejection ToolMessage → Agent
```

Both approaches use the same underlying tools.

This makes it possible to compare explicit Python orchestration against
LangGraph orchestration without changing the actual execution layer.

---

## Tool Calling

One of the clearest benefits provided by LangChain is structured tool plumbing.

A tool can be declared as a Python function, registered with the model, and
dispatched through a generic interface without writing a separate parser and
dispatch branch for each tool.

Conceptually:

```text
Model-native protocol
        ↓
Inference server / provider
        ↓
Structured API tool call
        ↓
LangChain
        ↓
AIMessage.tool_calls
        ↓
Python tool
```

This is concise and works well when the model, inference server, and integration
agree on the tool-call representation.

During local-model testing, however, an important distinction became apparent:

> A model understanding that it should call a tool is not the same thing as the
> application receiving a structured tool call.

A model may produce the correct tool name and arguments as ordinary generated
text while still failing to trigger execution.

For LangChain's `ChatOpenAI` integration, the serving stack ultimately needs to
expose the action through the expected structured `tool_calls` representation.

With GPT-OSS and llama.cpp tool parsing enabled, llama.cpp translated the
model-native representation into the OpenAI-compatible structure expected by
LangChain, after which tool execution worked normally.

This is not a limitation to OpenAI models.

It is an interface requirement between:

- the model
- the model's native tool protocol
- the inference server
- the provider abstraction
- the application

---

## Persistent Terminal Execution

Registering a terminal function as a LangChain tool is straightforward.

Implementing reliable terminal behavior is a separate problem.

UNADAPT's persistent session implementation uses `tmux` with unique start and
end markers around each command:

```text
START_MARKER
command
END_MARKER
```

The runtime polls the session pane and returns only output found between the
matching markers.

This allows terminal state to survive across model actions while avoiding the
ambiguity of returning an entire terminal pane after every command.

This part of the implementation did not become substantially different because
LangChain was present.

The framework exposes the tool to the model.

The application still determines:

- how commands are executed
- how completion is detected
- which output belongs to which invocation
- how persistent state is maintained
- what happens when execution fails
- how unsafe commands are blocked

This distinction became one of the central findings of the project:

> **Tool registration and tool execution semantics are different layers.**

---

## Safety

UNADAPT includes a configurable command-safety layer before shell execution.

The current implementation checks commands using:

- configurable deny-list entries
- normalized command text
- chained-command inspection
- destructive executable detection
- several simple obfuscation checks

Safety enforcement occurs inside the execution path rather than relying on the
language model to decide whether a command should be allowed.

The implementation is intentionally small and is not intended to represent a
complete sandbox.

---

## Summarization

UNADAPT implements two forms of summarization.

### Tool-Output Summarization

Large tool results can be passed through a separately configured summarizer
before being returned to the model.

This reduces context growth while preserving important output such as:

- errors
- paths
- commands
- results
- state changes

### Context Summarization

When conversation history exceeds a configurable threshold, older messages can
be summarized while preserving the original system prompt and recent turns.

The summarizer can use a separate model endpoint from the main agent model.

---

## Semantic Memory

UNADAPT implements model-driven semantic memory using LangChain integrations.

The agent can explicitly call:

```text
append_memory(category, content)
read_memory(query, limit)
```

Embeddings are generated through a configurable OpenAI-compatible embeddings
endpoint and stored using Chroma.

This is an area where the framework produced a meaningful implementation
benefit.

Instead of manually implementing:

- vector storage
- document insertion
- similarity search
- embedding-client plumbing

UNADAPT can compose existing LangChain abstractions around those components.

The application still owns the policy decision of when memory should be read or
written.

---

## LangGraph

UNADAPT also implements the same basic agent cycle using LangGraph.

For a simple autonomous loop, LangGraph does not eliminate much code compared
with ordinary Python control flow.

A conventional loop already expresses:

```text
model
  ↓
tool?
  ├─ yes → execute → model
  └─ no → finish
```

LangGraph expresses the same behavior as explicit nodes and edges.

Its value becomes clearer when additional control-flow requirements are added.

UNADAPT currently uses a separate approval node before tool execution:

```text
Agent
  ↓
Approval
  ↓
Tools
  ↓
Agent
```

Rejected calls are converted into matching `ToolMessage` responses so that the
tool-call transaction remains valid and the model can continue reasoning.

This makes control flow more visible and provides a natural structure for
features such as:

- human review
- branching
- checkpointing
- pause/resume
- retries
- multi-stage workflows

For a minimal agent, ordinary Python remains simpler.

For workflows where state transitions themselves are important, LangGraph
provides a useful abstraction.

---

## UNADAPT vs Adapt

The comparison is now less about whether either system can implement a feature.

Both approaches can.

The more useful question is:

> Where does the complexity live?

| Area | UNADAPT / LangChain | Adapt |
|---|---|---|
| Tool declaration | Very concise | Runtime-owned |
| Tool registration | Framework abstraction | Runtime-owned |
| Structured tool parsing | Provider/integration abstraction | Runtime-owned protocol |
| Tool dispatch | Generic framework path | Runtime-owned |
| Provider integrations | Large existing ecosystem | Provider adapter layer |
| Persistent shell execution | Application code | Runtime code |
| Command boundaries | Application code | Runtime code |
| Safety enforcement | Application code | Runtime code |
| Tool summarization | Application code | Runtime code |
| Context management | Application code | Runtime code |
| Semantic vector storage | Strong framework/library advantage | Custom/runtime choice |
| Human approval flow | Natural LangGraph node | Must be designed directly |
| Model boundary control | Integration-dependent | Runtime-controlled |
| Orchestration visibility | Explicit graph available | Explicit runtime logic |

---

## Where LangChain Helped

The experiment identified several concrete advantages.

### Tool Declarations

LangChain's tool abstraction is concise and removes repetitive schema and
dispatch plumbing.

### Structured Message Handling

`AIMessage`, `ToolMessage`, and provider integrations provide a consistent
application-level representation once the serving stack produces compatible
structured calls.

### Existing Integrations

Common model providers, embedding APIs, vector stores, and related components
already have integrations available.

This can reduce initial integration work, particularly when working with
unfamiliar APIs or rapidly prototyping a new system.

### Semantic Memory Components

Using `OpenAIEmbeddings` with Chroma avoided implementing vector persistence and
similarity retrieval manually.

This was one of the clearest areas where using an existing framework/library
removed meaningful implementation work rather than simply moving code behind
an abstraction.

### LangGraph Workflow Structure

LangGraph makes branching and human-in-the-loop execution explicit.

This can become useful as workflows develop multiple paths, checkpoints,
approval stages, retries, or other state transitions that are more difficult to
follow inside a large conventional control loop.

These are real improvements and are useful independently of whether the entire
framework is adopted.

---

## What Still Had to Be Built

The largest observation from UNADAPT is that reducing framework plumbing does
not remove most agent-runtime behavior.

The application still had to implement:

- shell execution
- persistent terminal state
- command-boundary detection
- polling
- output extraction
- command safety
- summarization policy
- context management
- memory policy
- human approval behavior
- configuration
- runtime control flow

For the functionality implemented so far, LangChain reduced code around the
model/application interface more substantially than it reduced code around
runtime behavior.

That difference matters when evaluating framework value.

A framework can make a tool easy to expose to a model without making the
underlying capability easy to implement.

---

## Provider Abstraction

LangChain provides a large ecosystem of provider integrations, which is useful
when starting a project or supporting unfamiliar APIs.

Adapt takes a different approach.

Provider-specific behavior is normalized behind its own runtime boundary so
that provider selection can remain primarily configuration-driven once an
adapter exists.

The practical tradeoff is therefore not simply:

```text
framework supports many providers
vs.
custom runtime supports one
```

It is closer to:

```text
Framework:
provider integrations are supplied by an external ecosystem

Custom runtime:
provider integrations are implemented once behind a project-owned interface
```

LangChain reduces the initial work required to support a provider.

A project-owned abstraction provides greater control over how providers are
normalized and how much provider-specific behavior is exposed to the rest of
the runtime.

The preferred approach depends largely on whether rapid integration or direct
control of the model boundary is more important to the project.

---

## LangChain and AI-Assisted Development

One result of this experiment was not specific to LangChain itself.

Modern AI-assisted software development changes the cost of writing framework
plumbing.

Historically, avoiding custom infrastructure could save a substantial amount of
developer time.

Today, relatively small adapters, dispatch layers, configuration structures,
and API integrations can often be implemented quickly when the developer
already understands the desired architecture.

This does not eliminate the value of frameworks.

Frameworks still provide:

- tested integrations
- shared conventions
- documentation
- ecosystem compatibility
- abstractions familiar to other developers
- reduced initial design work

However, the tradeoff between adopting a framework and building a small
purpose-specific abstraction has changed.

The relevant question is increasingly not:

> "Can this be built without a framework?"

but:

> "Does the framework remove enough complexity to justify adopting its
> abstractions and constraints?"

UNADAPT was useful precisely because it allowed that question to be tested
through implementation rather than assumption.

---

## Early Conclusions

Several conclusions have become clearer as the project has grown.

### 1. LangChain reduces plumbing more than runtime engineering

Tool schemas, message conversion, registration, and dispatch become concise.

Execution semantics still belong to the application.

### 2. LangChain is strongest when using its ecosystem

Embedding integrations, vector stores, provider wrappers, and similar
components provide more substantial savings than replacing a small Python agent
loop.

### 3. LangGraph becomes more useful as workflow structure becomes more complex

For a simple tool-use cycle, conventional Python is straightforward.

As human approval, branching, retries, durable state, or multiple execution
paths are introduced, an explicit graph becomes easier to justify.

### 4. Owning the runtime boundary provides flexibility

A custom runtime can normalize provider behavior and tool protocols according to
its own requirements.

The cost is that the project owns that implementation and maintenance.

### 5. Using a framework does not eliminate systems engineering

Persistent processes, operating-system interaction, authorization, safety,
reliable output capture, concurrency, and lifecycle management remain systems
problems regardless of how a tool is registered with a language model.

---

## What UNADAPT Changed My View On

The experiment began with the expectation that a mature agent framework might
replace a substantial portion of the runtime engineering required by Adapt.

The result was more nuanced.

LangChain successfully reduced repetitive integration code and provided useful
existing components.

LangGraph provided a clean representation for explicit workflow state and
human-in-the-loop execution.

However, most of the behavior that determines how an autonomous system
actually operates still had to be implemented in ordinary application code.

That does not make the framework unnecessary.

It changes the role of the framework.

Rather than replacing the runtime, LangChain primarily provides abstractions and
integrations around parts of the runtime.

For projects that benefit from its ecosystem, those abstractions can save
meaningful work.

For projects with unusual execution semantics or an already-developed runtime
architecture, building small purpose-specific abstractions may provide greater
control without requiring substantially more implementation effort.

That tradeoff is the main result of the experiment so far.

---

## Planned Work

The remaining planned experiment is:

- MCP server connectivity

Additional work may be added if it reveals a meaningful architectural
difference between the framework-based implementation and Adapt.

The project is not intended to reproduce every Adapt feature solely for feature
parity.

---

## Why Build This?

Adapt was built largely from first principles before its author had significant
experience with mainstream agent frameworks.

UNADAPT reverses that process.

Instead of asking:

> "How would I build this with LangChain?"

the project asks:

> "What happens when functionality already implemented independently is rebuilt
> using LangChain?"

That provides a concrete baseline for evaluating:

- what the framework replaces
- what it simplifies
- what constraints it introduces
- what complexity remains
- where existing ecosystem components provide meaningful leverage
- where direct implementation remains competitive

The project is therefore both a learning exercise and an implementation
comparison.

---

## Related Project

Adapt:

https://github.com/charlesericwilson-portfolio/Echo_Adapt_v5
