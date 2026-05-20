"""
Exort Shell — the interactive command-line interface.

Launch with `exort` or `exort shell`.  This is where users
spend most of their time.  It should feel like Exort's own
terminal — not a generic REPL.

Commands use a colon-prefix convention (Exort-native):
    :help           Show commands
    :new            New session
    :status         Engine stats
    :gear           List gear
    :providers      List providers
    :switch <prov>  Switch provider
    :model <name>   Switch model
    :history        Show chat history
    :sessions       List saved sessions
    :load <id>      Resume a session
    :clear          Clear screen
    :skills         List available skills/playbooks
    :quit           Exit

Everything else is sent to the engine as a message.
"""

import os
import sys
import time

import click

from exort.config import Config, ensure_exort_dir
from exort.utils import C, banner, fmt_tokens, fmt_time


def _make_engine(config, provider=None, model=None, verbose=False):
    from exort.engine import Engine
    return Engine(provider=provider, model=model, config=config, verbose=verbose)


def _show_help():
    print(f"""
{C.B}{C.ACC}  Exort Commands{C.RST}
  ─────────────────────────────────────
  {C.CYN}:help{C.RST}            Show this list
  {C.CYN}:new{C.RST}             Start a fresh session
  {C.CYN}:status{C.RST}          Provider, model, token stats
  {C.CYN}:gear{C.RST}            List available gear (tools)
  {C.CYN}:providers{C.RST}       List LLM backends
  {C.CYN}:switch <prov>{C.RST}   Switch LLM provider
  {C.CYN}:model <name>{C.RST}    Switch model
  {C.CYN}:history{C.RST}         Show current conversation
  {C.CYN}:sessions{C.RST}        List saved sessions
  {C.CYN}:load <id>{C.RST}       Resume a session
  {C.CYN}:skills{C.RST}          List available skills/playbooks
  {C.CYN}:clear{C.RST}           Clear screen
  {C.CYN}:quit{C.RST}            Exit

  {C.DIM}Type anything else to talk to the engine.{C.RST}
""")


class ExortShell:
    """The interactive Exort terminal."""

    def __init__(self, engine, config):
        self.engine = engine
        self.cfg = config
        self.running = True

    def run(self):
        banner()
        st = self.engine.status()
        print(f"  {C.DIM}provider: {st['provider']}  model: {st['model']}  gear: {st['gear_count']}{C.RST}")
        print(f"  {C.DIM}type :help for commands, :quit to exit{C.RST}")
        print()

        while self.running:
            try:
                line = self._prompt()
                if not line:
                    continue
                if line.startswith(":"):
                    self._command(line)
                else:
                    self._chat(line)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print(f"\n{C.DIM}goodbye.{C.RST}")
                break

    def _prompt(self) -> str:
        try:
            return input(f"{C.ACC}exort ▸{C.RST} ").strip()
        except (EOFError, KeyboardInterrupt):
            raise

    def _command(self, line: str):
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in (":quit", ":q", ":exit"):
            print(f"{C.DIM}goodbye.{C.RST}")
            self.running = False

        elif cmd == ":help":
            _show_help()

        elif cmd == ":new":
            self.engine.open("new session")
            print(f"{C.GRN}✓ new session started{C.RST}")

        elif cmd == ":status":
            s = self.engine.status()
            t = s["tokens"]
            print(f"""
{C.B}  Engine Status{C.RST}
  ──────────────────────────────
  provider    {C.ACC}{s['provider']}{C.RST}
  model       {s['model']}
  session     {s['session'] or '(none)'}
  turns       {s['turns']}
  gear calls  {s['gear_calls']}
  tokens      {t['prompt_tok']} in / {t['completion_tok']} out / {t['total_tok']} total
  gear        {s['gear_count']} available
""")

        elif cmd == ":gear":
            names = self.engine.gear.names()
            cats = self.engine.gear.categories()
            print(f"\n{C.B}  Gear ({len(names)} total){C.RST}")
            for cat, items in cats.items():
                print(f"\n  {C.ACC}{cat.upper()}{C.RST}")
                for n in items:
                    g = self.engine.gear._gear[n]
                    warn = f" {C.RED}⚠ unsafe{C.RST}" if g.unsafe else ""
                    desc = g.spec.info[:70]
                    print(f"    {C.CYN}{n}{C.RST}{warn}")
                    print(f"      {C.DIM}{desc}{C.RST}")
            print()

        elif cmd == ":providers":
            from exort.providers import list_providers, provider_info
            ps = provider_info()
            print(f"\n{C.B}  Providers ({len(ps)}){C.RST}")
            for p in ps:
                cur = f" {C.ACC}← current{C.RST}" if p["name"] == self.engine._prov_name else ""
                free = f" {C.GRN}free{C.RST}" if p.get("needs_key") is False else ""
                print(f"  {C.CYN}{p['name']}{C.RST}{free}{cur}")
            print()

        elif cmd == ":switch":
            if not arg:
                print(f"  usage: :switch <provider>")
                return
            try:
                self.engine = _make_engine(self.cfg, provider=arg)
                print(f"{C.GRN}✓ switched to {arg}{C.RST}")
            except Exception as e:
                print(f"{C.RED}✗ {e}{C.RST}")

        elif cmd == ":model":
            if not arg:
                print(f"  current: {self.engine._model or 'default'}")
                print(f"  usage: :model <model_name>")
            else:
                self.engine._model = arg
                print(f"{C.GRN}✓ model → {arg}{C.RST}")

        elif cmd == ":history":
            for m in self.engine._history[-20:]:
                role = m["role"]
                txt = m.get("content", "")[:100]
                if role == "user":
                    print(f"  {C.CYN}you:{C.RST} {txt}")
                elif role == "assistant":
                    print(f"  {C.GRN}exort:{C.RST} {txt}")
            print()

        elif cmd == ":sessions":
            sessions = self.engine.mem.recent(10)
            if sessions:
                print(f"\n{C.B}  Sessions{C.RST}")
                for s in sessions:
                    print(f"  {C.CYN}{s['id']}{C.RST}  {s['title']}  ({s['updated'][:10]})")
                print()
            else:
                print(f"  {C.DIM}no saved sessions{C.RST}")

        elif cmd == ":load":
            if not arg:
                print("  usage: :load <session_id>")
            else:
                try:
                    self.engine.resume(arg)
                    title = self.engine.mem.title(arg)
                    print(f"{C.GRN}✓ loaded: {title}{C.RST}")
                except Exception as e:
                    print(f"{C.RED}✗ {e}{C.RST}")

        elif cmd == ":skills":
            from exort.playbooks.library import PlaybookLibrary
            lib = PlaybookLibrary()
            lib.load()
            books = lib.list_all()
            print(f"\n{C.B}  Skills & Playbooks ({len(books)}){C.RST}")
            for b in books:
                origin_tag = f" {C.GRN}built-in{C.RST}" if b["origin"] == "builtin" else f" {C.DIM}user{C.RST}"
                print(f"  {C.CYN}{b['name']}{C.RST}{origin_tag}")
            print(f"\n  {C.DIM}Load: exort config set playbooks.autoload ['skill-name']{C.RST}")
            print()

        elif cmd == ":clear":
            os.system("cls" if os.name == "nt" else "clear")

        else:
            print(f"  {C.DIM}unknown command: {cmd} — type :help{C.RST}")

    def _chat(self, text: str):
        """Send message to engine and display response."""
        t0 = time.time()
        print(f"\n{C.GRN}exort ▸{C.RST} ", end="", flush=True)

        try:
            full = ""
            for chunk in self.engine.talk(text, stream=True):
                print(chunk, end="", flush=True)
                full += chunk
            print()

            elapsed = time.time() - t0
            st = self.engine.stats
            if self.cfg.get("display.show_tokens"):
                line = f"{C.DIM}  [{fmt_time(elapsed)}"
                if st.get("total_tok"):
                    line += f" | {fmt_tokens(st)}"
                line += f" | {st.get('gear_calls', 0)} gear]{C.RST}"
                print(line)

        except KeyboardInterrupt:
            print(f"\n{C.YEL}  interrupted{C.RST}")
        except Exception as e:
            print(f"\n{C.RED}  error: {e}{C.RST}")

        print()


