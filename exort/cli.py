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
import json

import click

from exort.config import Config, ensure_exort_dir
from exort.utils import (
    C, splash_screen, loading_animation, tool_call_display,
    response_header, stats_line, get_terminal_width, glow_text,
    separator, fmt_time, fmt_tokens,
)


def _make_engine(config, provider=None, model=None, verbose=False):
    from exort.engine import Engine
    return Engine(provider=provider, model=model, config=config, verbose=verbose)


def _show_help():
    w = min(62, get_terminal_width() - 4)
    top = f"  {C.GRY}┌{'─' * (w - 2)}┐{C.RST}"
    bot = f"  {C.GRY}└{'─' * (w - 2)}┘{C.RST}"
    mid = f"  {C.GRY}├{'─' * (w - 2)}┤{C.RST}"

    commands = [
        (":help", "Show this help menu"),
        (":new", "Start a fresh session"),
        (":status", "Provider, model, token stats"),
        (":gear", "List available tools"),
        (":providers", "List LLM backends"),
        (":switch <prov>", "Switch LLM provider"),
        (":model <name>", "Switch model"),
        (":history", "Show current conversation"),
        (":sessions", "List saved sessions"),
        (":load <id>", "Resume a session"),
        (":skills", "List skills & playbooks"),
        (":clear", "Clear screen"),
        (":quit", "Exit Exort"),
    ]

    print()
    print(top)
    print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}⚡ COMMANDS{C.RST}{' ' * (w - 14)}{C.GRY}│{C.RST}")
    print(mid)

    for cmd, desc in commands:
        cmd_part = f"{C.CYN}{cmd:<18}{C.RST}"
        desc_part = f"{C.GRY2}{desc}{C.RST}"
        # Pad description
        padding = max(1, w - len(cmd) - 22)
        print(f"  {C.GRY}│{C.RST}  {cmd_part}{desc_part}{' ' * padding}{C.GRY}│{C.RST}")

    print(mid)
    print(f"  {C.GRY}│{C.RST}  {C.DIM}Type anything else to chat with the engine.{C.RST}{' ' * max(1, w - 48)}{C.GRY}│{C.RST}")
    print(f"  {C.GRY}│{C.RST}  {C.DIM}Prefix with ! to run shell commands.{C.RST}{' ' * max(1, w - 40)}{C.GRY}│{C.RST}")
    print(bot)
    print()


