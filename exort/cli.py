"""
Exort CLI — interactive command-line interface for the AI agent.

Commands:
    exort chat              # Start interactive REPL
    exort chat "question"   # Ask a single question
    exort config show       # Show configuration
    exort config set KEY VALUE  # Set config value
    exort serve             # Start Telegram bot
    exort history           # Show conversation history
    exort providers         # List available providers
    exort tools             # List available tools
"""

import json
import os
import sys
import time

import click

from exort.config import Config, ensure_exort_home
from exort.utils import (
    Colors, print_banner, colorize, format_tokens, format_duration,
    get_terminal_width, truncate,
)


def _create_agent(config: Config, provider: str = None, model: str = None, verbose: bool = False):
    """Create an Agent instance from config."""
    from exort.agent import Agent
    return Agent(
        provider=provider,
        model=model,
        config=config,
        verbose=verbose,
    )


def _print_help():
    """Print REPL help."""
    help_text = f"""
{Colors.BOLD}Exort CLI Commands:{Colors.RESET}
  /help           Show this help
  /new            Start a new conversation
  /history        Show recent conversations
  /sessions       List saved sessions
  /load <id>      Load a conversation by ID
  /status         Show agent status (provider, model, usage)
  /model <name>   Switch model
  /provider <name> Switch provider
  /tools          List available tools
  /providers      List available providers
  /clear          Clear screen
  /save           Save current conversation
  /quit, /exit    Exit

{Colors.DIM}Type your message and press Enter to chat.
The agent can use tools to search the web, run code, manage files, and more.{Colors.RESET}
"""
    print(help_text)


