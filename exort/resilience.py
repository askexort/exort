"""
Exort Provider Resilience Layer — Self-Healing AI for Everyone

Features:
  - Multi-key rotation per provider (survive rate limits)
  - Health monitoring with admin Telegram alerts
  - Auto-failover chain (never return errors to users)
  - Usage dashboard (web UI)
  - Provider health tracking

Usage:
  from exort.resilience import ResilientProviderChain
  chain = ResilientProviderChain()
  response = await chain.chat("hello")
"""

import asyncio
import json
import logging
import os
import time
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

from dotenv import load_dotenv

# Load .env from ~/.exort/.env
load_dotenv(os.path.expanduser('~/.exort/.env'))

logger = logging.getLogger(__name__)


# ─── Provider Key Pool ────────────────────────────────────────────────────────

@dataclass
class ProviderKey:
    """A single API key with health tracking."""
    key: str
    provider: str
    healthy: bool = True
    last_used: float = 0
    last_error: str = ""
    error_count: int = 0
    success_count: int = 0
    rate_limited_until: float = 0  # timestamp when rate limit expires

    @property
    def is_available(self) -> bool:
        """Check if this key can be used right now."""
        if not self.healthy:
            return False
        if self.rate_limited_until > time.time():
            return False
        return True

    def mark_success(self):
        self.last_used = time.time()
        self.success_count += 1
        self.error_count = 0
        self.healthy = True
        self.rate_limited_until = 0

    def mark_error(self, error: str, is_rate_limit: bool = False):
        self.last_used = time.time()
        self.last_error = error
        self.error_count += 1
        if is_rate_limit:
            # Rate limit: wait 60 seconds before retrying
            self.rate_limited_until = time.time() + 60
        elif self.error_count >= 3:
            # 3 consecutive errors: mark unhealthy
            self.healthy = False


@dataclass
class ProviderConfig:
    """Configuration for a provider with multiple keys."""
    name: str
    url: str
    model: str
    keys: list = field(default_factory=list)
    priority: int = 0  # lower = higher priority

    @property
    def has_available_key(self) -> bool:
        return any(k.is_available for k in self.keys)

    def get_next_key(self) -> ProviderKey:
        """Get the next available key, preferring least-recently-used."""
        available = [k for k in self.keys if k.is_available]
        if not available:
            return None
        # Prefer least-recently-used
        available.sort(key=lambda k: k.last_used)
        return available[0]


# ─── Resilient Provider Chain ─────────────────────────────────────────────────

