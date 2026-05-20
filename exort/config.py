"""
Exort configuration system.

Manages settings, API keys, and runtime preferences.
All config lives in ~/.exort/ (or EXORT_DIR env override).

Config priority:  runtime args > env vars > config.yaml > defaults
"""

import os
from pathlib import Path
from typing import Any, Optional

import yaml


def exort_dir() -> Path:
    """Return the Exort data directory. Defaults to ~/.exort/."""
    override = os.environ.get("EXORT_DIR")
    return Path(override) if override else Path.home() / ".exort"


# ── Factory Defaults ──────────────────────────────────────
# These are the sane defaults. Override in ~/.exort/config.yaml.

BUILT_IN_DEFAULTS = {
    # Which AI backend to use
    "engine": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "max_rounds": 20,           # max tool-call loops per reply
        "max_tokens": 4096,
        "temperature": 0.7,
    },

    # Provider credentials and endpoints
    "providers": {
        # ── Core Providers ──
        "groq": {
            "key_var": "GROQ_API_KEY",
            "endpoint": "https://api.groq.com/openai/v1",
            "model": "llama-3.3-70b-versatile",
            "free": True,
        },
        "openai": {
            "key_var": "OPENAI_API_KEY",
            "endpoint": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
        },
        "ollama": {
            "key_var": None,
            "endpoint": "http://localhost:11434/v1",
            "model": "llama3.1",
            "free": True,
        },
        "anthropic": {
            "key_var": "ANTHROPIC_API_KEY",
            "endpoint": "https://api.anthropic.com/v1",
            "model": "claude-sonnet-4-20250514",
        },
        # ── Open-Source Friendly ──
        "together": {
            "key_var": "TOGETHER_API_KEY",
            "endpoint": "https://api.together.xyz/v1",
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        },
        "fireworks": {
            "key_var": "FIREWORKS_API_KEY",
            "endpoint": "https://api.fireworks.ai/inference/v1",
            "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
        },
        "huggingface": {
            "key_var": "HF_TOKEN",
            "endpoint": "https://api-inference.huggingface.co/v1",
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
        },
        # ── Search-Augmented ──
        "perplexity": {
            "key_var": "PERPLEXITY_API_KEY",
            "endpoint": "https://api.perplexity.ai",
            "model": "sonar-pro",
        },
        # ── Gateway / Aggregator ──
        "openrouter": {
            "key_var": "OPENROUTER_API_KEY",
            "endpoint": "https://openrouter.ai/api/v1",
            "model": "meta-llama/llama-3.3-70b-instruct:free",
            "free": True,
        },
        # ── Chinese / Asian Providers ──
        "deepseek": {
            "key_var": "DEEPSEEK_API_KEY",
            "endpoint": "https://api.deepseek.com/v1",
            "model": "deepseek-chat",
        },
        "moonshot": {
            "key_var": "MOONSHOT_API_KEY",
            "endpoint": "https://api.moonshot.cn/v1",
            "model": "moonshot-v1-128k",
        },
        "siliconflow": {
            "key_var": "SILICONFLOW_API_KEY",
            "endpoint": "https://api.siliconflow.cn/v1",
            "model": "Qwen/Qwen2.5-72B-Instruct",
        },
        # ── European ──
        "mistral": {
            "key_var": "MISTRAL_API_KEY",
            "endpoint": "https://api.mistral.ai/v1",
            "model": "mistral-large-latest",
        },
        # ── Multimodal / Specialized ──
        "gemini": {
            "key_var": "GEMINI_API_KEY",
            "endpoint": None,
            "model": "gemini-2.0-flash",
            "free": True,
        },
        "cohere": {
            "key_var": "COHERE_API_KEY",
            "endpoint": None,
            "model": "command-r-plus",
        },
        # ── Cloud Inference ──
        "replicate": {
            "key_var": "REPLICATE_API_TOKEN",
            "endpoint": None,
            "model": "meta/meta-llama-3.1-405b-instruct",
        },
        # ── Xiaomi MiMo (aliases: xiaomi, xiaomi-mimo) ──
        "mimo": {
            "key_var": "MIMO_API_KEY",  # also accepts XIAOMI_API_KEY
            "endpoint": "https://api.xiaomimimo.com/v1",
            "model": "mimo-v2.5-pro",
            "free": True,
        },
        # ── Other ──
        "xai": {
            "key_var": "XAI_API_KEY",
            "endpoint": "https://api.x.ai/v1",
            "model": "grok-3",
        },
        # ── New Providers (2026) ──
        "nvidia": {
            "key_var": "NVIDIA_API_KEY",
            "endpoint": "https://integrate.api.nvidia.com/v1",
            "model": "nvidia/llama-3.3-nemotron-super-49b-v1",
            "free": True,
        },
        "cerebras": {
            "key_var": "CEREBRAS_API_KEY",
            "endpoint": "https://api.cerebras.ai/v1",
            "model": "llama-3.3-70b",
            "free": True,
        },
        "sambanova": {
            "key_var": "SAMBANOVA_API_KEY",
            "endpoint": "https://api.sambanova.ai/v1",
            "model": "Meta-Llama-3.1-8B-Instruct",
            "free": True,
        },
        "novita": {
            "key_var": "NOVITA_API_KEY",
            "endpoint": "https://api.novita.ai/openai/v1",
            "model": "deepseek/deepseek-v3-0324",
            "free": True,
        },
        "nous": {
            "key_var": "NOUS_API_KEY",
            "endpoint": "https://inference.nousresearch.com/v1",
            "model": "Hermes-3-Llama-3.1-70B",
            "free": True,
        },
        "minimax": {
            "key_var": "MINIMAX_API_KEY",
            "endpoint": "https://api.minimax.io/v1",
            "model": "MiniMax-M2.7",
        },
        "stepfun": {
            "key_var": "STEPFUN_API_KEY",
            "endpoint": "https://api.stepfun.ai/v1",
            "model": "step-3.5-flash",
        },
        "qwen": {
            "key_var": "DASHSCOPE_API_KEY",
            "endpoint": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
        },
        "ollama-cloud": {
            "key_var": "OLLAMA_CLOUD_API_KEY",
            "endpoint": "https://ollama.com/v1",
            "model": "nemotron-3-nano:30b",
            "free": True,
        },
        "kimi": {
            "key_var": "KIMI_API_KEY",
            "endpoint": "https://api.moonshot.ai/v1",
            "model": "kimi-k2",
        },
        "gmi": {
            "key_var": "GMI_API_KEY",
            "endpoint": "https://api.gmi-serving.com/v1",
            "model": "deepseek-ai/DeepSeek-R1",
            "free": True,
        },
        "arcee": {
            "key_var": "ARCEEAI_API_KEY",
            "endpoint": "https://api.arcee.ai/api/v1",
            "model": "arcee-spotlight",
        },
        "zai": {
            "key_var": "ZAI_API_KEY",
            "endpoint": "https://api.z.ai/api/paas/v4",
            "model": "glm-4-flash",
        },
        "volcengine": {
            "key_var": "VOLCENGINE_API_KEY",
            "endpoint": "https://ark.cn-beijing.volces.com/api/v3",
            "model": "doubao-1.5-pro-256k",
        },
        "yi": {
            "key_var": "YI_API_KEY",
            "endpoint": "https://api.lingyiwanwu.com/v1",
            "model": "yi-large",
        },
        "zhipu": {
            "key_var": "ZHIPU_API_KEY",
            "endpoint": "https://open.bigmodel.cn/api/paas/v4",
            "model": "glm-4-flash",
        },
        "baichuan": {
            "key_var": "BAICHUAN_API_KEY",
            "endpoint": "https://api.baichuan-ai.com/v1",
            "model": "Baichuan4",
        },
        "cloudflare": {
            "key_var": "CLOUDFLARE_API_KEY",
            "endpoint": None,  # built dynamically with CLOUDFLARE_ACCOUNT_ID
            "model": "@cf/meta/llama-3.3-70b-instruct",
            "free": True,
        },
        "deepinfra": {
            "key_var": "DEEPINFRA_API_KEY",
            "endpoint": "https://api.deepinfra.com/v1/openai",
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "free": True,
        },
        "lepton": {
            "key_var": "LEPTON_API_KEY",
            "endpoint": "https://api.lepton.ai/v1",
            "model": "llama-3.3-70b",
            "free": True,
        },
        "writer": {
            "key_var": "WRITER_API_KEY",
            "endpoint": "https://api.writer.com/v1",
            "model": "palmyra-x-004",
        },
        "ai21": {
            "key_var": "AI21_API_KEY",
            "endpoint": "https://api.ai21.com/v1",
            "model": "jamba-1.5-large",
        },
        "databricks": {
            "key_var": "DATABRICKS_API_KEY",
            "endpoint": None,  # built from DATABRICKS_HOST
            "model": "dbrx-instruct",
        },
        "voyage": {
            "key_var": "VOYAGE_API_KEY",
            "endpoint": "https://api.voyageai.com/v1",
            "model": "voyage-3",
        },
        "baseten": {
            "key_var": "BASETEN_API_KEY",
            "endpoint": "https://api.baseten.co/v1",
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "free": True,
        },
        "anyscale": {
            "key_var": "ANYSCALE_API_KEY",
            "endpoint": "https://api.endpoints.anyscale.com/v1",
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "free": True,
        },
        "lambda": {
            "key_var": "LAMBDA_API_KEY",
            "endpoint": "https://api.lambdalabs.com/v1",
            "model": "llama3.3-70b-instruct",
        },
        "textsynth": {
            "key_var": "TEXTSYNTH_API_KEY",
            "endpoint": "https://api.textsynth.com/v1",
            "model": "Mistral-7B-v0.3",
            "free": True,
        },
        "nebius": {
            "key_var": "NEBIUS_API_KEY",
            "endpoint": "https://api.studio.nebius.ai/v1",
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "free": True,
        },
        "upstage": {
            "key_var": "UPSTAGE_API_KEY",
            "endpoint": "https://api.upstage.ai/v1",
            "model": "solar-1-mini-chat",
        },
    },

    # Conversation memory
    "memory": {
        "enabled": True,
        "window": 50,               # messages kept in active context
    },

    # Gear (tool) settings
    "gear": {
        "enabled": True,
        "allow_unsafe": False,      # shell/exec require explicit opt-in
    },

    # Playbook (knowledge file) settings
    "playbooks": {
        "enabled": True,
        "autoload": [],
    },

    # Display preferences
    "display": {
        "stream": True,
        "show_gear_calls": True,
        "show_tokens": True,
        "color": True,
    },

    # Telegram bot
    "telegram": {
        "token_var": "TELEGRAM_BOT_TOKEN",
        "max_tokens": 2048,
        "rate_per_minute": 10,
        "allowed_users": [],
    },
}


