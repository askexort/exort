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
            print(f"\n{C.B}  Gear ({len(names)}){C.RST}")
            for n in names:
                g = self.engine.gear._gear[n]
                warn = f" {C.RED}⚠ unsafe{C.RST}" if g.unsafe else ""
                desc = g.spec.info[:70]
                print(f"  {C.CYN}{n}{C.RST}{warn}")
                print(f"    {C.DIM}{desc}{C.RST}")
            print()

        elif cmd == ":providers":
            from exort.providers import list_providers
            ps = list_providers()
            print(f"\n{C.B}  Providers{C.RST}")
            for p in ps:
                cur = f" {C.ACC}← current{C.RST}" if p == self.engine._prov_name else ""
                print(f"  {C.CYN}{p}{C.RST}{cur}")
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
@click.version_option(version="2.0.0", prog_name="exort")
def cli():
    """Exort — The Open Agent Engine. Free AI for Everyone."""
    ensure_exort_dir()


@cli.command()
@click.argument("question", required=False)
@click.option("--provider", "-p", help="LLM provider (groq, openai, ollama, anthropic)")
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


@cli.command()
def providers():
    """List available LLM providers."""
    from exort.providers import list_providers
    for p in list_providers():
        print(f"  • {p}")


@cli.command()
def gear():
    """List available gear (tools)."""
    from exort.tools.gear import GearBox
    gb = GearBox()
    gb.discover()
    print(f"\n{C.B}Gear ({len(gb)}){C.RST}")
    for n in gb.names():
        g = gb._gear[n]
        warn = " ⚠" if g.unsafe else ""
        print(f"  {C.CYN}{n}{C.RST}{warn}")
        print(f"    {C.DIM}{g.spec.info[:90]}{C.RST}")
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
    """First-time setup wizard."""
    banner()
    print(f"{C.B}  Setup Wizard{C.RST}\n")

    cfg = Config()
    d = ensure_exort_dir()
    print(f"  data dir: {d}\n")

    print("  Which provider?")
    print(f"    {C.CYN}1{C.RST}. Groq    (free, fast — recommended)")
    print(f"    {C.CYN}2{C.RST}. OpenAI  (GPT-4, paid)")
    print(f"    {C.CYN}3{C.RST}. Ollama  (local, free)")
    print(f"    {C.CYN}4{C.RST}. Anthropic (Claude, paid)")

    try:
        choice = input(f"\n  choice [1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        return

    prov = {"1": "groq", "2": "openai", "3": "ollama", "4": "anthropic"}.get(choice, "groq")
    cfg.set("engine.provider", prov)

    key_var = cfg.get(f"providers.{prov}.key_var")
    if key_var:
        print(f"\n  To use {prov}, you need {key_var}.")
        print(f"  Get a key and paste it below (or press Enter to skip).")
        if prov == "groq":
            print(f"  {C.DIM}→ https://console.groq.com (free, no credit card){C.RST}")

        try:
            key = input(f"  {key_var}: ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if key:
            env = d / ".env"
            with open(env, "a") as f:
                f.write(f"\n{key_var}={key}\n")
            os.environ[key_var] = key
            print(f"  {C.GRN}✓ saved to {env}{C.RST}")

    cfg.save()
    print(f"\n  {C.GRN}✓ Setup complete! Run 'exort shell' to start.{C.RST}\n")


def main():
    cli()


if __name__ == "__main__":
    main()
