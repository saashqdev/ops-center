#!/usr/bin/env python3
"""
Ops-Center CLI - Command-line interface for Ops-Center management

Usage:
    ops-center [OPTIONS] COMMAND [ARGS]...

Examples:
    ops-center init
    ops-center status
    ops-center users list
    ops-center devices list --org acme-corp
"""

import sys
import click
from rich.console import Console
from rich.table import Table

console = Console()

# Import command groups
from cli.commands import server, users, orgs, devices, webhooks, logs


@click.group()
@click.version_option(version="1.0.0", prog_name="ops-center")
@click.option('--config', '-c', envvar='OPS_CENTER_CONFIG', 
              help='Path to config file (default: ~/.ops-center/config.yaml)')
@click.option('--api-url', envvar='OPS_CENTER_API_URL',
              help='Override API URL from config')
@click.option('--api-key', envvar='OPS_CENTER_API_KEY',
              help='Override API key from config')
@click.option('--output', '-o', type=click.Choice(['table', 'json', 'yaml']), 
              default='table', help='Output format')
@click.pass_context
def cli(ctx, config, api_url, api_key, output):
    """Ops-Center CLI - Manage your Ops-Center infrastructure from the terminal"""
    # Store global options in context
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['api_url'] = api_url
    ctx.obj['api_key'] = api_key
    ctx.obj['output_format'] = output


# Register command groups
cli.add_command(server.server)
cli.add_command(users.users)
cli.add_command(orgs.orgs)
cli.add_command(devices.devices)
cli.add_command(webhooks.webhooks)
cli.add_command(logs.logs)


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize Ops-Center CLI configuration"""
    from cli.config import ConfigManager
    
    console.print("\n[bold cyan]🚀 Ops-Center CLI Setup[/bold cyan]\n")
    
    # Get API URL
    api_url = click.prompt(
        "Enter your Ops-Center API URL",
        default="http://localhost:8084"
    )
    
    # Get API key
    console.print("\n[yellow]You can generate an API key at:[/yellow]")
    console.print(f"[dim]{api_url}/admin/api-keys[/dim]\n")
    
    api_key = click.prompt(
        "Enter your API key",
        hide_input=True
    )
    
    # Optional org ID
    org_id = click.prompt(
        "Default organization ID (optional, press Enter to skip)",
        default="",
        show_default=False
    )
    
    # Save configuration
    config_mgr = ConfigManager(ctx.obj.get('config_path'))
    config_mgr.save_config({
        'api_url': api_url,
        'api_key': api_key,
        'default_org': org_id if org_id else None,
        'output_format': 'table'
    })
    
    console.print("\n[green]✅ Configuration saved successfully![/green]")
    console.print(f"[dim]Config file: {config_mgr.config_path}[/dim]\n")
    
    # Test connection
    console.print("[cyan]Testing connection...[/cyan]")
    from cli.api_client import APIClient
    
    try:
        client = APIClient(api_url, api_key)
        health = client.get('/health')
        console.print("[green]✅ Connected to Ops-Center successfully![/green]\n")
    except Exception as e:
        console.print(f"[red]❌ Connection failed: {e}[/red]\n")
        sys.exit(1)


@cli.command()
@click.pass_context
def config(ctx):
    """Show current configuration"""
    from cli.config import ConfigManager
    
    config_mgr = ConfigManager(ctx.obj.get('config_path'))
    config_data = config_mgr.load_config()
    
    if not config_data:
        console.print("[yellow]No configuration found. Run 'ops-center init' first.[/yellow]")
        return
    
    table = Table(title="Ops-Center Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    # Mask API key
    config_display = config_data.copy()
    if 'api_key' in config_display and config_display['api_key']:
        config_display['api_key'] = config_display['api_key'][:8] + '...' + config_display['api_key'][-4:]
    
    for key, value in config_display.items():
        table.add_row(key, str(value) if value else "[dim]not set[/dim]")
    
    console.print(table)
    console.print(f"\n[dim]Config file: {config_mgr.config_path}[/dim]")


if __name__ == '__main__':
    cli(obj={})
