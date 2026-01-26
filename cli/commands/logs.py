"""Log viewing commands"""

import click
from rich.console import Console
from cli.commands.server import get_client

console = Console()


@click.group()
def logs():
    """View logs from various sources"""
    pass


@logs.command()
@click.option('--follow', '-f', is_flag=True, help='Follow log output (not yet implemented)')
@click.option('--lines', '-n', default=100, help='Number of lines to show')
@click.option('--level', type=click.Choice(['ERROR', 'WARNING', 'INFO', 'DEBUG']),
              help='Filter by log level')
@click.option('--source', help='Filter by log source')
@click.pass_context
def server(ctx, follow, lines, level, source):
    """View server logs"""
    # This is implemented in server.py, but included here for grouping
    from cli.commands.server import logs as server_logs_cmd
    ctx.invoke(server_logs_cmd, follow=follow, lines=lines, level=level)


@logs.command()
@click.argument('device_id')
@click.option('--lines', '-n', default=100, help='Number of lines to show')
@click.pass_context
def device(ctx, device_id, lines):
    """View device logs"""
    from cli.commands.devices import logs as device_logs_cmd
    ctx.invoke(device_logs_cmd, device_id=device_id, lines=lines)