class ResilientProviderChain:
    """
    Self-healing AI provider chain with multi-key rotation.
    
    Features:
    - Multiple keys per provider (survive rate limits)
    - Auto-failover between providers
    - Health monitoring with admin alerts
    - Usage statistics
    """

    def __init__(self, admin_chat_id: int = None):
        self.providers: list[ProviderConfig] = []
        self.admin_chat_id = admin_chat_id or self._get_admin_id()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.stats = {
            "total_requests": 0,
            "total_success": 0,
            "total_failures": 0,
            "provider_usage": defaultdict(int),
            "provider_errors": defaultdict(int),
            "start_time": datetime.utcnow(),
            "last_alert": 0,
        }
        self._load_providers()

    def _get_admin_id(self) -> int:
        """Get admin chat ID from env or database."""
        admin_ids = os.getenv("ADMIN_IDS", "")
        if admin_ids:
            try:
                return int(admin_ids.split(",")[0].strip())
            except ValueError:
                pass
        # Try to read from database
        try:
            import sqlite3
            db_path = os.path.expanduser("~/.exort/conversations.db")
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT title FROM sessions WHERE title LIKE 'tg-%' LIMIT 1")
                result = cursor.fetchone()
                conn.close()
                if result:
                    return int(result[0].replace("tg-", ""))
        except Exception:
            pass
        return None

    def _load_providers(self):
        """Load providers from environment variables."""
        # OpenRouter (supports multiple keys via comma-separated env)
        openrouter_keys = self._split_keys(os.getenv("OPENROUTER_API_KEY", ""))
        if openrouter_keys:
            openrouter_models = [
                "google/gemma-4-26b-a4b-it:free",
                "google/gemma-4-31b-it:free",
                "deepseek/deepseek-v4-flash:free",
                "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
            ]
            for model in openrouter_models:
                model_short = model.split("/")[1].split(":")[0]
                self.providers.append(ProviderConfig(
                    name=f"OpenRouter/{model_short}",
                    url="https://openrouter.ai/api/v1/chat/completions",
                    model=model,
                    keys=[ProviderKey(key=k, provider="OpenRouter") for k in openrouter_keys],
                    priority=0,
                ))

        # Groq (supports multiple keys)
        groq_keys = self._split_keys(os.getenv("GROQ_API_KEY", ""))
        if groq_keys:
            self.providers.append(ProviderConfig(
                name="Groq/llama-3.3-70b",
                url="https://api.groq.com/openai/v1/chat/completions",
                model="llama-3.3-70b-versatile",
                keys=[ProviderKey(key=k, provider="Groq") for k in groq_keys],
                priority=1,
            ))

        # MiMo
        mimo_keys = self._split_keys(os.getenv("MIMO_API_KEY", ""))
        if mimo_keys:
            self.providers.append(ProviderConfig(
                name="MiMo/v2.5-pro",
                url="https://api.xiaomimimo.com/v1/chat/completions",
                model="mimo-v2.5-pro",
                keys=[ProviderKey(key=k, provider="MiMo") for k in mimo_keys],
                priority=2,
            ))

        # Cerebras (supports multiple keys)
        cerebras_keys = self._split_keys(os.getenv("CEREBRAS_API_KEY", ""))
        if cerebras_keys:
            self.providers.append(ProviderConfig(
                name="Cerebras/llama-3.3-70b",
                url="https://api.cerebras.ai/v1/chat/completions",
                model="llama-3.3-70b",
                keys=[ProviderKey(key=k, provider="Cerebras") for k in cerebras_keys],
                priority=3,
            ))

        # Together AI
        together_keys = self._split_keys(os.getenv("TOGETHER_API_KEY", ""))
        if together_keys:
            self.providers.append(ProviderConfig(
                name="Together/Meta-Llama-3.1-70B",
                url="https://api.together.xyz/v1/chat/completions",
                model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                keys=[ProviderKey(key=k, provider="Together") for k in together_keys],
                priority=4,
            ))

        # DeepSeek
        deepseek_keys = self._split_keys(os.getenv("DEEPSEEK_API_KEY", ""))
        if deepseek_keys:
            self.providers.append(ProviderConfig(
                name="DeepSeek/chat",
                url="https://api.deepseek.com/v1/chat/completions",
                model="deepseek-chat",
                keys=[ProviderKey(key=k, provider="DeepSeek") for k in deepseek_keys],
                priority=5,
            ))

        # Mistral
        mistral_keys = self._split_keys(os.getenv("MISTRAL_API_KEY", ""))
        if mistral_keys:
            self.providers.append(ProviderConfig(
                name="Mistral/large",
                url="https://api.mistral.ai/v1/chat/completions",
                model="mistral-large-latest",
                keys=[ProviderKey(key=k, provider="Mistral") for k in mistral_keys],
                priority=6,
            ))

        # Fireworks
        fireworks_keys = self._split_keys(os.getenv("FIREWORKS_API_KEY", ""))
        if fireworks_keys:
            self.providers.append(ProviderConfig(
                name="Fireworks/llama-v3p3-70b",
                url="https://api.fireworks.ai/inference/v1/chat/completions",
                model="accounts/fireworks/models/llama-v3p3-70b-instruct",
                keys=[ProviderKey(key=k, provider="Fireworks") for k in fireworks_keys],
                priority=7,
            ))

        # xAI
        xai_keys = self._split_keys(os.getenv("XAI_API_KEY", ""))
        if xai_keys:
            self.providers.append(ProviderConfig(
                name="xAI/grok-3",
                url="https://api.x.ai/v1/chat/completions",
                model="grok-3",
                keys=[ProviderKey(key=k, provider="xAI") for k in xai_keys],
                priority=8,
            ))

        # SiliconFlow
        silicon_keys = self._split_keys(os.getenv("SILICONFLOW_API_KEY", ""))
        if silicon_keys:
            self.providers.append(ProviderConfig(
                name="SiliconFlow/Qwen2.5-72B",
                url="https://api.siliconflow.cn/v1/chat/completions",
                model="Qwen/Qwen2.5-72B-Instruct",
                keys=[ProviderKey(key=k, provider="SiliconFlow") for k in silicon_keys],
                priority=9,
            ))

        # Moonshot
        moonshot_keys = self._split_keys(os.getenv("MOONSHOT_API_KEY", ""))
        if moonshot_keys:
            self.providers.append(ProviderConfig(
                name="Moonshot/v1-128k",
                url="https://api.moonshot.cn/v1/chat/completions",
                model="moonshot-v1-128k",
                keys=[ProviderKey(key=k, provider="Moonshot") for k in moonshot_keys],
                priority=10,
            ))

        # Hugging Face
        hf_keys = self._split_keys(os.getenv("HF_TOKEN", ""))
        if hf_keys:
            self.providers.append(ProviderConfig(
                name="HuggingFace/Llama-3.1-70B",
                url="https://api-inference.huggingface.co/v1/chat/completions",
                model="meta-llama/Meta-Llama-3.1-70B-Instruct",
                keys=[ProviderKey(key=k, provider="HuggingFace") for k in hf_keys],
                priority=11,
            ))

        # NVIDIA NIM
        nvidia_keys = self._split_keys(os.getenv("NVIDIA_API_KEY", ""))
        if nvidia_keys:
            self.providers.append(ProviderConfig(
                name="NVIDIA/nemotron-super-49b",
                url="https://integrate.api.nvidia.com/v1/chat/completions",
                model="nvidia/llama-3.3-nemotron-super-49b-v1",
                keys=[ProviderKey(key=k, provider="NVIDIA") for k in nvidia_keys],
                priority=12,
            ))

        # SambaNova
        sambanova_keys = self._split_keys(os.getenv("SAMBANOVA_API_KEY", ""))
        if sambanova_keys:
            self.providers.append(ProviderConfig(
                name="SambaNova/Llama-3.1-8B",
                url="https://api.sambanova.ai/v1/chat/completions",
                model="Meta-Llama-3.1-8B-Instruct",
                keys=[ProviderKey(key=k, provider="SambaNova") for k in sambanova_keys],
                priority=13,
            ))

        # NovitaAI
        novita_keys = self._split_keys(os.getenv("NOVITA_API_KEY", ""))
        if novita_keys:
            self.providers.append(ProviderConfig(
                name="Novita/deepseek-v3",
                url="https://api.novita.ai/openai/v1/chat/completions",
                model="deepseek/deepseek-v3-0324",
                keys=[ProviderKey(key=k, provider="Novita") for k in novita_keys],
                priority=14,
            ))

        # Nous Research
        nous_keys = self._split_keys(os.getenv("NOUS_API_KEY", ""))
        if nous_keys:
            self.providers.append(ProviderConfig(
                name="Nous/Hermes-3-70B",
                url="https://inference.nousresearch.com/v1/chat/completions",
                model="Hermes-3-Llama-3.1-70B",
                keys=[ProviderKey(key=k, provider="Nous") for k in nous_keys],
                priority=15,
            ))

        # MiniMax
        minimax_keys = self._split_keys(os.getenv("MINIMAX_API_KEY", ""))
        if minimax_keys:
            self.providers.append(ProviderConfig(
                name="MiniMax/M2.7",
                url="https://api.minimax.io/v1/chat/completions",
                model="MiniMax-M2.7",
                keys=[ProviderKey(key=k, provider="MiniMax") for k in minimax_keys],
                priority=16,
            ))

        # StepFun
        stepfun_keys = self._split_keys(os.getenv("STEPFUN_API_KEY", ""))
        if stepfun_keys:
            self.providers.append(ProviderConfig(
                name="StepFun/step-3.5-flash",
                url="https://api.stepfun.ai/v1/chat/completions",
                model="step-3.5-flash",
                keys=[ProviderKey(key=k, provider="StepFun") for k in stepfun_keys],
                priority=17,
            ))

        # Qwen (DashScope)
        qwen_keys = self._split_keys(os.getenv("DASHSCOPE_API_KEY", ""))
        if qwen_keys:
            self.providers.append(ProviderConfig(
                name="Qwen/qwen-plus",
                url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions",
                model="qwen-plus",
                keys=[ProviderKey(key=k, provider="Qwen") for k in qwen_keys],
                priority=18,
            ))

        # Kimi (Moonshot)
        kimi_keys = self._split_keys(os.getenv("KIMI_API_KEY", ""))
        if kimi_keys:
            self.providers.append(ProviderConfig(
                name="Kimi/kimi-k2",
                url="https://api.moonshot.ai/v1/chat/completions",
                model="kimi-k2",
                keys=[ProviderKey(key=k, provider="Kimi") for k in kimi_keys],
                priority=19,
            ))

        # GMI Cloud
        gmi_keys = self._split_keys(os.getenv("GMI_API_KEY", ""))
        if gmi_keys:
            self.providers.append(ProviderConfig(
                name="GMI/DeepSeek-R1",
                url="https://api.gmi-serving.com/v1/chat/completions",
                model="deepseek-ai/DeepSeek-R1",
                keys=[ProviderKey(key=k, provider="GMI") for k in gmi_keys],
                priority=20,
            ))

        # Arcee AI
        arcee_keys = self._split_keys(os.getenv("ARCEEAI_API_KEY", ""))
        if arcee_keys:
            self.providers.append(ProviderConfig(
                name="Arcee/spotlight",
                url="https://api.arcee.ai/api/v1/chat/completions",
                model="arcee-spotlight",
                keys=[ProviderKey(key=k, provider="Arcee") for k in arcee_keys],
                priority=21,
            ))

        # Z.AI (Zhipu)
        zai_keys = self._split_keys(os.getenv("ZAI_API_KEY", "") or os.getenv("GLM_API_KEY", ""))
        if zai_keys:
            self.providers.append(ProviderConfig(
                name="ZAI/glm-4-flash",
                url="https://api.z.ai/api/paas/v4/chat/completions",
                model="glm-4-flash",
                keys=[ProviderKey(key=k, provider="ZAI") for k in zai_keys],
                priority=22,
            ))

        # Volcengine (ByteDance)
        volc_keys = self._split_keys(os.getenv("VOLCENGINE_API_KEY", ""))
        if volc_keys:
            self.providers.append(ProviderConfig(
                name="Volcengine/doubao",
                url="https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                model="doubao-1.5-pro-256k",
                keys=[ProviderKey(key=k, provider="Volcengine") for k in volc_keys],
                priority=23,
            ))

        # Yi (01.AI)
        yi_keys = self._split_keys(os.getenv("YI_API_KEY", ""))
        if yi_keys:
            self.providers.append(ProviderConfig(
                name="Yi/yi-large",
                url="https://api.lingyiwanwu.com/v1/chat/completions",
                model="yi-large",
                keys=[ProviderKey(key=k, provider="Yi") for k in yi_keys],
                priority=24,
            ))

        # Zhipu AI
        zhipu_keys = self._split_keys(os.getenv("ZHIPU_API_KEY", ""))
        if zhipu_keys:
            self.providers.append(ProviderConfig(
                name="Zhipu/glm-4-flash",
                url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
                model="glm-4-flash",
                keys=[ProviderKey(key=k, provider="Zhipu") for k in zhipu_keys],
                priority=25,
            ))

        # Baichuan
        baichuan_keys = self._split_keys(os.getenv("BAICHUAN_API_KEY", ""))
        if baichuan_keys:
            self.providers.append(ProviderConfig(
                name="Baichuan/Baichuan4",
                url="https://api.baichuan-ai.com/v1/chat/completions",
                model="Baichuan4",
                keys=[ProviderKey(key=k, provider="Baichuan") for k in baichuan_keys],
                priority=26,
            ))

        # Cloudflare Workers AI
        cf_keys = self._split_keys(os.getenv("CLOUDFLARE_API_KEY", ""))
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
        if cf_keys and cf_account:
            self.providers.append(ProviderConfig(
                name="Cloudflare/llama-3.3-70b",
                url=f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/v1/chat/completions",
                model="@cf/meta/llama-3.3-70b-instruct",
                keys=[ProviderKey(key=k, provider="Cloudflare") for k in cf_keys],
                priority=27,
            ))

        # DeepInfra
        deepinfra_keys = self._split_keys(os.getenv("DEEPINFRA_API_KEY", ""))
        if deepinfra_keys:
            self.providers.append(ProviderConfig(
                name="DeepInfra/Llama-3.1-70B",
                url="https://api.deepinfra.com/v1/openai/chat/completions",
                model="meta-llama/Meta-Llama-3.1-70B-Instruct",
                keys=[ProviderKey(key=k, provider="DeepInfra") for k in deepinfra_keys],
                priority=28,
            ))

        # Lepton AI
        lepton_keys = self._split_keys(os.getenv("LEPTON_API_KEY", ""))
        if lepton_keys:
            self.providers.append(ProviderConfig(
                name="Lepton/llama-3.3-70b",
                url="https://api.lepton.ai/v1/chat/completions",
                model="llama-3.3-70b",
                keys=[ProviderKey(key=k, provider="Lepton") for k in lepton_keys],
                priority=29,
            ))

        # Writer
        writer_keys = self._split_keys(os.getenv("WRITER_API_KEY", ""))
        if writer_keys:
            self.providers.append(ProviderConfig(
                name="Writer/palmyra-x-004",
                url="https://api.writer.com/v1/chat/completions",
                model="palmyra-x-004",
                keys=[ProviderKey(key=k, provider="Writer") for k in writer_keys],
                priority=30,
            ))

        # AI21 Labs
        ai21_keys = self._split_keys(os.getenv("AI21_API_KEY", ""))
        if ai21_keys:
            self.providers.append(ProviderConfig(
                name="AI21/jamba-1.5-large",
                url="https://api.ai21.com/v1/chat/completions",
                model="jamba-1.5-large",
                keys=[ProviderKey(key=k, provider="AI21") for k in ai21_keys],
                priority=31,
            ))

        # Databricks
        dbx_keys = self._split_keys(os.getenv("DATABRICKS_API_KEY", ""))
        dbx_host = os.getenv("DATABRICKS_HOST", "")
        if dbx_keys and dbx_host:
            self.providers.append(ProviderConfig(
                name="Databricks/dbrx-instruct",
                url=f"https://{dbx_host}/serving-endpoints/chat/completions",
                model="dbrx-instruct",
                keys=[ProviderKey(key=k, provider="Databricks") for k in dbx_keys],
                priority=32,
            ))

        # Anyscale
        anyscale_keys = self._split_keys(os.getenv("ANYSCALE_API_KEY", ""))
        if anyscale_keys:
            self.providers.append(ProviderConfig(
                name="Anyscale/Llama-3.1-70B",
                url="https://api.endpoints.anyscale.com/v1/chat/completions",
                model="meta-llama/Meta-Llama-3.1-70B-Instruct",
                keys=[ProviderKey(key=k, provider="Anyscale") for k in anyscale_keys],
                priority=33,
            ))

        # Lambda Cloud
        lambda_keys = self._split_keys(os.getenv("LAMBDA_API_KEY", ""))
        if lambda_keys:
            self.providers.append(ProviderConfig(
                name="Lambda/llama3.3-70b",
                url="https://api.lambdalabs.com/v1/chat/completions",
                model="llama3.3-70b-instruct",
                keys=[ProviderKey(key=k, provider="Lambda") for k in lambda_keys],
                priority=34,
            ))

        # Nebius AI Studio
        nebius_keys = self._split_keys(os.getenv("NEBIUS_API_KEY", ""))
        if nebius_keys:
            self.providers.append(ProviderConfig(
                name="Nebius/Llama-3.1-70B",
                url="https://api.studio.nebius.ai/v1/chat/completions",
                model="meta-llama/Meta-Llama-3.1-70B-Instruct",
                keys=[ProviderKey(key=k, provider="Nebius") for k in nebius_keys],
                priority=35,
            ))

        # Upstage
        upstage_keys = self._split_keys(os.getenv("UPSTAGE_API_KEY", ""))
        if upstage_keys:
            self.providers.append(ProviderConfig(
                name="Upstage/solar-1-mini",
                url="https://api.upstage.ai/v1/chat/completions",
                model="solar-1-mini-chat",
                keys=[ProviderKey(key=k, provider="Upstage") for k in upstage_keys],
                priority=36,
            ))

        # Baseten
        baseten_keys = self._split_keys(os.getenv("BASETEN_API_KEY", ""))
        if baseten_keys:
            self.providers.append(ProviderConfig(
                name="Baseten/Llama-3.1-70B",
                url="https://api.baseten.co/v1/chat/completions",
                model="meta-llama/Meta-Llama-3.1-70B-Instruct",
                keys=[ProviderKey(key=k, provider="Baseten") for k in baseten_keys],
                priority=37,
            ))

        # TextSynth
        textsynth_keys = self._split_keys(os.getenv("TEXTSYNTH_API_KEY", ""))
        if textsynth_keys:
            self.providers.append(ProviderConfig(
                name="TextSynth/Mistral-7B",
                url="https://api.textsynth.com/v1/chat/completions",
                model="Mistral-7B-v0.3",
                keys=[ProviderKey(key=k, provider="TextSynth") for k in textsynth_keys],
                priority=38,
            ))

        # Ollama Cloud
        ollama_cloud_keys = self._split_keys(os.getenv("OLLAMA_CLOUD_API_KEY", ""))
        if ollama_cloud_keys:
            self.providers.append(ProviderConfig(
                name="OllamaCloud/nemotron-3-nano",
                url="https://ollama.com/v1/chat/completions",
                model="nemotron-3-nano:30b",
                keys=[ProviderKey(key=k, provider="OllamaCloud") for k in ollama_cloud_keys],
                priority=39,
            ))

        # Sort by priority
        self.providers.sort(key=lambda p: p.priority)
        logger.info(f"Loaded {len(self.providers)} providers")

    def _split_keys(self, keys_str: str) -> list:
        """Split comma-separated keys, filtering empty ones."""
        if not keys_str:
            return []
        return [k.strip() for k in keys_str.split(",") if k.strip()]

    async def chat(self, message: str, system_prompt: str = None) -> str:
        """
        Send a message to AI with automatic failover.
        
        Tries each provider in order. If one fails, moves to next.
        If all fail, returns a helpful error message.
        """
        self.stats["total_requests"] += 1

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        last_error = None
        for provider in self.providers:
            if not provider.has_available_key:
                continue

            key = provider.get_next_key()
            if not key:
                continue

            try:
                response = await self._call_provider(provider, key, messages)
                if response:
                    key.mark_success()
                    self.stats["total_success"] += 1
                    self.stats["provider_usage"][provider.name] += 1
                    return response
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "rate" in error_str.lower()
                key.mark_error(error_str, is_rate_limit)
                self.stats["total_failures"] += 1
                self.stats["provider_errors"][provider.name] += 1
                last_error = f"{provider.name}: {error_str[:100]}"
                logger.warning(f"{provider.name} failed: {error_str[:100]}")

                # Alert admin if key is now unhealthy
                if not key.healthy:
                    await self._alert_admin(
                        f"⚠️ Key dead: {provider.name}\n"
                        f"Error: {error_str[:100]}\n"
                        f"Rotating to next key..."
                    )

        # All providers failed
        logger.error(f"All providers failed. Last error: {last_error}")
        await self._alert_admin(f"🚨 ALL PROVIDERS FAILED\nLast error: {last_error}")
        return f"⚠️ All AI providers exhausted. Please try again in a few minutes."

    async def _call_provider(self, provider: ProviderConfig, key: ProviderKey, messages: list) -> str:
        """Call a single provider with the given key."""
        payload = json.dumps({
            "model": provider.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }).encode()

        headers = {
            "Authorization": f"Bearer {key.key}",
            "Content-Type": "application/json",
            "User-Agent": "Exort-Bot/2.0.0",
        }

        # Add OpenRouter-specific headers
        if "openrouter" in provider.url:
            headers["HTTP-Referer"] = "https://github.com/askexort/exort"
            headers["X-Title"] = "Exort AI"

        req = urllib.request.Request(provider.url, data=payload, headers=headers)

        def _sync_call():
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]

        return await asyncio.to_thread(_sync_call)

    async def _alert_admin(self, message: str):
        """Send alert to admin via Telegram."""
        if not self.admin_chat_id or not self.bot_token:
            return

        # Rate limit alerts (max 1 per 5 minutes)
        now = time.time()
        if now - self.stats["last_alert"] < 300:
            return
        self.stats["last_alert"] = now

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = json.dumps({
                "chat_id": self.admin_chat_id,
                "text": f"🤖 Exort Alert\n\n{message}",
                "parse_mode": "Markdown",
            }).encode()

            def _send():
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return json.loads(resp.read())

            await asyncio.to_thread(_send)
        except Exception as e:
            logger.warning(f"Failed to send admin alert: {e}")

    def get_health_report(self) -> dict:
        """Get current health status of all providers."""
        report = {
            "providers": [],
            "stats": dict(self.stats),
            "timestamp": datetime.utcnow().isoformat(),
        }

        for provider in self.providers:
            provider_info = {
                "name": provider.name,
                "model": provider.model,
                "total_keys": len(provider.keys),
                "healthy_keys": sum(1 for k in provider.keys if k.healthy),
                "available_keys": sum(1 for k in provider.keys if k.is_available),
                "keys": [],
            }
            for key in provider.keys:
                provider_info["keys"].append({
                    "healthy": key.healthy,
                    "available": key.is_available,
                    "success_count": key.success_count,
                    "error_count": key.error_count,
                    "last_error": key.last_error[:50] if key.last_error else "",
                    "rate_limited": key.rate_limited_until > time.time(),
                })
            report["providers"].append(provider_info)

        return report

    async def health_check(self) -> str:
        """Run a health check on all providers and return status."""
        report = self.get_health_report()
        lines = ["🏥 **Provider Health Report**\n"]

        for p in report["providers"]:
            status = "✅" if p["available_keys"] > 0 else "❌"
            lines.append(f"{status} **{p['name']}**")
            lines.append(f"   Model: `{p['model']}`")
            lines.append(f"   Keys: {p['available_keys']}/{p['total_keys']} available")
            for i, k in enumerate(p["keys"]):
                k_status = "✅" if k["available"] else ("⏳" if k["rate_limited"] else "❌")
                lines.append(f"   Key {i+1}: {k_status} (success: {k['success_count']}, errors: {k['error_count']})")

        stats = report["stats"]
        uptime = datetime.utcnow() - stats["start_time"]
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)

        lines.append(f"\n📊 **Stats**")
        lines.append(f"   Requests: {stats['total_requests']}")
        lines.append(f"   Success: {stats['total_success']}")
        lines.append(f"   Failures: {stats['total_failures']}")
        lines.append(f"   Uptime: {hours}h {minutes}m")

        return "\n".join(lines)