class ExortREPL:
    """Interactive Read-Eval-Print Loop for Exort Agent."""

    def __init__(self, agent, config: Config):
        self.agent = agent
        self.config = config
        self.running = True

    def run(self):
        """Main REPL loop."""
        print_banner()
        status = self.agent.get_status()
        provider = status["provider"]
        model = status["model"]
        tools_count = status["tools_available"]

        print(f"  {Colors.DIM}Provider: {provider} | Model: {model} | Tools: {tools_count}{Colors.RESET}")
        print(f"  {Colors.DIM}Type /help for commands, /quit to exit{Colors.RESET}")
        print()

        while self.running:
            try:
                user_input = self._get_input()
                if not user_input:
                    continue
                self._handle_input(user_input)
            except KeyboardInterrupt:
                print("\n")
                continue
            except EOFError:
                print("\nGoodbye!")
                break

    def _get_input(self) -> str:
        """Get user input with a prompt."""
        try:
            return input(f"{Colors.CYAN}You>{Colors.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            raise

    def _handle_input(self, user_input: str):
        """Handle user input — commands or chat."""
        if user_input.startswith("/"):
            self._handle_command(user_input)
        else:
            self._handle_chat(user_input)

    def _handle_command(self, cmd: str):
        """Handle slash commands."""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command in ("/quit", "/exit", "/q"):
            print("Goodbye!")
            self.running = False

        elif command == "/help":
            _print_help()

        elif command == "/new":
            self.agent.start_session("New Chat")
            print(f"{Colors.GREEN}New conversation started.{Colors.RESET}")

        elif command == "/status":
            status = self.agent.get_status()
            print(f"\n{Colors.BOLD}Agent Status:{Colors.RESET}")
            print(f"  Provider:    {status['provider']}")
            print(f"  Model:       {status['model']}")
            print(f"  Conversation: {status['conversation_id'] or 'none'}")
            print(f"  Turns:       {status['turns']}")
            print(f"  Tool calls:  {status['tool_calls']}")
            usage = status['usage']
            print(f"  Tokens:      {usage['prompt_tokens']} in / {usage['completion_tokens']} out / {usage['total_tokens']} total")
            print(f"  Tools:       {status['tools_available']} available")
            print()

        elif command == "/tools":
            tools = self.agent.tools.get_tool_names()
            print(f"\n{Colors.BOLD}Available Tools ({len(tools)}):{Colors.RESET}")
            for t in tools:
                tool_obj = self.agent.tools._tools.get(t)
                desc = tool_obj.schema.description[:80] if tool_obj else ""
                danger = " ⚠️" if (tool_obj and tool_obj.dangerous) else ""
                print(f"  {Colors.CYAN}{t}{Colors.RESET}{danger} — {Colors.DIM}{desc}{Colors.RESET}")
            print()

        elif command == "/providers":
            from exort.providers import list_providers
            providers = list_providers()
            print(f"\n{Colors.BOLD}Available Providers:{Colors.RESET}")
            for p in providers:
                current = " ← current" if p == self.agent._provider_name else ""
                print(f"  {Colors.CYAN}{p}{Colors.RESET}{current}")
            print()

        elif command == "/model":
            if not args:
                print(f"Current model: {self.agent._model or 'default'}")
                print(f"Usage: /model <model_name>")
            else:
                self.agent._model = args.strip()
                print(f"Model changed to: {args.strip()}")

        elif command == "/provider":
            if not args:
                print(f"Current provider: {self.agent._provider_name}")
                print(f"Usage: /provider <provider_name>")
            else:
                try:
                    self.agent = _create_agent(self.config, provider=args.strip())
                    print(f"Provider changed to: {args.strip()}")
                except Exception as e:
                    print(f"{Colors.RED}Error: {e}{Colors.RESET}")

        elif command == "/history":
            if self.agent._conversation_id:
                messages = self.agent._messages
                print(f"\n{Colors.BOLD}Conversation ({len(messages)} messages):{Colors.RESET}")
                for msg in messages[-20:]:
                    role = msg["role"]
                    content = msg["content"][:100] + "..." if len(msg.get("content", "")) > 100 else msg.get("content", "")
                    if role == "user":
                        print(f"  {Colors.CYAN}You:{Colors.RESET} {content}")
                    elif role == "assistant":
                        print(f"  {Colors.GREEN}Exort:{Colors.RESET} {content}")
                    elif role == "tool":
                        print(f"  {Colors.YELLOW}[tool result]{Colors.RESET} {content[:60]}...")
                print()
            else:
                print("No active conversation. Start chatting to begin.")

        elif command == "/sessions":
            sessions = self.agent.memory.get_recent_conversations(10)
            if sessions:
                print(f"\n{Colors.BOLD}Recent Sessions:{Colors.RESET}")
                for s in sessions:
                    print(f"  {Colors.CYAN}{s['id']}{Colors.RESET} — {s['title']} ({s['updated_at'][:10]})")
                print()
            else:
                print("No saved sessions.")

        elif command == "/load":
            if not args:
                print("Usage: /load <conversation_id>")
            else:
                try:
                    self.agent.load_session(args.strip())
                    title = self.agent.memory.get_conversation_title(args.strip())
                    print(f"Loaded: {title}")
                except Exception as e:
                    print(f"{Colors.RED}Error loading session: {e}{Colors.RESET}")

        elif command == "/clear":
            os.system("cls" if os.name == "nt" else "clear")

        elif command == "/save":
            if self.agent._conversation_id:
                print(f"Conversation saved: {self.agent._conversation_id}")
            else:
                print("No active conversation to save.")

        else:
            print(f"{Colors.YELLOW}Unknown command: {command}. Type /help for commands.{Colors.RESET}")

    def _handle_chat(self, user_input: str):
        """Handle chat message — send to agent and display response."""
        start_time = time.time()
        print(f"\n{Colors.GREEN}Exort>{Colors.RESET} ", end="", flush=True)

        try:
            # Use streaming
            full_response = ""
            for chunk in self.agent.chat(user_input, stream=True):
                print(chunk, end="", flush=True)
                full_response += chunk
            print()

            # Show stats
            elapsed = time.time() - start_time
            usage = self.agent.usage
            if self.config.get("display.show_token_usage"):
                stats = f"{Colors.DIM}[{format_duration(elapsed)}"
                if usage.get("total_tokens"):
                    stats += f" | {format_tokens(usage)}"
                stats += f" | {self.agent.tool_call_count} tools]{Colors.RESET}"
                print(stats)

        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[Interrupted]{Colors.RESET}")
        except Exception as e:
            print(f"\n{Colors.RED}Error: {e}{Colors.RESET}")

        print()


@click.group()
@click.version_option(version="1.0.0", prog_name="exort")
def cli():
    """Exort — AI Agent for Everyone.

    An open-source AI agent with tool use, memory, and multi-provider support.
    """
    ensure_exort_home()


@cli.command()
@click.argument("question", required=False)
@click.option("--provider", "-p", help="LLM provider (groq, openai, ollama, anthropic)")
@click.option("--model", "-m", help="Model name to use")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output (show tool calls)")
@click.option("--no-stream", is_flag=True, help="Disable streaming")
def chat(question, provider, model, verbose, no_stream):
    """Chat with the AI agent. Start interactive REPL or ask a single question.

    \b
    Examples:
        exort chat                        # Interactive REPL
        exort chat "What is Python?"      # Single question
        exort chat -p ollama -m llama3.1  # Use local Ollama
    """
    config = Config()
    agent = _create_agent(config, provider=provider, model=model, verbose=verbose)

    if question:
        # Single question mode
        if no_stream:
            response = agent.chat(question, stream=False)
            print(response)
        else:
            for chunk in agent.chat(question, stream=True):
                print(chunk, end="", flush=True)
            print()
    else:
        # Interactive REPL
        repl = ExortREPL(agent, config)
        repl.run()


@cli.command()
@click.argument("action", required=False)
@click.argument("key", required=False)
@click.argument("value", required=False)
def config(action, key, value):
    """Manage Exort configuration.

    \b
    Examples:
        exort config show                           # Show all config
        exort config set provider openai            # Change provider
        exort config set model gpt-4o               # Change model
        exort config set agent.temperature 0.5      # Change temperature
    """
    cfg = Config()

    if action == "show" or action is None:
        print(f"\n{Colors.BOLD}Exort Configuration:{Colors.RESET}")
        print(f"  Config file: {cfg._path}")
        print(f"  Home dir:    {cfg._home}")
        print()
        print(yaml.dump(cfg.data, default_flow_style=False))

    elif action == "set":
        if not key or not value:
            print("Usage: exort config set <key> <value>")
            return
        # Try to parse as JSON for nested values
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            parsed = value
        cfg.set(key, parsed)
        cfg.save()
        print(f"{Colors.GREEN}Set {key} = {value}{Colors.RESET}")

    elif action == "get":
        if not key:
            print("Usage: exort config get <key>")
            return
        val = cfg.get(key)
        print(f"{key} = {val}")

    else:
        print(f"Unknown config action: {action}. Use: show, set, get")


@cli.command()
def providers():
    """List available LLM providers."""
    from exort.providers import list_providers
    available = list_providers()
    print(f"\n{Colors.BOLD}Available Providers:{Colors.RESET}")
    for p in available:
        print(f"  • {p}")
    print(f"\n{Colors.DIM}Use: exort chat -p <provider> to switch{Colors.RESET}")


@cli.command()
def tools():
    """List available tools."""
    from exort.tools.registry import ToolRegistry
    registry = ToolRegistry()
    registry.discover()
    names = registry.get_tool_names()
    print(f"\n{Colors.BOLD}Available Tools ({len(names)}):{Colors.RESET}")
    for name in names:
        tool = registry._tools[name]
        danger = " ⚠️ dangerous" if tool.dangerous else ""
        print(f"  • {Colors.CYAN}{name}{Colors.RESET}{danger}")
        print(f"    {tool.schema.description[:100]}")
    print()


@cli.command()
def serve():
    """Start the Telegram bot server."""
    from exort.config import Config
    cfg = Config()
    token = os.environ.get(cfg.get("telegram.token_env", "TELEGRAM_BOT_TOKEN"))
    if not token:
        print(f"{Colors.RED}Error: TELEGRAM_BOT_TOKEN not set.{Colors.RESET}")
        print("Set it in ~/.exort/.env or as an environment variable.")
        print("Get a token from @BotFather on Telegram.")
        return

    from exort.bot.telegram_bot import run_bot
    run_bot(token, cfg)


@cli.command()
def setup():
    """Interactive setup wizard for first-time configuration."""
    print_banner()
    print(f"{Colors.BOLD}Exort Setup Wizard{Colors.RESET}\n")

    cfg = Config()
    home = ensure_exort_home()

    print(f"Exort home: {home}")
    print()

    # Provider selection
    print("Which LLM provider do you want to use?")
    print("  1. Groq (FREE, fast, recommended for getting started)")
    print("  2. OpenAI (GPT-4, requires API key)")
    print("  3. Ollama (100% local, no API key needed)")
    print("  4. Anthropic (Claude, requires API key)")

    try:
        choice = input("\nEnter choice [1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        return

    provider_map = {"1": "groq", "2": "openai", "3": "ollama", "4": "anthropic"}
    provider = provider_map.get(choice, "groq")
    cfg.set("provider", provider)

    # API key setup
    api_key_env = cfg.get(f"providers.{provider}.api_key_env")
    if api_key_env:
        print(f"\nTo use {provider}, set {api_key_env} in {home / '.env'}")
        print(f"Example: echo '{api_key_env}=your-key-here' > {home / '.env'}")

        try:
            key = input(f"Enter your {api_key_env} (or press Enter to skip): ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if key:
            env_path = home / ".env"
            with open(env_path, "a") as f:
                f.write(f"\n{api_key_env}={key}\n")
            os.environ[api_key_env] = key
            print(f"{Colors.GREEN}API key saved!{Colors.RESET}")

    cfg.save()
    print(f"\n{Colors.GREEN}Setup complete! Run 'exort chat' to start.{Colors.RESET}")


# Need to import yaml for config command
try:
    import yaml
except ImportError:
    yaml = None


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
