"""
Command-line interface for OpenMind.

Provides commands for chatting, managing configuration,
and running the agent.
"""

from __future__ import annotations

import sys
import os
from typing import Optional

try:
    import click
except ImportError:
    print("Error: 'click' is required for the CLI. Install with: pip install click")
    sys.exit(1)

from openmind import __version__
from openmind.config import Config
from openmind.utils import Colors, colorize


BANNER = r"""
   ____                    __  __           _ __
  / __ \____  ___  ____   / / / /___  _____(_) /____
 / / / / __ \/ _ \/ __ \ / /_/ / __ \/ ___/ / __/ _ \
/ /_/ / /_/ /  __/ / / / / __/ / /_/ / /  / / /_/  __/
\____/ .___/\___/_/ /_/_/ /_/\____/_/  /_/\__/\___/
    /_/
"""


@click.group()
@click.version_option(version=__version__, prog_name="openmind")
@click.option("--config", "-c", "config_path", default=None, help="Path to config file.")
@click.pass_context
def cli(ctx: click.Context, config_path: Optional[str] = None) -> None:
    """OpenMind — Open-source AI Agent Framework.

    Create autonomous AI agents with tool use, memory, and
    multi-provider support.
    """
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path
    ctx.obj["config"] = Config(config_path=config_path)


@cli.command()
@click.option("--provider", "-p", default=None, help="LLM provider (openai, ollama, groq).")
@click.option("--model", "-m", default=None, help="Model name.")
@click.option("--stream/--no-stream", default=True, help="Enable/disable streaming.")
@click.option("--system", "-s", default=None, help="Custom system prompt.")
@click.option("--conversation", "-conv", default=None, help="Resume a conversation ID.")
@click.option("--temperature", "-t", default=None, type=float, help="Temperature (0.0-2.0).")
@click.pass_context
def chat(
    ctx: click.Context,
    provider: Optional[str],
    model: Optional[str],
    stream: bool,
    system: Optional[str],
    conversation: Optional[str],
    temperature: Optional[float],
) -> None:
    """Start an interactive chat session.

    Chat with an AI agent that can use tools, search the web,
    read files, and execute code.

    Examples:

        openmind chat

        openmind chat --provider groq --model llama-3.1-8b-instant

        openmind chat --provider ollama --model llama3.1
    """
    config = ctx.obj["config"]

    # Apply CLI overrides
    if provider:
        config.set("provider", provider)
    if model:
        config.set("model", model)
    if stream is not None:
        config.set("ui.stream", stream)
    if temperature is not None:
        config.set("temperature", temperature)

    provider_name = config.get("provider", "groq")
    model_name = config.get("model")

    # Print banner
    if config.get("ui.color", True):
        click.echo(colorize(BANNER, Colors.CYAN, bold=True))
        click.echo(
            colorize(
                f"  Provider: {provider_name} | Model: {model_name or 'default'}",
                Colors.DIM,
            )
        )
        click.echo(
            colorize(
                "  Type 'exit' or 'quit' to end. '/help' for commands.",
                Colors.DIM,
            )
        )
        click.echo()
    else:
        click.echo(BANNER)
        click.echo(f"  Provider: {provider_name} | Model: {model_name or 'default'}")
        click.echo("  Type 'exit' or 'quit' to end. '/help' for commands.")
        click.echo()

    # Initialize agent
    try:
        from openmind.agent import Agent
        agent = Agent(
            provider=provider_name,
            model=model_name,
            config=config,
            system_prompt=system,
            on_thought=lambda t: click.echo(colorize(f"  💭 {t}", Colors.YELLOW) if config.get("ui.color") else f"  💭 {t}"),
            on_action=lambda n, a: click.echo(
                f"  ⚡ Using tool: {n}" +
                (colorize(f"({a})", Colors.DIM) if config.get("ui.color") else f"({a})")
            ),
            on_observation=lambda r: None,  # Don't echo full results
        )
    except ImportError as exc:
        click.echo(f"Error initializing agent: {exc}")
        click.echo("Make sure provider packages are installed.")
        sys.exit(1)

    if conversation:
        agent.conversation_id = conversation

    # Main chat loop
    while True:
        try:
            user_input = click.prompt(
                colorize("You", Colors.GREEN, bold=True)
                if config.get("ui.color")
                else "You",
                prompt_suffix=" > ",
            )
        except (EOFError, KeyboardInterrupt):
            click.echo("\nGoodbye! 👋")
            break

        if not user_input.strip():
            continue

        # Handle special commands
        if user_input.strip().lower() in ("exit", "quit", "/exit", "/quit"):
            click.echo("Goodbye! 👋")
            break

        if user_input.strip() == "/help":
            _show_help()
            continue

        if user_input.strip() == "/stats":
            stats = agent.get_stats()
            click.echo("\n📊 Agent Statistics:")
            for key, value in stats.items():
                click.echo(f"  {key}: {value}")
            click.echo()
            continue

        if user_input.strip() == "/reset":
            agent.reset()
            click.echo("🔄 Conversation reset.\n")
            continue

        if user_input.strip() == "/tools":
            click.echo("\n🔧 Registered Tools:")
            for tool_name in agent.tools.list_tools():
                t = agent.tools.get(tool_name)
                click.echo(f"  • {tool_name}: {t.description if t else ''}")
            click.echo()
            continue

        # Generate response
        try:
            if stream and config.get("ui.stream", True):
                click.echo(
                    colorize("\nAssistant", Colors.BLUE, bold=True)
                    if config.get("ui.color")
                    else "\nAssistant",
                    nl=False,
                )
                click.echo(" > ", nl=False)
                for chunk in agent.chat_stream(user_input):
                    click.echo(chunk, nl=False)
                click.echo("\n")
            else:
                response = agent.chat(user_input)
                click.echo()
                if config.get("ui.color"):
                    click.echo(colorize("Assistant", Colors.BLUE, bold=True), nl=False)
                else:
                    click.echo("Assistant", nl=False)
                click.echo(f" > {response}\n")

        except KeyboardInterrupt:
            click.echo("\n⚠️  Response interrupted.\n")
        except Exception as exc:
            click.echo(f"\n❌ Error: {exc}\n")

    # Show session stats
    stats = agent.get_stats()
    if stats.get("total_tokens", 0) > 0:
        click.echo(
            colorize(
                f"\n📊 Session: {stats['total_tokens']} tokens used, "
                f"{stats['iteration_count']} iterations",
                Colors.DIM,
            )
        )