# ══════════════════════════════════════════════════════════
# CLI entry points (click)
# ══════════════════════════════════════════════════════════

@click.group()
@click.version_option(version="2.1.0", prog_name="exort")
def cli():
    """Exort — The Open Agent Engine. Free AI for Everyone."""
    ensure_exort_dir()


@cli.command()
@click.argument("question", required=False)
@click.option("--provider", "-p", help="LLM provider (groq, openai, ollama, anthropic, ...)")
@click.option("--model", "-m", help="Model name")
@click.option("--verbose", "-v", is_flag=True, help="Show gear calls")
def shell(question, provider, model, verbose):
    """Launch the interactive Exort shell.

    \b
    Examples:
        exort shell                  # interactive mode
        exort shell "what is Rust?"  # one-shot
        exort shell -p ollama        # use local Ollama
    """
    cfg = Config()
    engine = _make_engine(cfg, provider=provider, model=model, verbose=verbose)

    if question:
        for chunk in engine.talk(question, stream=True):
            print(chunk, end="", flush=True)
        print()
    else:
        ExortShell(engine, cfg).run()


@cli.command()
@click.argument("question", required=False)
@click.option("--provider", "-p")
@click.option("--model", "-m")
@click.option("--verbose", "-v", is_flag=True)
def ask(question, provider, model, verbose):
    """Ask a single question (no interactive mode).

    \b
    Examples:
        exort ask "what is the capital of France?"
        exort ask -p ollama "explain recursion"
    """
    cfg = Config()
    engine = _make_engine(cfg, provider=provider, model=model, verbose=verbose)
    if not question:
        print("Usage: exort ask <question>")
        return
    for chunk in engine.talk(question, stream=True):
        print(chunk, end="", flush=True)
    print()


@cli.command()
@click.argument("action", required=False)
@click.argument("key", required=False)
@click.argument("value", required=False)
def config(action, key, value):
    """View or change Exort configuration.

    \b
    Examples:
        exort config show
        exort config set engine.provider openai
        exort config get engine.temperature
    """
    cfg = Config()
    if action == "show" or action is None:
        try:
            import yaml
            print(f"\n{C.B}Config: {cfg._path}{C.RST}\n")
            print(yaml.dump(cfg.data, default_flow_style=False))
        except ImportError:
            for k, v in cfg.data.items():
                print(f"  {k}: {v}")
    elif action == "set" and key and value:
        try:
            import json
            value = json.loads(value)
        except Exception:
            pass
        cfg.set(key, value)
        cfg.save()
        print(f"{C.GRN}✓ {key} = {value}{C.RST}")
    elif action == "get" and key:
        print(f"{key} = {cfg.get(key)}")
    else:
        print("Usage: exort config [show|set|get] [key] [value]")


@cli.group()
def providers():
    """Manage LLM providers."""
    pass


@providers.command("list")
def providers_list():
    """List all available providers."""
    from exort.providers import provider_info
    cfg = Config()
    current = cfg.get("engine.provider")
    ps = provider_info()
    print(f"\n{C.B}  Available Providers ({len(ps)}){C.RST}\n")
    for p in ps:
        cur = f" {C.ACC}← current{C.RST}" if p["name"] == current else ""
        key = "no key needed" if not p["needs_key"] else "API key required"
        print(f"  {C.CYN}{p['name']}{C.RST}  {C.DIM}{key}{C.RST}{cur}")
    print()


@providers.command("add")
@click.argument("name")
@click.option("--key", "-k", help="API key to save")
@click.option("--endpoint", "-e", help="Custom endpoint URL")
@click.option("--model", "-m", help="Default model")
def providers_add(name, key, endpoint, model):
    """Add or configure a provider.

    \b
    Examples:
        exort providers add groq --key gsk_xxx
        exort providers add together --key sk-xxx
        exort providers add custom --endpoint http://localhost:8000/v1 --model my-model
    """
    from exort.providers import list_providers
    cfg = Config()

    available = list_providers()

    # For custom provider, allow any name
    if name == "custom":
        if not endpoint:
            print(f"{C.RED}✗ Custom provider requires --endpoint{C.RST}")
            return
        cfg.set(f"providers.custom.endpoint", endpoint)
        if model:
            cfg.set(f"providers.custom.model", model)
        if key:
            cfg.set(f"providers.custom.key_var", f"CUSTOM_API_KEY")
            _save_env_key("CUSTOM_API_KEY", key)
        cfg.save()
        print(f"{C.GRN}✓ Custom provider configured{C.RST}")
        return

    if name not in available:
        print(f"{C.RED}✗ Unknown provider: {name}{C.RST}")
        print(f"  Available: {', '.join(available)}")
        print(f"  For custom endpoints: exort providers add custom --endpoint <url>")
        return

    # Update existing provider
    if endpoint:
        cfg.set(f"providers.{name}.endpoint", endpoint)
    if model:
        cfg.set(f"providers.{name}.model", model)
    if key:
        key_var = cfg.get(f"providers.{name}.key_var", f"{name.upper()}_API_KEY")
        _save_env_key(key_var, key)
        print(f"{C.GRN}✓ API key saved to .env as {key_var}{C.RST}")

    cfg.save()
    print(f"{C.GRN}✓ Provider '{name}' configured{C.RST}")