# ─── Dashboard Server ─────────────────────────────────────────────────────────

class DashboardHandler(BaseHTTPRequestHandler):
    """Web dashboard for provider health monitoring."""

    chain: ResilientProviderChain = None

    def do_GET(self):
        if self.path == "/dashboard" or self.path == "/dashboard/":
            self._serve_dashboard()
        elif self.path == "/api/health":
            self._serve_api()
        elif self.path == "/":
            self._serve_health()
        else:
            self.send_error(404)

    def _serve_health(self):
        """Simple health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def _serve_api(self):
        """JSON API endpoint for health data."""
        if not self.chain:
            self.send_error(503, "Chain not initialized")
            return

        report = self.chain.get_health_report()
        # Convert datetime to string for JSON serialization
        report["stats"]["start_time"] = report["stats"]["start_time"].isoformat()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(report, indent=2).encode())

    def _serve_dashboard(self):
        """Serve the HTML dashboard."""
        html = self._get_dashboard_html()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def _get_dashboard_html(self) -> str:
        """Generate the dashboard HTML."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Exort Dashboard — Provider Health</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 {
            font-size: 2rem;
            margin-bottom: 8px;
            background: linear-gradient(135deg, #F9E383, #f0c040);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle { color: #888; margin-bottom: 30px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 12px;
            padding: 20px;
            transition: border-color 0.2s;
        }
        .card:hover { border-color: #F9E383; }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .card-title {
            font-size: 1.1rem;
            font-weight: 600;
        }
        .status-badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }
        .status-healthy { background: #1a3a1a; color: #4ade80; }
        .status-degraded { background: #3a3a1a; color: #facc15; }
        .status-dead { background: #3a1a1a; color: #f87171; }
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #222;
        }
        .stat-row:last-child { border-bottom: none; }
        .stat-label { color: #888; }
        .stat-value { font-weight: 500; }
        .key-indicator {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 6px;
        }
        .key-healthy { background: #4ade80; }
        .key-rate-limited { background: #facc15; }
        .key-dead { background: #f87171; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }
        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            color: #F9E383;
        }
        .stat-desc {
            font-size: 0.85rem;
            color: #888;
            margin-top: 5px;
        }
        .footer {
            text-align: center;
            color: #555;
            margin-top: 40px;
            font-size: 0.85rem;
        }
        .footer a { color: #F9E383; text-decoration: none; }
        .auto-refresh {
            display: inline-block;
            padding: 4px 12px;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 20px;
            font-size: 0.8rem;
            color: #888;
        }
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            h1 { font-size: 1.5rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Exort Dashboard</h1>
        <p class="subtitle">Provider Health Monitor — Auto-refreshes every 30s</p>

        <div class="stats-grid" id="global-stats">
            <div class="stat-card">
                <div class="stat-number" id="total-requests">-</div>
                <div class="stat-desc">Total Requests</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="success-rate">-</div>
                <div class="stat-desc">Success Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="active-providers">-</div>
                <div class="stat-desc">Active Providers</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="uptime">-</div>
                <div class="stat-desc">Uptime</div>
            </div>
        </div>

        <div class="grid" id="providers"></div>

        <div class="footer">
            <span class="auto-refresh">Auto-refresh: 30s</span><br><br>
            Powered by <a href="https://github.com/askexort/exort">Exort AI</a> — Free AI for Everyone
        </div>
    </div>

    <script>
        async function fetchHealth() {
            try {
                const resp = await fetch('/api/health');
                const data = await resp.json();
                updateDashboard(data);
            } catch (e) {
                console.error('Failed to fetch health:', e);
            }
        }

        function updateDashboard(data) {
            // Update global stats
            const stats = data.stats;
            document.getElementById('total-requests').textContent = stats.total_requests;
            
            const successRate = stats.total_requests > 0 
                ? Math.round((stats.total_success / stats.total_requests) * 100) + '%'
                : '100%';
            document.getElementById('success-rate').textContent = successRate;

            const activeProviders = data.providers.filter(p => p.available_keys > 0).length;
            document.getElementById('active-providers').textContent = activeProviders;

            // Calculate uptime
            const startTime = new Date(stats.start_time);
            const now = new Date();
            const diff = now - startTime;
            const hours = Math.floor(diff / 3600000);
            const minutes = Math.floor((diff % 3600000) / 60000);
            document.getElementById('uptime').textContent = hours + 'h ' + minutes + 'm';

            // Update provider cards
            const container = document.getElementById('providers');
            container.innerHTML = '';

            for (const provider of data.providers) {
                const status = provider.available_keys > 0 ? 'healthy' 
                    : provider.healthy_keys > 0 ? 'degraded' : 'dead';
                const statusText = status === 'healthy' ? 'Healthy' 
                    : status === 'degraded' ? 'Degraded' : 'Down';

                const card = document.createElement('div');
                card.className = 'card';
                card.innerHTML = `
                    <div class="card-header">
                        <span class="card-title">${provider.name}</span>
                        <span class="status-badge status-${status}">${statusText}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Model</span>
                        <span class="stat-value">${provider.model}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Keys</span>
                        <span class="stat-value">${provider.available_keys}/${provider.total_keys} available</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Requests</span>
                        <span class="stat-value">${stats.provider_usage[provider.name] || 0}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Errors</span>
                        <span class="stat-value">${stats.provider_errors[provider.name] || 0}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Key Status</span>
                        <span class="stat-value">
                            ${provider.keys.map((k, i) => {
                                const cls = k.available ? 'key-healthy' 
                                    : k.rate_limited ? 'key-rate-limited' : 'key-dead';
                                return `<span class="key-indicator ${cls}"></span>`;
                            }).join('')}
                        </span>
                    </div>
                `;
                container.appendChild(card);
            }
        }

        // Initial fetch
        fetchHealth();

        // Auto-refresh every 30 seconds
        setInterval(fetchHealth, 30000);
    </script>
</body>
</html>'''

    def log_message(self, *_):
        pass  # silence request logs


# ─── Global Instance ──────────────────────────────────────────────────────────

_chain: ResilientProviderChain = None

def get_chain() -> ResilientProviderChain:
    """Get or create the global resilient provider chain."""
    global _chain
    if _chain is None:
        _chain = ResilientProviderChain()
    return _chain

def start_dashboard(port: int = 8080):
    """Start the dashboard server."""
    chain = get_chain()
    DashboardHandler.chain = chain
    
    httpd = HTTPServer(("0.0.0.0", port), DashboardHandler)
    Thread(target=httpd.serve_forever, daemon=True).start()
    logger.info(f"Dashboard server on port {port}")
    return httpd