class ExortShell:
    """The interactive Exort terminal."""

    def __init__(self, engine, config):
        self.engine = engine
        self.cfg = config
        self.running = True
        self._turn_count = 0

    def run(self):
        st = self.engine.status()
        provider = st['provider']
        model = st['model']
        gear_count = st['gear_count']

        # Animated startup
        splash_screen(provider, model, gear_count, st.get('session'))

        while self.running:
            try:
                line = self._prompt()
                if not line:
                    continue
                if line.startswith(":"):
                    self._command(line)
                elif line.startswith("!"):
                    self._shell(line[1:].strip())
                else:
                    self._chat(line)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print(f"\n  {C.GRY}goodbye.{C.RST}")
                break

    def _prompt(self) -> str:
        self._turn_count += 1
        # Dynamic prompt with turn counter
        turn = f"{C.GRY}[{self._turn_count}]{C.RST}"
        arrow = f"{C.ACC}{C.B}exort ▸{C.RST}"
        try:
            return input(f"  {turn} {arrow} ").strip()
        except (EOFError, KeyboardInterrupt):
            raise

    def _shell(self, cmd: str):
        """Run a shell command."""
        if not cmd:
            return
        print(f"  {C.GRY}$ {cmd}{C.RST}")
        os.system(cmd)

    def _command(self, line: str):
        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in (":quit", ":q", ":exit"):
            print(f"\n  {C.ACC}▸{C.RST} {C.GRY}Session ended. Goodbye!{C.RST}\n")
            self.running = False

        elif cmd == ":help":
            _show_help()

        elif cmd == ":new":
            self.engine.open("new session")
            self._turn_count = 0
            print(f"  {C.GRN}✓{C.RST} {C.GRY2}New session started{C.RST}")

        elif cmd == ":status":
            self._show_status()

        elif cmd == ":gear":
            self._show_gear()

        elif cmd == ":providers":
            self._show_providers()

        elif cmd == ":switch":
            if not arg:
                print(f"  {C.RED}✗{C.RST} Usage: :switch <provider>")
                return
            try:
                self.engine = _make_engine(self.cfg, provider=arg)
                print(f"  {C.GRN}✓{C.RST} Switched to {C.CYN}{arg}{C.RST}")
            except Exception as e:
                print(f"  {C.RED}✗{C.RST} {e}")

        elif cmd == ":model":
            if not arg:
                cur = self.engine._model or 'default'
                print(f"  {C.GRY2}Current: {C.HI}{cur}{C.RST}")
                print(f"  {C.GRY2}Usage: :model <model_name>{C.RST}")
            else:
                self.engine._model = arg
                print(f"  {C.GRN}✓{C.RST} Model → {C.HI}{arg}{C.RST}")

        elif cmd == ":history":
            self._show_history()

        elif cmd == ":sessions":
            self._show_sessions()

        elif cmd == ":load":
            if not arg:
                print(f"  {C.GRY2}Usage: :load <session_id>{C.RST}")
            else:
                try:
                    self.engine.resume(arg)
                    title = self.engine.mem.title(arg)
                    print(f"  {C.GRN}✓{C.RST} Loaded: {C.HI}{title}{C.RST}")
                except Exception as e:
                    print(f"  {C.RED}✗{C.RST} {e}")

        elif cmd == ":skills":
            self._show_skills()

        elif cmd == ":clear":
            os.system("cls" if os.name == "nt" else "clear")

        else:
            print(f"  {C.GRY}Unknown: {cmd} — type :help{C.RST}")

    def _show_status(self):
        s = self.engine.status()
        t = s["tokens"]
        w = min(62, get_terminal_width() - 4)
        top = f"  {C.GRY}┌{'─' * (w - 2)}┐{C.RST}"
        bot = f"  {C.GRY}└{'─' * (w - 2)}┘{C.RST}"
        mid = f"  {C.GRY}├{'─' * (w - 2)}┤{C.RST}"

        print()
        print(top)
        print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}⚡ ENGINE STATUS{C.RST}{' ' * (w - 19)}{C.GRY}│{C.RST}")
        print(mid)

        rows = [
            ("Provider", f"{C.CYN}{s['provider']}{C.RST}"),
            ("Model", f"{C.HI}{s['model']}{C.RST}"),
            ("Session", f"{C.GRY2}{s['session'] or '(none)'}{C.RST}"),
            ("Turns", f"{C.HI}{s['turns']}{C.RST}"),
            ("Gear Calls", f"{C.HI}{s['gear_calls']}{C.RST}"),
            ("Tokens In", f"{C.CYN}{t['prompt_tok']}{C.RST}"),
            ("Tokens Out", f"{C.CYN}{t['completion_tok']}{C.RST}"),
            ("Tokens Total", f"{C.ACC}{t['total_tok']}{C.RST}"),
            ("Gear Loaded", f"{C.GRN}{s['gear_count']} tools{C.RST}"),
        ]

        for label, value in rows:
            padding = max(1, w - len(label) - 16)
            print(f"  {C.GRY}│{C.RST}  {C.GRY2}{label:<14}{C.RST} {value}{' ' * padding}{C.GRY}│{C.RST}")

        print(bot)
        print()

    def _show_gear(self):
        names = self.engine.gear.names()
        cats = self.engine.gear.categories()
        w = min(62, get_terminal_width() - 4)
        top = f"  {C.GRY}┌{'─' * (w - 2)}┐{C.RST}"
        bot = f"  {C.GRY}└{'─' * (w - 2)}┘{C.RST}"
        mid = f"  {C.GRY}├{'─' * (w - 2)}┤{C.RST}"

        print()
        print(top)
        print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}⚡ GEAR ({len(names)} tools){C.RST}{' ' * max(1, w - 20 - len(str(len(names))))}{C.GRY}│{C.RST}")
        print(mid)

        for cat, items in cats.items():
            print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}{cat.upper()}{C.RST}{' ' * max(1, w - len(cat) - 6)}{C.GRY}│{C.RST}")
            for n in items:
                g = self.engine.gear._gear[n]
                warn = f" {C.RED}⚠{C.RST}" if g.unsafe else ""
                desc = g.spec.info[:40]
                line = f"    {C.CYN}{n}{C.RST}{warn} {C.GRY}{desc}{C.RST}"
                # Simple padding
                print(f"  {C.GRY}│{C.RST}{line}{' ' * max(1, w - len(n) - len(desc) - 10)}{C.GRY}│{C.RST}")

        print(bot)
        print()

    def _show_providers(self):
        from exort.providers import provider_info
        ps = provider_info()
        w = min(62, get_terminal_width() - 4)
        top = f"  {C.GRY}┌{'─' * (w - 2)}┐{C.RST}"
        bot = f"  {C.GRY}└{'─' * (w - 2)}┘{C.RST}"
        mid = f"  {C.GRY}├{'─' * (w - 2)}┤{C.RST}"

        print()
        print(top)
        print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}⚡ PROVIDERS ({len(ps)}){C.RST}{' ' * max(1, w - 18 - len(str(len(ps))))}{C.GRY}│{C.RST}")
        print(mid)

        for p in ps:
            cur = f" {C.ACC}← active{C.RST}" if p["name"] == self.engine._prov_name else ""
            free = f" {C.GRN}free{C.RST}" if p.get("needs_key") is False else ""
            tag = f"{cur}{free}"
            name = f"{C.CYN}{p['name']}{C.RST}"
            print(f"  {C.GRY}│{C.RST}  {name}{tag}{' ' * max(1, w - len(p['name']) - 12)}{C.GRY}│{C.RST}")

        print(bot)
        print()

    def _show_history(self):
        history = self.engine._history[-20:]
        if not history:
            print(f"  {C.GRY}No conversation history{C.RST}")
            return

        w = min(62, get_terminal_width() - 4)
        print()
        print(f"  {C.GRY}┌{'─' * (w - 2)}┐{C.RST}")
        print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}⚡ HISTORY ({len(history)} messages){C.RST}{' ' * max(1, w - 24 - len(str(len(history))))}{C.GRY}│{C.RST}")
        print(f"  {C.GRY}├{'─' * (w - 2)}┤{C.RST}")

        for m in history:
            role = m["role"]
            txt = m.get("content", "")[:50]
            if role == "user":
                icon = f"{C.CYN}▸{C.RST}"
                label = f"{C.CYN}you{C.RST}"
            else:
                icon = f"{C.GRN}▸{C.RST}"
                label = f"{C.GRN}exort{C.RST}"
            print(f"  {C.GRY}│{C.RST}  {icon} {label}: {C.GRY2}{txt}{C.RST}{' ' * max(1, w - len(txt) - 14)}{C.GRY}│{C.RST}")

        print(f"  {C.GRY}└{'─' * (w - 2)}┘{C.RST}")
        print()

    def _show_sessions(self):
        sessions = self.engine.mem.recent(10)
        if not sessions:
            print(f"  {C.GRY}No saved sessions{C.RST}")
            return

        w = min(62, get_terminal_width() - 4)
        print()
        print(f"  {C.GRY}┌{'─' * (w - 2)}┐{C.RST}")
        print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}⚡ SESSIONS{C.RST}{' ' * (w - 14)}{C.GRY}│{C.RST}")
        print(f"  {C.GRY}├{'─' * (w - 2)}┤{C.RST}")

        for s in sessions:
            sid = s['id'][:12]
            title = s['title'][:30]
            date = s['updated'][:10]
            print(f"  {C.GRY}│{C.RST}  {C.CYN}{sid}{C.RST}  {C.GRY2}{title}{C.RST}  {C.GRY}{date}{C.RST}{' ' * max(1, w - len(sid) - len(title) - len(date) - 10)}{C.GRY}│{C.RST}")

        print(f"  {C.GRY}└{'─' * (w - 2)}┘{C.RST}")
        print()

    def _show_skills(self):
        from exort.playbooks.library import PlaybookLibrary
        lib = PlaybookLibrary()
        lib.load()
        books = lib.list_all()
        w = min(62, get_terminal_width() - 4)

        print()
        print(f"  {C.GRY}┌{'─' * (w - 2)}┐{C.RST}")
        print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}⚡ SKILLS ({len(books)}){C.RST}{' ' * max(1, w - 14 - len(str(len(books))))}{C.GRY}│{C.RST}")
        print(f"  {C.GRY}├{'─' * (w - 2)}┤{C.RST}")

        for b in books:
            origin = f"{C.GRN}built-in{C.RST}" if b["origin"] == "builtin" else f"{C.GRY}user{C.RST}"
            name = b['name']
            print(f"  {C.GRY}│{C.RST}  {C.CYN}{name}{C.RST} {origin}{' ' * max(1, w - len(name) - 14)}{C.GRY}│{C.RST}")

        print(f"  {C.GRY}└{'─' * (w - 2)}┘{C.RST}")
        print()

    def _chat(self, text: str):
        """Send message to engine and display response."""
        t0 = time.time()
        self._turn_count += 1

        # Show thinking indicator
        sys.stdout.write(f"\r  {C.ACC}⠋{C.RST} {C.GRY2}thinking...{C.RST}  \r")
        sys.stdout.flush()

        try:
            full = ""
            first_chunk = True
            for chunk in self.engine.talk(text, stream=True):
                if first_chunk:
                    # Clear thinking indicator and show response header
                    sys.stdout.write(f"\r{' ' * 40}\r")
                    st = self.engine.status()
                    print(f"  {C.GRN}▸{C.RST} {C.GRY2}{st['provider']}/{st['model']}{C.RST}")
                    print(f"  {C.GRN}│{C.RST} ", end="", flush=True)
                    first_chunk = False
                print(chunk, end="", flush=True)
                full += chunk
            print()

            elapsed = time.time() - t0
            st = self.engine.stats
            if self.cfg.get("display.show_tokens"):
                print(stats_line(elapsed, st, st.get('gear_calls', 0)))

        except KeyboardInterrupt:
            print(f"\n  {C.YEL}⚠{C.RST} {C.GRY}Interrupted{C.RST}")
        except Exception as e:
            print(f"\n  {C.RED}✗{C.RST} {C.RED}{e}{C.RST}")

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
            print(f"\n  {C.ACC}{C.B}Config: {cfg._path}{C.RST}\n")
            print(yaml.dump(cfg.data, default_flow_style=False))
        except ImportError:
            for k, v in cfg.data.items():
                print(f"  {k}: {v}")
    elif action == "set" and key and value:
        try:
            value = json.loads(value)
        except Exception:
            pass
        cfg.set(key, value)
        cfg.save()
        print(f"  {C.GRN}✓{C.RST} {key} = {value}")
    elif action == "get" and key:
        print(f"  {key} = {cfg.get(key)}")
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
    w = min(62, get_terminal_width() - 4)

    print()
    print(f"  {C.GRY}┌{'─' * (w - 2)}┐{C.RST}")
    print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}⚡ PROVIDERS ({len(ps)}){C.RST}{' ' * max(1, w - 18 - len(str(len(ps))))}{C.GRY}│{C.RST}")
    print(f"  {C.GRY}├{'─' * (w - 2)}┤{C.RST}")

    for p in ps:
        cur = f" {C.ACC}← active{C.RST}" if p["name"] == current else ""
        key = f"{C.GRN}free{C.RST}" if not p["needs_key"] else f"{C.GRY}key required{C.RST}"
        name = f"{C.CYN}{p['name']}{C.RST}"
        print(f"  {C.GRY}│{C.RST}  {name}  {key}{cur}{' ' * max(1, w - len(p['name']) - 20)}{C.GRY}│{C.RST}")

    print(f"  {C.GRY}└{'─' * (w - 2)}┘{C.RST}")
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

    if name == "custom":
        if not endpoint:
            print(f"  {C.RED}✗{C.RST} Custom provider requires --endpoint")
            return
        cfg.set(f"providers.custom.endpoint", endpoint)
        if model:
            cfg.set(f"providers.custom.model", model)
        if key:
            cfg.set(f"providers.custom.key_var", f"CUSTOM_API_KEY")
            _save_env_key("CUSTOM_API_KEY", key)
        cfg.save()
        print(f"  {C.GRN}✓{C.RST} Custom provider configured")
        return

    if name not in available:
        print(f"  {C.RED}✗{C.RST} Unknown provider: {name}")
        print(f"  Available: {', '.join(available)}")
        return

    if endpoint:
        cfg.set(f"providers.{name}.endpoint", endpoint)
    if model:
        cfg.set(f"providers.{name}.model", model)
    if key:
        key_var = cfg.get(f"providers.{name}.key_var", f"{name.upper()}_API_KEY")
        _save_env_key(key_var, key)
        print(f"  {C.GRN}✓{C.RST} API key saved as {key_var}")

    cfg.save()
    print(f"  {C.GRN}✓{C.RST} Provider '{name}' configured")