@providers.command("remove")
@click.argument("name")
def providers_remove(name):
    """Remove a provider configuration."""
    cfg = Config()
    if name not in cfg.get("providers", {}):
        print(f"{C.RED}✗ Provider '{name}' not in config{C.RST}")
        return
    cfg.data["providers"].pop(name, None)
    cfg.save()
    print(f"{C.GRN}✓ Provider '{name}' removed from config{C.RST}")


@providers.command("test")
@click.argument("name", required=False)
def providers_test(name):
    """Test a provider connection (or test all).

    \b
    Examples:
        exort providers test groq
        exort providers test
    """
    from exort.providers import list_providers, get_provider
    import os
    cfg = Config()

    def _test(prov_name):
        try:
            pcfg = cfg.provider_conf(prov_name)
            key = cfg.api_key(prov_name)
            if pcfg.get("key_var") and not key:
                return None  # no key configured
            p = get_provider(prov_name, api_key=key,
                           base_url=pcfg.get("endpoint"),
                           default_model=pcfg.get("model"))
            if not p.ok():
                return False
            resp = p.chat([{"role": "user", "content": "Say 'ok' in one word."}],
                         max_tokens=10, stream=False)
            return bool(resp.content)
        except Exception as e:
            return str(e)

    if name:
        result = _test(name)
        if result is True:
            print(f"{C.GRN}✓ {name}: OK{C.RST}")
        elif result is None:
            print(f"{C.YEL}? {name}: No API key configured{C.RST}")
        elif result is False:
            print(f"{C.RED}✗ {name}: Connection failed{C.RST}")
        else:
            print(f"{C.RED}✗ {name}: {result}{C.RST}")
    else:
        print(f"\n{C.B}  Testing All Providers{C.RST}\n")
        for p in list_providers():
            if p == "custom":
                continue
            result = _test(p)
            if result is True:
                print(f"  {C.GRN}✓{C.RST} {p}")
            elif result is None:
                print(f"  {C.DIM}○ {p} (no key){C.RST}")
            elif result is False:
                print(f"  {C.RED}✗ {p} (failed){C.RST}")
            else:
                print(f"  {C.RED}✗ {p} ({result[:50]}){C.RST}")
        print()


# ── Provider setup wizard data ──────────────────────────────────────────────

_PROVIDER_CATALOG = {
    # ── Free Providers (no credit card) ──
    "free": {
        "title": "Free Providers (no credit card needed)",
        "providers": [
            ("groq", "GROQ_API_KEY", "https://console.groq.com", "llama-3.3-70b-versatile", "Fast inference, 100K tok/day free"),
            ("cerebras", "CEREBRAS_API_KEY", "https://cloud.cerebras.ai", "llama-3.3-70b", "Ultra-fast, 1M tok/day free"),
            ("sambanova", "SAMBANOVA_API_KEY", "https://cloud.sambanova.ai", "Meta-Llama-3.1-8B-Instruct", "Fast inference, free tier"),
            ("nvidia", "NVIDIA_API_KEY", "https://build.nvidia.com", "nvidia/llama-3.3-nemotron-super-49b-a3b", "NVIDIA NIM, free tier"),
            ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai", "meta-llama/llama-3.3-70b-instruct:free", "200+ models, many free"),
            ("gemini", "GEMINI_API_KEY", "https://aistudio.google.com", "gemini-2.0-flash", "Google Gemini, free tier"),
            ("ollama", None, "http://localhost:11434", "llama3.1", "Local models, unlimited"),
            ("ollama_cloud", "OLLAMA_CLOUD_API_KEY", "https://ollama.com", "nemotron-3-nano:30b", "Ollama cloud inference"),
            ("huggingface", "HF_TOKEN", "https://huggingface.co", "meta-llama/Meta-Llama-3.1-70B-Instruct", "Serverless free inference"),
            ("novita", "NOVITA_API_KEY", "https://novita.ai", "deepseek/deepseek-v3-0324", "AI-native cloud, free tier"),
            ("nous", "NOUS_API_KEY", "https://nousresearch.com", "Hermes-3-Llama-3.1-70B", "Nous Research portal"),
            ("deepinfra", "DEEPINFRA_API_KEY", "https://deepinfra.com", "meta-llama/Meta-Llama-3.1-70B-Instruct", "Cheap inference, free models"),
            ("lepton", "LEPTON_API_KEY", "https://lepton.ai", "llama-3.3-70b", "Fast API, free tier"),
            ("nebius", "NEBIUS_API_KEY", "https://studio.nebius.ai", "meta-llama/Meta-Llama-3.1-70B-Instruct", "Nebius AI Studio, free"),
            ("gmi", "GMI_API_KEY", "https://www.gmicloud.ai", "deepseek-ai/DeepSeek-R1", "GMI Cloud, free tier"),
            ("baseten", "BASETEN_API_KEY", "https://baseten.co", "meta-llama/Meta-Llama-3.1-70B-Instruct", "Model serving, free tier"),
            ("anyscale", "ANYSCALE_API_KEY", "https://anyscale.com", "meta-llama/Meta-Llama-3.1-70B-Instruct", "Anyscale endpoints"),
            ("textsynth", "TEXTSYNTH_API_KEY", "https://textsynth.com", "Mistral-7B-v0.3", "Free inference"),
            ("mimo", "MIMO_API_KEY", "https://mimo.xiaomi.com", "mimo-v2.5-pro", "Xiaomi MiMo, free"),
            ("stepfun", "STEPFUN_API_KEY", "https://stepfun.com", "step-3.5-flash", "StepFun, free tier"),
        ],
    },
    # ── Paid Providers ──
    "paid": {
        "title": "Paid Providers",
        "providers": [
            ("openai", "OPENAI_API_KEY", "https://platform.openai.com", "gpt-4o-mini", "GPT-4, GPT-4o, DALL-E"),
            ("anthropic", "ANTHROPIC_API_KEY", "https://console.anthropic.com", "claude-sonnet-4-20250514", "Claude 4, Sonnet, Haiku"),
            ("deepseek", "DEEPSEEK_API_KEY", "https://platform.deepseek.com", "deepseek-chat", "Strong reasoning, cheap"),
            ("mistral", "MISTRAL_API_KEY", "https://console.mistral.ai", "mistral-large-latest", "European AI, free tier"),
            ("together", "TOGETHER_API_KEY", "https://api.together.xyz", "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", "Open models, cheap"),
            ("fireworks", "FIREWORKS_API_KEY", "https://fireworks.ai", "accounts/fireworks/models/llama-v3p3-70b-instruct", "Fast inference"),
            ("perplexity", "PERPLEXITY_API_KEY", "https://perplexity.ai", "sonar-pro", "Search-augmented AI"),
            ("cohere", "COHERE_API_KEY", "https://cohere.com", "command-r-plus", "Enterprise AI"),
            ("replicate", "REPLICATE_API_TOKEN", "https://replicate.com", "meta/meta-llama-3.1-405b-instruct", "Run any model"),
            ("xai", "XAI_API_KEY", "https://x.ai", "grok-3", "xAI Grok"),
            ("moonshot", "MOONSHOT_API_KEY", "https://platform.moonshot.cn", "moonshot-v1-128k", "Moonshot AI, 128K context"),
            ("kimi", "KIMI_API_KEY", "https://platform.moonshot.cn", "kimi-k2", "Kimi Coding, 128K context"),
            ("siliconflow", "SILICONFLOW_API_KEY", "https://siliconflow.cn", "Qwen/Qwen2.5-72B-Instruct", "Chinese model hub"),
            ("minimax", "MINIMAX_API_KEY", "https://platform.minimax.io", "MiniMax-M2.7", "MiniMax M-series"),
            ("qwen", "DASHSCOPE_API_KEY", "https://dashscope.aliyun.com", "qwen-plus", "Alibaba Qwen (DashScope)"),
            ("arcee", "ARCEEAI_API_KEY", "https://arcee.ai", "arcee-spotlight", "Arcee AI"),
            ("zai", "ZAI_API_KEY", "https://z.ai", "glm-4-flash", "Z.AI / Zhipu GLM"),
            ("zhipu", "ZHIPU_API_KEY", "https://open.bigmodel.cn", "glm-4-flash", "Zhipu AI (China endpoint)"),
            ("volcengine", "VOLCENGINE_API_KEY", "https://console.volcengine.com", "doubao-1.5-pro-256k", "ByteDance Doubao"),
            ("yi", "YI_API_KEY", "https://platform.lingyiwanwu.com", "yi-large", "01.AI Yi models"),
            ("baichuan", "BAICHUAN_API_KEY", "https://platform.baichuan-ai.com", "Baichuan4", "Baichuan AI"),
            ("writer", "WRITER_API_KEY", "https://writer.com", "palmyra-x-004", "Writer (Palmyra)"),
            ("ai21", "AI21_API_KEY", "https://studio.ai21.com", "jamba-1.5-large", "AI21 Jamba"),
            ("upstage", "UPSTAGE_API_KEY", "https://console.upstage.ai", "solar-1-mini-chat", "Upstage Solar"),
            ("lambda", "LAMBDA_API_KEY", "https://lambdalabs.com", "llama3.3-70b-instruct", "Lambda Cloud"),
            ("databricks", "DATABRICKS_API_KEY", "https://databricks.com", "dbrx-instruct", "Databricks (needs host)"),
            ("voyage", "VOYAGE_API_KEY", "https://voyageai.com", "voyage-3", "Voyage AI"),
        ],
    },
}


