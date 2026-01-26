"""Server management commands"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from cli.api_client import APIClient
from cli.config import ConfigManager

console = Console()


def get_client(ctx) -> APIClient:
    """Get configured API client"""
    # Check for overrides from CLI flags
    api_url = ctx.obj.get('api_url')
    api_key = ctx.obj.get('api_key')
    
    # Load from config if not provided
    if not api_url or not api_key:
        config_mgr = ConfigManager(ctx.obj.get('config_path'))
        config = config_mgr.load_config()
        
        if not config:
            console.print("[red]No configuration found. Run 'ops-center init' first.[/red]")
            raise click.Abort()
        
        api_url = api_url or config.get('api_url')
        api_key = api_key or config.get('api_key')
    
    if not api_url or not api_key:
        console.print("[red]Missing API URL or API key. Run 'ops-center init' first.[/red]")
        raise click.Abort()
    
    return APIClient(api_url, api_key)


@click.group()
def server():
    """Server management commands"""
    pass


@server.command()
@click.pass_context
def status(ctx):
    """Check server health and status"""
    client = get_client(ctx)
    
    try:
        # Get health status
        health = client.get('/health')
        
        # Get version/info if available
        try:
            info = client.get('/api/v1/admin/info')
        except:
            info = {}
        
        # Display status
        if health.get('status') == 'healthy':
            console.print("\n[green]✅ Server is healthy[/green]\n")
        else:
            console.print("\n[yellow]⚠️  Server status unknown[/yellow]\n")
        
        # Create status table
        table = Table(show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Status", health.get('status', 'unknown'))
        
        if info:
            table.add_row("Version", info.get('version', 'N/A'))
            table.add_row("Environment", info.get('environment', 'N/A'))
            table.add_row("Uptime", info.get('uptime', 'N/A'))
        
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"\n[red]❌ Failed to check server status: {e}[/red]\n")
        raise click.Abort()


@server.command()
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--lines', '-n', default=50, help='Number of lines to show')
@click.option('--level', type=click.Choice(['ERROR', 'WARNING', 'INFO', 'DEBUG']), 
              help='Filter by log level')
@click.pass_context
def logs(ctx, follow, lines, level):
    """View server logs (requires admin access)"""
    client = get_client(ctx)
    
    try:
        params = {'limit': lines}
        if level:
            params['level'] = level
        
        logs_data = client.get('/api/v1/admin/logs', params=params)
        
        if not logs_data.get('logs'):
            console.print("[yellow]No logs found[/yellow]")
            return
        
        for log in logs_data['logs']:
            level_color = {
                'ERROR': 'red',
                'WARNING': 'yellow',
                'INFO': 'blue',
                'DEBUG': 'dim'
            }.get(log.get('level', 'INFO'), 'white')
            
            console.print(
                f"[dim]{log.get('timestamp')}[/dim] "
                f"[{level_color}]{log.get('level', 'INFO')}[/{level_color}] "
                f"{log.get('message')}"
            )
        
        if follow:
            console.print("\n[dim]Live log following not yet implemented[/dim]")
        
    except Exception as e:
        console.print(f"[red]Failed to fetch logs: {e}[/red]")
        raise click.Abort()


@server.command()
@click.pass_context
def info(ctx):
    """Show detailed server information"""
    client = get_client(ctx)
    
    try:
        info = client.get('/api/v1/admin/info')
        
        # Create info panel
        info_text = ""
        for key, value in info.items():
            info_text += f"[cyan]{key}:[/cyan] {value}\n"
        
        panel = Panel(info_text, title="Server Information", border_style="blue")
        console.print(panel)
        
    except Exception as e:
        console.print(f"[red]Failed to fetch server info: {e}[/red]")
        raise click.Abort()


@server.command()
@click.pass_context
def metrics(ctx):
    """Show server metrics and statistics"""
    client = get_client(ctx)
    
    try:
        metrics = client.get('/api/v1/admin/metrics')
        
        # Display metrics in a table
        table = Table(title="Server Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        
        for key, value in metrics.items():
            table.add_row(key.replace('_', ' ').title(), str(value))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to fetch metrics: {e}[/red]")
        raise click.Abort()