@providers.command("remove")
@click.argument("name")
def providers_remove(name):
    """Remove a provider configuration."""
    cfg = Config()
    if name not in cfg.get("providers", {}):
        print(f"  {C.RED}✗{C.RST} Provider '{name}' not in config")
        return
    cfg.data["providers"].pop(name, None)
    cfg.save()
    print(f"  {C.GRN}✓{C.RST} Provider '{name}' removed")


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
    cfg = Config()

    def _test(prov_name):
        try:
            pcfg = cfg.provider_conf(prov_name)
            key = cfg.api_key(prov_name)
            if pcfg.get("key_var") and not key:
                return None
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
            print(f"  {C.GRN}✓{C.RST} {name}: {C.GRN}OK{C.RST}")
        elif result is None:
            print(f"  {C.YEL}?{C.RST} {name}: {C.GRY}No API key configured{C.RST}")
        elif result is False:
            print(f"  {C.RED}✗{C.RST} {name}: {C.RED}Connection failed{C.RST}")
        else:
            print(f"  {C.RED}✗{C.RST} {name}: {C.RED}{result}{C.RST}")
    else:
        print(f"\n  {C.ACC}{C.B}⚡ Testing All Providers{C.RST}\n")
        for p in list_providers():
            if p == "custom":
                continue
            result = _test(p)
            if result is True:
                print(f"  {C.GRN}✓{C.RST} {C.CYN}{p}{C.RST} {C.GRN}OK{C.RST}")
            elif result is None:
                print(f"  {C.GRY}○{C.RST} {C.CYN}{p}{C.RST} {C.GRY}(no key){C.RST}")
            elif result is False:
                print(f"  {C.RED}✗{C.RST} {C.CYN}{p}{C.RST} {C.RED}(failed){C.RST}")
            else:
                print(f"  {C.RED}✗{C.RST} {C.CYN}{p}{C.RST} {C.RED}({result[:40]}){C.RST}")
        print()