@providers.command("setup-all")
@click.option("--category", "-c", type=click.Choice(["free", "paid", "all"]), default="all",
              help="Which providers to set up")
@click.option("--batch", "-b", is_flag=True, help="Batch mode: enter keys one by one")
def providers_setup_all(category, batch):
    """Interactive setup wizard for ALL providers at once.

    Walks through every provider, asks for API keys, and saves them
    to ~/.exort/.env. Skips providers that already have keys.

    \b
    Examples:
        exort providers setup-all                 # interactive, all providers
        exort providers setup-all -c free         # only free providers
        exort providers setup-all -c paid         # only paid providers
        exort providers setup-all --batch         # batch mode (no descriptions)
    """
    from exort.config import exort_dir
    cfg = Config()
    d = exort_dir()

    # Load existing keys
    env_path = d / ".env"
    existing = {}
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()

    # Determine which categories to show
    cats_to_show = []
    if category in ("all", "free"):
        cats_to_show.append("free")
    if category in ("all", "paid"):
        cats_to_show.append("paid")

    total_configured = 0
    total_skipped = 0
    new_keys = []

    print(f"\n{C.B}  Exort Provider Setup — Configure All Providers{C.RST}")
    print(f"  {'─' * 55}")
    print(f"  {C.DIM}Press Enter to skip, 'q' to quit{C.RST}\n")

    for cat_key in cats_to_show:
        cat = _PROVIDER_CATALOG[cat_key]
        print(f"\n  {C.ACC}{cat['title']}{C.RST}")
        print(f"  {'─' * 50}")

        for name, key_var, signup_url, default_model, desc in cat["providers"]:
            # Check if already configured
            if key_var and key_var in existing and existing[key_var]:
                status = f"{C.GRN}✓ already set{C.RST}"
                if not batch:
                    print(f"\n    {C.CYN}{name}{C.RST} — {desc}")
                    print(f"      {status}  ({key_var}=***{existing[key_var][-4:]})")
                    ans = input(f"      Replace? [skip]: ").strip().lower()
                    if ans not in ("y", "yes"):
                        total_skipped += 1
                        continue
                else:
                    total_skipped += 1
                    continue
            else:
                if not batch:
                    print(f"\n    {C.CYN}{name}{C.RST} — {desc}")
                    print(f"      Model: {default_model}")
                    if signup_url:
                        print(f"      Get key: {C.DIM}{signup_url}{C.RST}")

            if not key_var:
                # No key needed (e.g. ollama)
                print(f"    {C.CYN}{name}{C.RST} — No key needed (local)")
                total_configured += 1
                continue

            try:
                key = input(f"      {key_var}: ").strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n  {C.YEL}Interrupted. Saving progress...{C.RST}")
                break

            if key.lower() == "q":
                print(f"\n  {C.YEL}Stopping. Saving configured keys...{C.RST}")
                break

            if key:
                new_keys.append((key_var, key))
                existing[key_var] = key
                total_configured += 1
                print(f"      {C.GRN}✓ saved{C.RST}")
            else:
                total_skipped += 1

    # Save all new keys to .env
    if new_keys:
        d.mkdir(parents=True, exist_ok=True)
        # Read existing content
        lines = []
        if env_path.exists():
            with open(env_path, "r") as f:
                lines = f.readlines()

        # Remove keys we're updating
        keys_to_update = {k for k, _ in new_keys}
        lines = [l for l in lines if not any(
            l.strip().startswith(f"{k}=") for k in keys_to_update
        )]

        # Add new keys
        for key_var, key in new_keys:
            lines.append(f"{key_var}={key}\n")
            os.environ[key_var] = key

        with open(env_path, "w") as f:
            f.writelines(lines)

    # Optionally set default provider
    print(f"\n  {'─' * 50}")
    print(f"  {C.B}Summary:{C.RST} {total_configured} configured, {total_skipped} skipped")

    if total_configured > 0:
        try:
            set_default = input(f"\n  Set default provider? [groq]: ").strip()
        except (EOFError, KeyboardInterrupt):
            set_default = ""

        if set_default:
            from exort.providers import list_providers
            available = list_providers()
            if set_default in available:
                cfg.set("engine.provider", set_default)
                cfg.save()
                print(f"  {C.GRN}✓ Default provider → {set_default}{C.RST}")
            else:
                print(f"  {C.YEL}? Unknown provider: {set_default}{C.RST}")
        else:
            cfg.set("engine.provider", "groq")
            cfg.save()
            print(f"  {C.GRN}✓ Default provider → groq{C.RST}")

    print(f"\n  {C.GRN}✓ Setup complete! Run 'exort shell' to start.{C.RST}")
    print(f"  {C.DIM}Keys saved to: {env_path}{C.RST}\n")


