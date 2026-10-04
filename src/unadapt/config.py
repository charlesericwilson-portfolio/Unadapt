from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@dataclass(frozen=True)
class ModelConfig:
    base_url: str
    model: str
    api_key: str
    temperature: float
    max_tokens: int


@dataclass(frozen=True)
class SummarizerConfig:
    enabled: bool
    base_url: str
    model: str
    api_key: str
    max_raw_output_chars: int
    tool_summary_max_tokens: int
    context_trigger_chars: int
    context_summary_max_tokens: int


@dataclass(frozen=True)
class Config:
    model: ModelConfig
    summarizer: SummarizerConfig
    safety: SafetyConfig
    memory: MemoryConfig

@dataclass(frozen=True)
class MemoryConfig:
    enabled: bool
    base_url: str
    model: str
    api_key: str
    persist_directory: str
    collection_name: str

@dataclass(frozen=True)
class SafetyConfig:
    denylist: list[str]

def load_config(path: str | Path = "config.toml") -> Config:
    config_path = Path(path)

    with config_path.open("rb") as file:
        data = tomllib.load(file)

    model_data = data["model"]
    summarizer_data = data["summarizer"]

    model = ModelConfig(
        base_url=model_data["base_url"],
        model=model_data["model"],
        api_key=model_data.get("api_key", ""),
        temperature=float(model_data.get("temperature", 0.7)),
        max_tokens=int(model_data.get("max_tokens", 2048)),
    )

    memory_data = data["memory"]

    memory = MemoryConfig(
        enabled=bool(memory_data.get("enabled", True)),
        base_url=memory_data["base_url"],
        model=memory_data["model"],
        api_key=memory_data.get("api_key", "not-needed"),
        persist_directory=memory_data.get(
            "persist_directory",
            ".unadapt_memory",
        ),
        collection_name=memory_data.get(
            "collection_name",
            "unadapt_memory",
        ),
    )

    summarizer = SummarizerConfig(
        enabled=bool(summarizer_data.get("enabled", True)),
        base_url=summarizer_data["base_url"],
        model=summarizer_data["model"],
        api_key=summarizer_data.get("api_key", ""),
        max_raw_output_chars=int(
            summarizer_data.get("max_raw_output_chars", 6000)
        ),
        tool_summary_max_tokens=int(
            summarizer_data.get("tool_summary_max_tokens", 1500)
        ),
        context_trigger_chars=int(
            summarizer_data.get("context_trigger_chars", 260000)
        ),
        context_summary_max_tokens=int(
            summarizer_data.get("context_summary_max_tokens", 10000)
        ),
    )

    safety_data = data.get("safety", {})

    safety = SafetyConfig(
        denylist=list(safety_data.get("denylist", [])),
    )

    return Config(
        model=model,
        summarizer=summarizer,
        safety=safety,
        memory=memory,
    )