# ── Provider setup wizard data ──────────────────────────────────────────────

_PROVIDER_CATALOG = {
    # ── Free Providers (no credit card) ──
    "free": {
        "title": "Free Providers (no credit card needed)",
        "providers": [
            ("groq", "GROQ_API_KEY", "https://console.groq.com", "llama-3.3-70b-versatile", "Fast inference, 100K tok/day free"),
            ("cerebras", "CEREBRAS_API_KEY", "https://cloud.cerebras.ai", "llama-3.3-70b", "Wafer-scale speed, 1M tok/day"),
            ("sambanova", "SAMBANOVA_API_KEY", "https://cloud.sambanova.ai", "llama-3.3-70b", "Free RDU inference"),
            ("openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai/keys", "meta-llama/llama-3.3-70b-instruct:free", "100+ models, many free"),
            ("gemini", "GEMINI_API_KEY", "https://aistudio.google.com/apikey", "gemini-2.0-flash", "Google's multimodal AI"),
            ("huggingface", "HUGGINGFACE_API_KEY", "https://huggingface.co/settings/tokens", "meta-llama/Llama-3.3-70B-Instruct", "Free Inference API"),
            ("cloudflare", "CLOUDFLARE_API_KEY", "https://dash.cloudflare.com", "@cf/meta/llama-3-8b-instruct", "Edge AI, 10K neurons/day"),
        ],
    },
    # ── Paid Providers ──
    "paid": {
        "title": "Paid Providers",
        "providers": [
            ("openai", "OPENAI_API_KEY", "https://platform.openai.com/api-keys", "gpt-4o", "GPT-4o, GPT-4, o1"),
            ("anthropic", "ANTHROPIC_API_KEY", "https://console.anthropic.com", "claude-sonnet-4-20250514", "Claude 3.5 Sonnet, Haiku"),
            ("together", "TOGETHER_API_KEY", "https://api.together.xyz", "meta-llama/Llama-3.3-70B-Instruct-Turbo", "Wide model selection"),
            ("mistral", "MISTRAL_API_KEY", "https://console.mistral.ai", "mistral-small-latest", "European AI, Codestral"),
            ("deepseek", "DEEPSEEK_API_KEY", "https://platform.deepseek.com", "deepseek-chat", "Top coding models"),
            ("fireworks", "FIREWORKS_API_KEY", "https://fireworks.ai", "accounts/fireworks/models/llama-v3p3-70b", "Fast inference"),
            ("nvidia", "NVIDIA_API_KEY", "https://build.nvidia.com", "meta/llama-3.3-70b-instruct", "NVIDIA NIM endpoints"),
            ("xai", "XAI_API_KEY", "https://console.x.ai", "grok-2", "Grok models"),
            ("perplexity", "PERPLEXITY_API_KEY", "https://www.perplexity.ai/settings/api", "llama-3.1-sonar-large-128k-online", "Search-augmented LLM"),
            ("cohere", "COHERE_API_KEY", "https://dashboard.cohere.com", "command-r-plus", "RAG & embeddings"),
            ("ollama", None, "https://ollama.com", "llama3.3", "Local models (no key needed)"),
        ],
    },
}