@providers.command("setup-free")
def providers_setup_free():
    """Quick setup: configure only free providers (no credit card needed).

    \b
    Shortcut for: exort providers setup-all --category free
    """
    from exort.config import exort_dir
    cfg = Config()
    d = exort_dir()

    # Load existing keys
    env_path = d / ".env"
    existing = {}
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()

    cat = _PROVIDER_CATALOG["free"]
    new_keys = []
    configured = 0

    print(f"\n{C.B}  Free Provider Setup{C.RST}")
    print(f"  {'─' * 40}")
    print(f"  {C.DIM}Press Enter to skip, 'q' to quit{C.RST}\n")

    for name, key_var, signup_url, default_model, desc in cat["providers"]:
        if not key_var:
            print(f"    {C.CYN}{name}{C.RST} — {desc} {C.GRN}(no key needed){C.RST}")
            configured += 1
            continue

        if key_var in existing and existing[key_var]:
            print(f"    {C.CYN}{name}{C.RST} — {C.GRN}✓ already set{C.RST}")
            configured += 1
            continue

        print(f"\n    {C.CYN}{name}{C.RST} — {desc}")
        if signup_url:
            print(f"    Get key: {C.DIM}{signup_url}{C.RST}")

        try:
            key = input(f"    {key_var}: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if key.lower() == "q":
            break

        if key:
            new_keys.append((key_var, key))
            existing[key_var] = key
            configured += 1
            print(f"    {C.GRN}✓ saved{C.RST}")

    # Save keys
    if new_keys:
        d.mkdir(parents=True, exist_ok=True)
        lines = []
        if env_path.exists():
            with open(env_path, "r") as f:
                lines = f.readlines()
        keys_to_update = {k for k, _ in new_keys}
        lines = [l for l in lines if not any(l.strip().startswith(f"{k}=") for k in keys_to_update)]
        for key_var, key in new_keys:
            lines.append(f"{key_var}={key}\n")
            os.environ[key_var] = key
        with open(env_path, "w") as f:
            f.writelines(lines)

    cfg.set("engine.provider", "groq")
    cfg.save()

    print(f"\n  {C.GRN}✓ {configured} free providers configured!{C.RST}")
    print(f"  {C.GRN}✓ Default → groq. Run 'exort shell' to start.{C.RST}\n")


@providers.command("env-show")
def providers_env_show():
    """Show all configured API keys (masked) and their status.

    Reads from ~/.exort/.env and shows which providers have keys set.
    """
    from exort.config import exort_dir
    d = exort_dir()
    env_path = d / ".env"

    if not env_path.exists():
        print(f"\n  {C.YEL}No .env file found at {env_path}{C.RST}")
        print(f"  Run 'exort providers setup-all' to configure.\n")
        return

    # Read env file
    keys = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                keys[k.strip()] = v.strip()

    # Map key vars to provider names
    key_to_provider = {}
    for cat in _PROVIDER_CATALOG.values():
        for name, key_var, _, _, _ in cat["providers"]:
            if key_var:
                key_to_provider[key_var] = name

    print(f"\n{C.B}  Configured API Keys ({len(keys)} total){C.RST}")
    print(f"  {C.DIM}{env_path}{C.RST}")
    print(f"  {'─' * 50}")

    for key_var, value in sorted(keys.items()):
        provider = key_to_provider.get(key_var, "unknown")
        masked = f"***{value[-4:]}" if len(value) > 4 else "***"
        status = f"{C.GRN}✓{C.RST}" if value else f"{C.RED}✗ empty{C.RST}"
        print(f"  {status} {C.CYN}{provider:<18}{C.RST} {key_var}={masked}")

    # Show which providers have no keys
    configured_vars = set(keys.keys())
    missing = []
    for cat in _PROVIDER_CATALOG.values():
        for name, key_var, _, _, _ in cat["providers"]:
            if key_var and key_var not in configured_vars:
                missing.append((name, key_var))

    if missing:
        print(f"\n  {C.DIM}Not configured:{C.RST}")
        for name, key_var in missing[:10]:
            print(f"    {C.DIM}○ {name} ({key_var}){C.RST}")
        if len(missing) > 10:
            print(f"    {C.DIM}... and {len(missing) - 10} more{C.RST}")

    print()


@cli.command()
def gear():
    """List available gear (tools)."""
    from exort.tools.gear import GearBox
    gb = GearBox()
    gb.discover()
    cats = gb.categories()
    print(f"\n{C.B}Gear ({len(gb)} total){C.RST}")
    for cat, items in cats.items():
        print(f"\n  {C.ACC}{cat.upper()}{C.RST}")
        for n in items:
            g = gb._gear[n]
            warn = " ⚠" if g.unsafe else ""
            print(f"    {C.CYN}{n}{C.RST}{warn}")
            print(f"      {C.DIM}{g.spec.info[:80]}{C.RST}")
    print()


@cli.command()
def skills():
    """List available skills/playbooks."""
    from exort.playbooks.library import PlaybookLibrary
    lib = PlaybookLibrary()
    lib.load()
    books = lib.list_all()

    builtin = [b for b in books if b["origin"] == "builtin"]
    user = [b for b in books if b["origin"] == "user"]

    print(f"\n{C.B}  Skills & Playbooks ({len(books)} total){C.RST}")

    if builtin:
        print(f"\n  {C.GRN}Built-in ({len(builtin)}){C.RST}")
        for b in builtin:
            print(f"    {C.CYN}{b['name']}{C.RST}")

    if user:
        print(f"\n  {C.ACC}User-created ({len(user)}){C.RST}")
        for b in user:
            print(f"    {C.CYN}{b['name']}{C.RST}  {C.DIM}{b['path']}{C.RST}")

    print(f"\n  {C.DIM}To create: save .md files to ~/.exort/playbooks/{C.RST}")
    print(f"  {C.DIM}To load: exort config set playbooks.autoload ['name']{C.RST}")
    print()


@cli.command()
def bot():
    """Start the Telegram bot."""
    cfg = Config()
    token = os.environ.get(cfg.get("telegram.token_var", "TELEGRAM_BOT_TOKEN"))
    if not token:
        print(f"{C.RED}TELEGRAM_BOT_TOKEN not set.{C.RST}")
        print(f"Add it to ~/.exort/.env")
        return
    from exort.bot.telegram_bot import run_bot
    run_bot(token, cfg)


@cli.command()
def setup():
    """First-time setup wizard. Configure ALL 49 providers interactively."""
    banner()
    print(f"{C.B}  Exort Setup Wizard — All 49 Providers{C.RST}\n")

    cfg = Config()
    d = ensure_exort_dir()
    print(f"  data dir: {d}\n")

    # Load existing keys
    env_path = d / ".env"
    existing = {}
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    existing[k.strip()] = v.strip()

    # ── Phase 1: Pick default provider ──
    print(f"  {C.B}Step 1:{C.RST} Choose your default provider\n")

    # Build flat list from catalog
    all_providers = []
    for cat_key in ("free", "paid"):
        cat = _PROVIDER_CATALOG[cat_key]
        for name, key_var, signup_url, default_model, desc in cat["providers"]:
            tag = "free" if cat_key == "free" else "paid"
            all_providers.append((name, key_var, signup_url, default_model, desc, tag))

    # Print in two columns
    for i, (name, _, _, model, desc, tag) in enumerate(all_providers, 1):
        num = f"{i:>2}"
        tag_color = C.GRN if tag == "free" else C.YEL
        status = ""
        key_var = all_providers[i-1][1]
        if key_var and key_var in existing and existing[key_var]:
            status = f" {C.GRN}✓{C.RST}"
        print(f"    {C.CYN}{num}{C.RST}. {name:<16} {tag_color}[{tag}]{C.RST} {desc}{status}")

    print(f"\n  {C.DIM}Enter number or provider name{C.RST}")
    try:
        choice = input(f"  choice [1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        return

    # Parse choice
    prov = None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(all_providers):
            prov = all_providers[idx][0]
    else:
        # Direct name
        choice_lower = choice.lower()
        for name, *_ in all_providers:
            if name == choice_lower:
                prov = name
                break
    prov = prov or "groq"

    cfg.set("engine.provider", prov)
    print(f"\n  {C.GRN}✓ Default provider → {prov}{C.RST}")

    # ── Phase 2: Configure selected provider key ──
    print(f"\n  {C.B}Step 2:{C.RST} Configure API key for {C.ACC}{prov}{C.RST}\n")

    # Find the selected provider's info
    selected = None
    for name, key_var, signup_url, default_model, desc, tag in all_providers:
        if name == prov:
            selected = (name, key_var, signup_url, default_model, desc, tag)
            break

    if selected:
        name, key_var, signup_url, default_model, desc, tag = selected

        if not key_var:
            print(f"    {C.CYN}{name}{C.RST} — No API key needed (local)")
        elif key_var in existing and existing[key_var]:
            masked = f"***{existing[key_var][-4:]}" if len(existing[key_var]) > 4 else "***"
            print(f"    {C.CYN}{name}{C.RST} — {C.GRN}✓ already set{C.RST} ({key_var}={masked})")
            ans = input(f"    Replace? [skip]: ").strip().lower()
            if ans in ("y", "yes"):
                tag_color = C.GRN if tag == "free" else C.YEL
                print(f"\n    {C.CYN}{name}{C.RST} {tag_color}[{tag}]{C.RST} — {desc}")
                if signup_url:
                    print(f"    {C.DIM}Get key: {signup_url}{C.RST}")
                try:
                    key = input(f"    {key_var}: ").strip()
                except (EOFError, KeyboardInterrupt):
                    key = ""
                if key:
                    _save_env_key(key_var, key)
                    print(f"    {C.GRN}✓ saved{C.RST}")
        else:
            tag_color = C.GRN if tag == "free" else C.YEL
            print(f"    {C.CYN}{name}{C.RST} {tag_color}[{tag}]{C.RST} — {desc}")
            if signup_url:
                print(f"    {C.DIM}Get key: {signup_url}{C.RST}")
            try:
                key = input(f"    {key_var}: ").strip()
            except (EOFError, KeyboardInterrupt):
                key = ""
            if key:
                _save_env_key(key_var, key)
                print(f"    {C.GRN}✓ saved{C.RST}")

    # ── Phase 3: Optionally configure more providers ──
    print(f"\n  {C.B}Step 3:{C.RST} Configure more providers? (optional)\n")
    try:
        more = input(f"  Add more keys? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        more = ""

    if more in ("y", "yes"):
        print(f"\n  {C.DIM}Press Enter to skip, 'q' to quit{C.RST}\n")
        configured = 0
        for name, key_var, signup_url, default_model, desc, tag in all_providers:
            if name == prov:
                continue  # Skip the one we already configured
            if not key_var:
                continue
            if key_var in existing and existing[key_var]:
                continue  # Skip already set

            tag_color = C.GRN if tag == "free" else C.YEL
            print(f"    {C.CYN}{name}{C.RST} {tag_color}[{tag}]{C.RST} — {desc}")
            if signup_url:
                print(f"    {C.DIM}Get key: {signup_url}{C.RST}")
            try:
                key = input(f"    {key_var}: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if key.lower() == "q":
                break
            if key:
                _save_env_key(key_var, key)
                configured += 1
                print(f"    {C.GRN}✓ saved{C.RST}")

        if configured:
            print(f"\n  {C.GRN}✓ {configured} more keys configured{C.RST}")

    # ── Summary ──
    cfg.save()
    print(f"\n  {'─' * 50}")
    print(f"  {C.B}Setup Complete!{C.RST}")
    print(f"    Default provider: {C.ACC}{prov}{C.RST}")
    print(f"\n  Next steps:")
    print(f"    {C.CYN}exort shell{C.RST}         Start chatting")
    print(f"    {C.CYN}exort providers list{C.RST}  See all providers")
    print(f"    {C.CYN}exort providers test{C.RST}  Test connections")
    print()


def _save_env_key(key_var: str, key: str):
    """Save an API key to ~/.exort/.env"""
    from exort.config import exort_dir
    d = exort_dir()
    d.mkdir(parents=True, exist_ok=True)
    env = d / ".env"

    # Read existing, remove old key if present
    lines = []
    if env.exists():
        with open(env, "r") as f:
            lines = f.readlines()
    lines = [l for l in lines if not l.strip().startswith(f"{key_var}=")]
    lines.append(f"{key_var}={key}\n")

    with open(env, "w") as f:
        f.writelines(lines)
    os.environ[key_var] = key


# ══════════════════════════════════════════════════════════
# Additional CLI Commands
# ══════════════════════════════════════════════════════════

@cli.command()
@click.argument("name")
@click.argument("body", required=False)
@click.option("--file", "-f", help="Load playbook from file")
def playbook(name, body, file):
    """Create or view a playbook (skill).

    \b
    Examples:
        exort playbook my-skill "# My Skill\\nInstructions here..."
        exort playbook my-skill --file skill.md
        exort playbook list
    """
    from exort.playbooks.library import PlaybookLibrary
    lib = PlaybookLibrary()
    lib.load()

    if name == "list":
        books = lib.list_all()
        print(f"\\n{C.B}Playbooks ({len(books)}){C.RST}")
        for b in books:
            tag = f"{C.GRN}built-in{C.RST}" if b["origin"] == "builtin" else f"{C.ACC}user{C.RST}"
            print(f"  {C.CYN}{b['name']}{C.RST}  [{tag}]")
        print()
        return

    if name == "delete":
        if body:
            from exort.config import exort_dir
            p = exort_dir() / "playbooks" / f"{body}.md"
            if p.exists():
                p.unlink()
                print(f"{C.GRN}✓ Deleted playbook: {body}{C.RST}")
            else:
                print(f"{C.RED}✗ Playbook not found: {body}{C.RST}")
        else:
            print("Usage: exort playbook delete <name>")
        return

    if file:
        import pathlib
        p = pathlib.Path(file)
        if not p.exists():
            print(f"{C.RED}✗ File not found: {file}{C.RST}")
            return
        body = p.read_text(encoding="utf-8")

    if not body:
        # Show existing playbook
        matches = lib.find(name)
        if matches:
            pb = matches[0]
            print(f"\\n{C.B}Playbook: {pb.name}{C.RST} [{pb.origin}]")
            print(f"{C.DIM}{pb.path}{C.RST}\\n")
            print(pb.body[:3000])
        else:
            print(f"{C.RED}✗ Playbook not found: {name}{C.RST}")
        return

    path = lib.save(name, body)
    print(f"{C.GRN}✓ Saved playbook: {name}{C.RST}")
    print(f"  {C.DIM}{path}{C.RST}")


@cli.command()
@click.option("--days", "-d", type=int, default=7, help="Show sessions from last N days")
@click.option("--limit", "-n", type=int, default=20, help="Max sessions to show")
def sessions(days, limit):
    """List conversation sessions."""
    from exort.memory.store import ConversationStore
    mem = ConversationStore()
    recent = mem.recent(limit)
    if recent:
        print(f"\\n{C.B}Recent Sessions ({len(recent)}){C.RST}\\n")
        for s in recent:
            print(f"  {C.CYN}{s['id']}{C.RST}  {s['title']}  {C.DIM}({s['updated'][:10]}){C.RST}")
        print()
    else:
        print(f"  {C.DIM}no sessions found{C.RST}")


@cli.command()
@click.argument("session_id")
def resume(session_id):
    """Resume a previous conversation session.

    \b
    Examples:
        exort resume abc123
    """
    cfg = Config()
    engine = _make_engine(cfg)
    try:
        engine.resume(session_id)
        title = engine.mem.title(session_id)
        print(f"{C.GRN}✓ Resumed: {title}{C.RST}\\n")
        ExortShell(engine, cfg).run()
    except Exception as e:
        print(f"{C.RED}✗ {e}{C.RST}")


@cli.command()
@click.argument("text")
@click.option("--provider", "-p")
@click.option("--model", "-m")
def translate(text, provider, model):
    """Translate text to English (or ask the AI).

    \b
    Examples:
        exort translate "Bonjour le monde"
        exort translate "你好世界" -p groq
    """
    cfg = Config()
    engine = _make_engine(cfg, provider=provider, model=model)
    prompt = f"Translate the following text to English. Output ONLY the translation, nothing else:\\n\\n{text}"
    for chunk in engine.talk(prompt, stream=True):
        print(chunk, end="", flush=True)
    print()


@cli.command()
@click.argument("code")
@click.option("--language", "-l", default="python", help="Language")
@click.option("--provider", "-p")
def explain(code, language, provider):
    """Explain a piece of code.

    \b
    Examples:
        exort explain "def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)"
        exort explain --language javascript "const x = [...arr].sort()"
    """
    cfg = Config()
    engine = _make_engine(cfg, provider=provider)
    prompt = f"Explain this {language} code in plain English. Be concise but thorough:\\n\\n```{language}\\n{code}\\n```"
    for chunk in engine.talk(prompt, stream=True):
        print(chunk, end="", flush=True)
    print()


@cli.command()
@click.argument("description")
@click.option("--language", "-l", default="python", help="Language")
@click.option("--provider", "-p")
def generate(description, language, provider):
    """Generate code from a description.

    \b
    Examples:
        exort generate "function that sorts a list of dicts by key"
        exort generate "REST API with flask" -l python
        exort generate "binary search" -l javascript
    """
    cfg = Config()
    engine = _make_engine(cfg, provider=provider)
    prompt = f"Write {language} code for: {description}. Output ONLY the code with brief comments. No explanation."
    for chunk in engine.talk(prompt, stream=True):
        print(chunk, end="", flush=True)
    print()


@cli.command()
@click.argument("text")
@click.option("--style", "-s", default="professional", help="Style: professional, casual, friendly, formal")
@click.option("--provider", "-p")
def rewrite(text, style, provider):
    """Rewrite text in a different style.

    \b
    Examples:
        exort rewrite "hey can u send me the docs asap"
        exort rewrite "Dear Sir/Madam, I am writing to inquire..." -s casual
    """
    cfg = Config()
    engine = _make_engine(cfg, provider=provider)
    prompt = f"Rewrite the following text in a {style} style. Output ONLY the rewritten text:\\n\\n{text}"
    for chunk in engine.talk(prompt, stream=True):
        print(chunk, end="", flush=True)
    print()


@cli.command()
@click.argument("topic")
@click.option("--provider", "-p")
def summarize(topic, provider):
    """Summarize a topic, URL, or file content.

    \b
    Examples:
        exort summarize "https://example.com/article"
        exort summarize "quantum computing"
        exort summarize "./README.md"
    """
    import os
    cfg = Config()
    engine = _make_engine(cfg, provider=provider)

    # Check if it's a file
    if os.path.isfile(topic):
        with open(topic, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()[:10000]
        prompt = f"Summarize the following document concisely:\\n\\n{content}"
    elif topic.startswith("http"):
        prompt = f"Fetch and summarize the content at this URL: {topic}"
    else:
        prompt = f"Provide a concise summary of: {topic}"

    for chunk in engine.talk(prompt, stream=True):
        print(chunk, end="", flush=True)
    print()


@cli.command()
@click.argument("code")
@click.option("--language", "-l", default="python")
@click.option("--provider", "-p")
def review(code, language, provider):
    """Review code for bugs, security issues, and improvements.

    \b
    Examples:
        exort review "def login(user, pwd): db.query(f'SELECT * FROM users WHERE name={user}')"
        exort review --file app.py
    """
    cfg = Config()
    engine = _make_engine(cfg, provider=provider)
    prompt = f"""Review this {language} code. Check for:
1. Bugs and logic errors
2. Security vulnerabilities
3. Performance issues
4. Code style improvements

Be concise. Format as a numbered list of findings.

```{language}
{code}
```"""
    for chunk in engine.talk(prompt, stream=True):
        print(chunk, end="", flush=True)
    print()


@cli.command()
@click.argument("query")
@click.option("--max-results", "-n", type=int, default=5)
def search(query, max_results):
    """Search the web (DuckDuckGo).

    \b
    Examples:
        exort search "python async best practices"
        exort search "latest AI news" -n 10
    """
    from exort.tools.web import _search
    results = _search(query, max_results)
    print(f"\\n{C.B}Search: {query}{C.RST}\\n")
    for i, r in enumerate(results, 1):
        if "error" in r:
            print(f"  {C.RED}Error: {r['error']}{C.RST}")
            continue
        if "note" in r:
            print(f"  {C.DIM}{r['note']}{C.RST}")
            continue
        print(f"  {C.CYN}{i}. {r.get('title', 'No title')}{C.RST}")
        print(f"     {C.DIM}{r.get('url', '')}{C.RST}")
        print(f"     {r.get('snippet', '')[:120]}")
        print()


@cli.command()
@click.argument("url")
@click.option("--max-chars", "-c", type=int, default=5000)
def fetch(url, max_chars):
    """Fetch a URL and display its text content.

    \b
    Examples:
        exort fetch "https://example.com"
        exort fetch "https://news.ycombinator.com" -c 3000
    """
    from exort.tools.web import _fetch
    content = _fetch(url, max_chars)
    print(f"\\n{C.B}Fetched: {url}{C.RST}\\n")
    print(content)
    print()


@cli.command()
@click.option("--json-format", "-j", is_flag=True, help="Output as JSON")
def status(json_format):
    """Show Exort system status."""
    import json as json_mod
    cfg = Config()
    from exort.providers import list_providers
    from exort.tools.gear import GearBox

    gb = GearBox()
    gb.discover()

    info = {
        "version": "2.1.0",
        "provider": cfg.get("engine.provider"),
        "model": cfg.get("engine.model"),
        "providers": list_providers(),
        "provider_count": len(list_providers()),
        "gear_count": len(gb),
        "gear": gb.names(),
        "config_path": str(cfg._path),
    }

    if json_format:
        print(json_mod.dumps(info, indent=2))
    else:
        print(f"\\n{C.B}Exort System Status{C.RST}")
        print(f"  {'─' * 40}")
        print(f"  version     {C.ACC}{info['version']}{C.RST}")
        print(f"  provider    {info['provider']}")
        print(f"  model       {info['model']}")
        print(f"  providers   {info['provider_count']} available")
        print(f"  gear        {info['gear_count']} tools")
        print(f"  config      {C.DIM}{info['config_path']}{C.RST}")
        print()


@cli.command()
@click.argument("key")
@click.argument("value")
def set(key, value):
    """Set a configuration value.

    \b
    Examples:
        exort set engine.provider groq
        exort set engine.temperature 0.3
        exort set engine.model llama-3.3-70b-versatile
    """
    cfg = Config()
    try:
        import json
        value = json.loads(value)
    except Exception:
        pass
    cfg.set(key, value)
    cfg.save()
    print(f"{C.GRN}✓ {key} = {value}{C.RST}")


@cli.command()
@click.argument("key")
def get(key):
    """Get a configuration value.

    \b
    Examples:
        exort get engine.provider
        exort get providers.groq.model
    """
    cfg = Config()
    val = cfg.get(key)
    if val is not None:
        print(f"{key} = {val}")
    else:
        print(f"{C.DIM}{key} is not set{C.RST}")


@cli.command()
@click.option("--count", "-n", type=int, default=5, help="Number of history entries")
def history(count):
    """Show recent conversation history."""
    from exort.memory.store import ConversationStore
    mem = ConversationStore()
    recent = mem.recent(count)
    if not recent:
        print(f"  {C.DIM}no conversation history{C.RST}")
        return
    print(f"\\n{C.B}Recent Conversations{C.RST}\\n")
    for s in recent:
        msgs = mem.messages(s["id"])
        print(f"  {C.CYN}{s['id']}{C.RST} — {s['title']}  {C.DIM}({len(msgs)} msgs){C.RST}")
        # Show last 2 exchanges
        for m in msgs[-4:]:
            role = m["role"]
            txt = m.get("content", "")[:80]
            if role == "user":
                print(f"    {C.CYN}▸{C.RST} {txt}")
            elif role == "assistant":
                print(f"    {C.GRN}▸{C.RST} {txt}")
        print()


@cli.command()
@click.argument("prompt_text")
@click.option("--system", "-s", help="System prompt")
@click.option("--provider", "-p")
@click.option("--model", "-m")
@click.option("--max-tokens", "-t", type=int, default=4096)
def complete(prompt_text, system, provider, model, max_tokens):
    """Raw completion (no tools, no memory).

    \b
    Examples:
        exort complete "Write a haiku about coding"
        exort complete "Explain quantum physics" -s "You are a physics teacher"
    """
    cfg = Config()
    engine = _make_engine(cfg, provider=provider, model=model)

    if system:
        engine._system = system

    # Disable tools for raw completion
    old_gear_enabled = cfg.get("gear.enabled")
    cfg.set("gear.enabled", False)

    for chunk in engine.talk(prompt_text, stream=True):
        print(chunk, end="", flush=True)
    print()

    cfg.set("gear.enabled", old_gear_enabled)


def main():
    cli()


if __name__ == "__main__":
    main()