class Config:
    """
    Exort configuration.

    Reads ~/.exort/config.yaml on init, merges with built-in defaults,
    and exposes .get() / .set() for dot-path access.

        cfg = Config()
        provider = cfg.get("engine.provider")       # "groq"
        cfg.set("engine.temperature", 0.3)
        cfg.save()
    """

    def __init__(self, path: Optional[str] = None):
        self._dir = exort_dir()
        self._path = Path(path) if path else self._dir / "config.yaml"
        self._data: dict = {}
        self._load_yaml()
        self._load_dotenv()

    # ── Loading ───────────────────────────────────────────

    def _load_yaml(self):
        merged = _deepcopy(BUILT_IN_DEFAULTS)
        if self._path.exists():
            with open(self._path, encoding="utf-8") as f:
                user = yaml.safe_load(f) or {}
            merged = _deepmerge(merged, user)
        self._data = merged

    def _load_dotenv(self):
        """Load key=value pairs from ~/.exort/.env into os.environ."""
        env = self._dir / ".env"
        if not env.exists():
            return
        with open(env, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip("\"'")
                if k and k not in os.environ:
                    os.environ[k] = v

    # ── Access ────────────────────────────────────────────

    def get(self, dotpath: str, default: Any = None) -> Any:
        """Read a config value by dot-path.  e.g. 'engine.temperature'"""
        node = self._data
        for key in dotpath.split("."):
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                return default
        return node

    def set(self, dotpath: str, value: Any):
        """Write a config value by dot-path."""
        keys = dotpath.split(".")
        node = self._data
        for k in keys[:-1]:
            if k not in node or not isinstance(node[k], dict):
                node[k] = {}
            node = node[k]
        node[keys[-1]] = value

    def save(self):
        """Persist current config to YAML."""
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    # ── Helpers ───────────────────────────────────────────

    def api_key(self, provider: Optional[str] = None) -> Optional[str]:
        """Resolve the API key env-var for a provider."""
        prov = provider or self.get("engine.provider", "groq")
        var = self.get(f"providers.{prov}.key_var")
        return os.environ.get(var) if var else None

    def provider_conf(self, provider: Optional[str] = None) -> dict:
        """Return the full provider sub-dict."""
        prov = provider or self.get("engine.provider", "groq")
        return self.get(f"providers.{prov}", {})

    @property
    def data(self) -> dict:
        return self._data

    def __repr__(self):
        return f"Config(provider={self.get('engine.provider')}, model={self.get('engine.model')})"


# ── Private helpers ───────────────────────────────────────

def _deepcopy(d: dict) -> dict:
    return {k: _deepcopy(v) if isinstance(v, dict) else v for k, v in d.items()}


def _deepmerge(base: dict, override: dict) -> dict:
    out = base.copy()
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deepmerge(out[k], v)
        else:
            out[k] = v
    return out


def ensure_exort_dir() -> Path:
    """Create ~/.exort/ skeleton if missing. Returns the path."""
    d = exort_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "playbooks").mkdir(exist_ok=True)
    (d / "logs").mkdir(exist_ok=True)
    return d