def _save_env_key(key_var: str, key_value: str):
    """Save an API key to the .env file."""
    env_path = os.path.join(os.path.expanduser("~"), ".exort", ".env")
    os.makedirs(os.path.dirname(env_path), exist_ok=True)

    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key_var}="):
            lines[i] = f"{key_var}={key_value}\n"
            found = True
            break

    if not found:
        lines.append(f"{key_var}={key_value}\n")

    with open(env_path, "w") as f:
        f.writelines(lines)


@cli.command()
def setup():
    """Interactive provider setup wizard.

    \b
    Guides you through setting up LLM providers.
    Supports free providers (no credit card) and paid providers.
    """
    w = min(62, get_terminal_width() - 4)
    top = f"  {C.GRY}┌{'─' * (w - 2)}┐{C.RST}"
    bot = f"  {C.GRY}└{'─' * (w - 2)}┘{C.RST}"
    mid = f"  {C.GRY}├{'─' * (w - 2)}┤{C.RST}"

    print()
    print(top)
    print(f"  {C.GRY}│{C.RST}  {C.ACC}{C.B}⚡ SETUP WIZARD{C.RST}{' ' * (w - 18)}{C.GRY}│{C.RST}")
    print(mid)
    print(f"  {C.GRY}│{C.RST}  {C.GRY2}Configure your LLM providers{C.RST}{' ' * (w - 33)}{C.GRY}│{C.RST}")
    print(bot)

    cfg = Config()

    # Show categories
    print()
    print(f"  {C.ACC}1{C.RST} {C.HI}Free Providers{C.RST} {C.GRY}(no credit card needed){C.RST}")
    print(f"  {C.ACC}2{C.RST} {C.HI}Paid Providers{C.RST} {C.GRY}(API key required){C.RST}")
    print(f"  {C.ACC}3{C.RST} {C.HI}Quick Setup{C.RST} {C.GRY}(recommended: Groq free){C.RST}")
    print()

    try:
        choice = input(f"  {C.ACC}▸{C.RST} Select [1/2/3]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if choice == "3":
        # Quick setup with Groq
        print(f"\n  {C.ACC}▸{C.RST} Quick setup with {C.CYN}Groq{C.RST} (free, fast)")
        print(f"  {C.GRY2}Get your key: https://console.groq.com{C.RST}")
        key = input(f"  {C.ACC}▸{C.RST} Paste API key (or Enter to skip): ").strip()
        if key:
            _save_env_key("GROQ_API_KEY", key)
            cfg.set("engine.provider", "groq")
            cfg.save()
            print(f"\n  {C.GRN}✓{C.RST} Groq configured! You're ready to go.")
            print(f"  {C.GRY2}Run: exort shell{C.RST}")
        else:
            print(f"  {C.GRY}Skipped. You can add keys later.{C.RST}")
        return

    cat = "free" if choice == "1" else "paid"
    catalog = _PROVIDER_CATALOG[cat]

    print(f"\n  {C.ACC}{C.B}{catalog['title']}{C.RST}\n")

    for i, (name, key_var, url, model, desc) in enumerate(catalog["providers"], 1):
        print(f"  {C.ACC}{i}{C.RST} {C.CYN}{name}{C.RST} {C.GRY}{desc}{C.RST}")

    print()
    try:
        prov_choice = input(f"  {C.ACC}▸{C.RST} Select provider number: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    try:
        idx = int(prov_choice) - 1
        name, key_var, url, model, desc = catalog["providers"][idx]
    except (ValueError, IndexError):
        print(f"  {C.RED}✗{C.RST} Invalid choice")
        return

    print(f"\n  {C.CYN}{name}{C.RST} — {desc}")
    print(f"  {C.GRY2}Get key: {url}{C.RST}")

    if key_var:
        key = input(f"  {C.ACC}▸{C.RST} Paste API key: ").strip()
        if not key:
            print(f"  {C.RED}✗{C.RST} API key required")
            return
        _save_env_key(key_var, key)

    cfg.set("engine.provider", name)
    if model:
        cfg.set("engine.model", model)
    cfg.save()

    print(f"\n  {C.GRN}✓{C.RST} {C.CYN}{name}{C.RST} configured!")
    print(f"  {C.GRY2}Model: {model}{C.RST}")
    print(f"  {C.GRY2}Run: exort shell{C.RST}\n")


@cli.command()
def providers_setup():
    """Alias for setup — interactive provider wizard."""
    # Click doesn't allow calling one command from another easily,
    # so we just invoke setup directly.
    from click.testing import CliRunner
    # Actually, let's just forward to setup
    setup.callback()


@cli.command()
def bot():
    """Start the Exort Telegram bot.

    \b
    Requires TELEGRAM_BOT_TOKEN env var.
    Optional: GROQ_API_KEY, OPENROUTER_API_KEY, CEREBRAS_API_KEY, MIMO_API_KEY
    """
    from exort.bot.telegram_bot import run_bot
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    run_bot(token)


# Backward-compatible alias
main = cli
