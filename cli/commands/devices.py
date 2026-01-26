"""Edge device management commands"""

import click
import json
from rich.console import Console
from rich.table import Table
from cli.commands.server import get_client

console = Console()


@click.group()
def devices():
    """Edge device management commands"""
    pass


@devices.command()
@click.option('--org', help='Filter by organization ID')
@click.option('--status', type=click.Choice(['online', 'offline', 'unknown']), 
              help='Filter by device status')
@click.option('--limit', default=50, help='Maximum number of devices to return')
@click.pass_context
def list(ctx, org, status, limit):
    """List all edge devices"""
    client = get_client(ctx)
    
    try:
        params = {'limit': limit}
        if org:
            params['org_id'] = org
        if status:
            params['status'] = status
        
        devices_data = client.get('/api/v1/edge/devices', params=params)
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(devices_data, indent=2))
            return
        
        devices_list = devices_data if isinstance(devices_data, list) else devices_data.get('devices', [])
        
        if not devices_list:
            console.print("[yellow]No devices found[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Edge Devices ({len(devices_list)})")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Status", style="green")
        table.add_column("Firmware", style="yellow")
        table.add_column("Last Seen", style="dim")
        
        for device in devices_list:
            status_icon = {
                'online': '🟢',
                'offline': '🔴',
                'unknown': '⚪'
            }.get(device.get('status', 'unknown'), '⚪')
            
            table.add_row(
                device.get('device_id', 'N/A'),
                device.get('device_name', 'N/A'),
                f"{status_icon} {device.get('status', 'unknown')}",
                device.get('firmware_version', 'N/A'),
                device.get('last_heartbeat', 'Never')[:19] if device.get('last_heartbeat') else 'Never'
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to list devices: {e}[/red]")
        raise click.Abort()


@devices.command()
@click.argument('device_id')
@click.pass_context
def get(ctx, device_id):
    """Get device details"""
    client = get_client(ctx)
    
    try:
        device = client.get(f'/api/v1/edge/devices/{device_id}')
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(device, indent=2))
            return
        
        # Display device details
        table = Table(show_header=False, title=f"Device: {device.get('device_name')}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        status_icon = {
            'online': '🟢',
            'offline': '🔴',
            'unknown': '⚪'
        }.get(device.get('status', 'unknown'), '⚪')
        
        table.add_row("Device ID", device.get('device_id', 'N/A'))
        table.add_row("Name", device.get('device_name', 'N/A'))
        table.add_row("Status", f"{status_icon} {device.get('status', 'unknown')}")
        table.add_row("Hardware ID", device.get('hardware_id', 'N/A'))
        table.add_row("Firmware Version", device.get('firmware_version', 'N/A'))
        table.add_row("Organization", device.get('organization_id', 'N/A'))
        table.add_row("Registered", device.get('registered_at', 'N/A'))
        table.add_row("Last Heartbeat", device.get('last_heartbeat', 'Never'))
        
        if device.get('metadata'):
            table.add_row("Metadata", json.dumps(device['metadata'], indent=2))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to get device: {e}[/red]")
        raise click.Abort()


@devices.command()
@click.option('--name', prompt=True, help='Device name')
@click.option('--hardware-id', prompt=True, help='Hardware ID (MAC address, serial, etc.)')
@click.option('--org', help='Organization ID')
@click.option('--firmware', default='1.0.0', help='Firmware version')
@click.pass_context
def register(ctx, name, hardware_id, org, firmware):
    """Register a new edge device"""
    client = get_client(ctx)
    
    try:
        device_data = {
            'device_name': name,
            'hardware_id': hardware_id,
            'firmware_version': firmware
        }
        
        if org:
            device_data['organization_id'] = org
        
        result = client.post('/api/v1/edge/devices/register', json=device_data)
        
        console.print(f"\n[green]✅ Device registered successfully![/green]")
        console.print(f"[cyan]Device ID:[/cyan] {result.get('device_id')}")
        console.print(f"[cyan]Device Name:[/cyan] {result.get('device_name')}")
        
        if result.get('device_token'):
            console.print(f"\n[yellow]⚠️  Save this device token securely:[/yellow]")
            console.print(f"[dim]{result['device_token']}[/dim]\n")
        
    except Exception as e:
        console.print(f"[red]Failed to register device: {e}[/red]")
        raise click.Abort()


@devices.command()
@click.argument('device_id')
@click.option('--name', help='New device name')
@click.option('--firmware', help='New firmware version')
@click.pass_context
def update(ctx, device_id, name, firmware):
    """Update device details"""
    client = get_client(ctx)
    
    try:
        update_data = {}
        if name:
            update_data['device_name'] = name
        if firmware:
            update_data['firmware_version'] = firmware
        
        if not update_data:
            console.print("[yellow]No updates specified[/yellow]")
            return
        
        result = client.patch(f'/api/v1/edge/devices/{device_id}', json=update_data)
        
        console.print(f"[green]✅ Device updated successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to update device: {e}[/red]")
        raise click.Abort()


@devices.command()
@click.argument('device_id')
@click.confirmation_option(prompt='Are you sure you want to delete this device?')
@click.pass_context
def delete(ctx, device_id):
    """Delete a device"""
    client = get_client(ctx)
    
    try:
        client.delete(f'/api/v1/edge/devices/{device_id}')
        console.print(f"[green]✅ Device deleted successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to delete device: {e}[/red]")
        raise click.Abort()


@devices.command()
@click.argument('device_id')
@click.option('--lines', '-n', default=100, help='Number of log entries to show')
@click.pass_context
def logs(ctx, device_id, lines):
    """View device logs"""
    client = get_client(ctx)
    
    try:
        params = {'limit': lines}
        logs_data = client.get(f'/api/v1/edge/devices/{device_id}/logs', params=params)
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(logs_data, indent=2))
            return
        
        logs_list = logs_data if isinstance(logs_data, list) else logs_data.get('logs', [])
        
        if not logs_list:
            console.print("[yellow]No logs found[/yellow]")
            return
        
        for log in logs_list:
            console.print(
                f"[dim]{log.get('timestamp', 'N/A')}[/dim] "
                f"[cyan]{log.get('level', 'INFO')}[/cyan] "
                f"{log.get('message', '')}"
            )
        
    except Exception as e:
        console.print(f"[red]Failed to fetch device logs: {e}[/red]")
        raise click.Abort()


@devices.command()
@click.argument('device_id')
@click.pass_context
def metrics(ctx, device_id):
    """Show device metrics"""
    client = get_client(ctx)
    
    try:
        metrics = client.get(f'/api/v1/edge/devices/{device_id}/metrics')
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(metrics, indent=2))
            return
        
        table = Table(title=f"Metrics for {device_id}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")
        table.add_column("Unit", style="dim")
        
        for metric in metrics.get('metrics', []):
            table.add_row(
                metric.get('name', 'N/A'),
                str(metric.get('value', 'N/A')),
                metric.get('unit', '')
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to fetch device metrics: {e}[/red]")
        raise click.Abort()