@cli.command()
@click.option("--key", "-k", default=None, help="Config key to get/set.")
@click.option("--value", "-v", default=None, help="Value to set.")
@click.option("--list", "-l", "list_config", is_flag=True, help="Show all config.")
@click.option("--init", is_flag=True, help="Create default config file.")
@click.pass_context
def config(
    ctx: click.Context,
    key: Optional[str],
    value: Optional[str],
    list_config: bool,
    init: bool,
) -> None:
    """Manage OpenMind configuration.

    Examples:

        openmind config --list

        openmind config --key provider --value groq

        openmind config --init
    """
    cfg = ctx.obj["config"]

    if init:
        cfg.save()
        click.echo(f"✅ Config file created at: {cfg.config_path}")
        click.echo("Edit it to customize your settings.")
        return

    if list_config:
        click.echo(f"\n📋 Configuration ({cfg.config_path}):\n")
        _print_dict(cfg.to_dict())
        click.echo()
        return

    if key:
        if value:
            cfg.set(key, value)
            cfg.save()
            click.echo(f"✅ Set {key} = {value}")
        else:
            val = cfg.get(key)
            if val is not None:
                click.echo(f"{key}: {val}")
            else:
                click.echo(f"Key '{key}' not found.")
        return

    # Default: show all config
    click.echo(f"\n📋 Configuration ({cfg.config_path}):\n")
    _print_dict(cfg.to_dict())
    click.echo()


@cli.command()
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to.")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind to.")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int) -> None:
    """Start the OpenMind API server (coming soon).

    Will expose a REST API for programmatic agent access.
    """
    click.echo("🚧 API server is coming soon!")
    click.echo(f"   Planned: http://{host}:{port}")
    click.echo()
    click.echo("For now, use the Python API directly:")
    click.echo()
    click.echo("  from openmind import Agent")
    click.echo('  agent = Agent(provider="groq")')
    click.echo('  response = agent.chat("Hello!")')
    click.echo()


@cli.command()
@click.option("--provider", "-p", default=None, help="Provider to test.")
@click.option("--query", "-q", default="Say hello in one sentence.", help="Test query.")
@click.pass_context
def test(ctx: click.Context, provider: Optional[str], query: str) -> None:
    """Test a provider with a simple query.

    Examples:

        openmind test --provider groq

        openmind test --provider ollama --query "What is 2+2?"
    """
    config = ctx.obj["config"]
    provider_name = provider or config.get("provider", "groq")

    click.echo(f"🧪 Testing provider: {provider_name}")
    click.echo(f"   Query: {query}")
    click.echo()

    try:
        from openmind.agent import Agent
        agent = Agent(provider=provider_name, config=config)
        response = agent.chat(query)
        click.echo(f"✅ Response: {response}")
        stats = agent.get_stats()
        click.echo(f"   Tokens: {stats['total_tokens']}")
    except Exception as exc:
        click.echo(f"❌ Error: {exc}")


@cli.command()
def providers() -> None:
    """List available LLM providers."""
    from openmind.providers import PROVIDERS

    click.echo("\n📡 Available Providers:\n")
    for name, cls in PROVIDERS.items():
        click.echo(f"  • {name:12s} - {cls.__doc__.strip().splitlines()[0] if cls.__doc__ else 'LLM provider'}")
    click.echo()


@cli.command()
def tools() -> None:
    """List available tools."""
    from openmind.tools.base import ToolRegistry

    registry = ToolRegistry()
    registry.auto_discover()

    click.echo("\n🔧 Available Tools:\n")
    for name in registry.list_tools():
        t = registry.get(name)
        desc = t.description if t else ""
        click.echo(f"  • {name:20s} - {desc}")
    click.echo()


def _show_help() -> None:
    """Show in-chat help."""
    click.echo("""
╔══════════════════════════════════════════╗
║          OpenMind Chat Commands          ║
╠══════════════════════════════════════════╣
║  /help     - Show this help message      ║
║  /stats    - Show session statistics     ║
║  /reset    - Reset conversation           ║
║  /tools    - List available tools        ║
║  exit      - Exit chat session           ║
╚══════════════════════════════════════════╝
""")


def _print_dict(d: dict, indent: int = 0) -> None:
    """Pretty-print a nested dict."""
    for key, value in sorted(d.items()):
        prefix = "  " * indent
        if isinstance(value, dict):
            click.echo(f"{prefix}{key}:")
            _print_dict(value, indent + 1)
        else:
            click.echo(f"{prefix}{key}: {value}")


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
