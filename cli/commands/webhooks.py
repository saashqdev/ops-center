"""Webhook management commands"""

import click
import json
from rich.console import Console
from rich.table import Table
from cli.commands.server import get_client

console = Console()


@click.group()
def webhooks():
    """Webhook management commands"""
    pass


@webhooks.command()
@click.option('--org', help='Filter by organization ID')
@click.option('--active/--inactive', default=None, help='Filter by active status')
@click.pass_context
def list(ctx, org, active):
    """List all webhooks"""
    client = get_client(ctx)
    
    try:
        params = {}
        if org:
            params['org_id'] = org
        if active is not None:
            params['active'] = active
        
        webhooks_data = client.get('/api/v1/webhooks', params=params)
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(webhooks_data, indent=2))
            return
        
        webhooks_list = webhooks_data if isinstance(webhooks_data, list) else webhooks_data.get('webhooks', [])
        
        if not webhooks_list:
            console.print("[yellow]No webhooks found[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Webhooks ({len(webhooks_list)})")
        table.add_column("ID", style="cyan")
        table.add_column("URL", style="white")
        table.add_column("Events", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="dim")
        
        for webhook in webhooks_list:
            status_icon = "✓" if webhook.get('active') else "✗"
            events_count = len(webhook.get('events', []))
            
            table.add_row(
                webhook.get('webhook_id', 'N/A')[:8],
                webhook.get('url', 'N/A')[:50],
                f"{events_count} events",
                status_icon,
                webhook.get('created_at', 'N/A')[:10] if webhook.get('created_at') else 'N/A'
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to list webhooks: {e}[/red]")
        raise click.Abort()


@webhooks.command()
@click.argument('webhook_id')
@click.pass_context
def get(ctx, webhook_id):
    """Get webhook details"""
    client = get_client(ctx)
    
    try:
        webhook = client.get(f'/api/v1/webhooks/{webhook_id}')
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(webhook, indent=2))
            return
        
        # Display webhook details
        table = Table(show_header=False, title="Webhook Details")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Webhook ID", webhook.get('webhook_id', 'N/A'))
        table.add_row("URL", webhook.get('url', 'N/A'))
        table.add_row("Description", webhook.get('description', 'N/A'))
        table.add_row("Active", "Yes" if webhook.get('active') else "No")
        table.add_row("Events", ', '.join(webhook.get('events', [])))
        table.add_row("Created", webhook.get('created_at', 'N/A'))
        table.add_row("Organization", webhook.get('organization_id', 'Global'))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to get webhook: {e}[/red]")
        raise click.Abort()


@webhooks.command()
@click.option('--url', prompt=True, help='Webhook URL')
@click.option('--events', prompt=True, help='Comma-separated list of events (e.g., user.created,device.online)')
@click.option('--description', default='', help='Webhook description')
@click.option('--org', help='Organization ID (optional)')
@click.option('--secret', help='Webhook secret for signature verification (auto-generated if not provided)')
@click.pass_context
def create(ctx, url, events, description, org, secret):
    """Create a new webhook"""
    client = get_client(ctx)
    
    try:
        webhook_data = {
            'url': url,
            'events': [e.strip() for e in events.split(',')],
            'description': description,
            'active': True
        }
        
        if org:
            webhook_data['organization_id'] = org
        if secret:
            webhook_data['secret'] = secret
        
        result = client.post('/api/v1/webhooks', json=webhook_data)
        
        console.print(f"\n[green]✅ Webhook created successfully![/green]")
        console.print(f"[cyan]Webhook ID:[/cyan] {result.get('webhook_id')}")
        console.print(f"[cyan]URL:[/cyan] {result.get('url')}")
        
        if result.get('secret'):
            console.print(f"\n[yellow]⚠️  Save this webhook secret securely:[/yellow]")
            console.print(f"[dim]{result['secret']}[/dim]\n")
        
    except Exception as e:
        console.print(f"[red]Failed to create webhook: {e}[/red]")
        raise click.Abort()


@webhooks.command()
@click.argument('webhook_id')
@click.option('--url', help='New webhook URL')
@click.option('--events', help='New comma-separated list of events')
@click.option('--description', help='New description')
@click.option('--active/--inactive', default=None, help='Activate or deactivate webhook')
@click.pass_context
def update(ctx, webhook_id, url, events, description, active):
    """Update webhook details"""
    client = get_client(ctx)
    
    try:
        update_data = {}
        if url:
            update_data['url'] = url
        if events:
            update_data['events'] = [e.strip() for e in events.split(',')]
        if description:
            update_data['description'] = description
        if active is not None:
            update_data['active'] = active
        
        if not update_data:
            console.print("[yellow]No updates specified[/yellow]")
            return
        
        result = client.patch(f'/api/v1/webhooks/{webhook_id}', json=update_data)
        
        console.print(f"[green]✅ Webhook updated successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to update webhook: {e}[/red]")
        raise click.Abort()


@webhooks.command()
@click.argument('webhook_id')
@click.confirmation_option(prompt='Are you sure you want to delete this webhook?')
@click.pass_context
def delete(ctx, webhook_id):
    """Delete a webhook"""
    client = get_client(ctx)
    
    try:
        client.delete(f'/api/v1/webhooks/{webhook_id}')
        console.print(f"[green]✅ Webhook deleted successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to delete webhook: {e}[/red]")
        raise click.Abort()


@webhooks.command()
@click.argument('webhook_id')
@click.option('--event', default='test.event', help='Event type to send')
@click.pass_context
def test(ctx, webhook_id, event):
    """Send a test webhook delivery"""
    client = get_client(ctx)
    
    try:
        test_data = {
            'event': event,
            'data': {
                'test': True,
                'message': 'This is a test webhook delivery from ops-center CLI'
            }
        }
        
        result = client.post(f'/api/v1/webhooks/{webhook_id}/test', json=test_data)
        
        console.print(f"[green]✅ Test webhook sent![/green]")
        console.print(f"[cyan]Delivery ID:[/cyan] {result.get('delivery_id', 'N/A')}")
        console.print(f"[cyan]Status:[/cyan] {result.get('status', 'pending')}")
        
    except Exception as e:
        console.print(f"[red]Failed to send test webhook: {e}[/red]")
        raise click.Abort()


@webhooks.command()
@click.argument('webhook_id')
@click.option('--limit', default=50, help='Maximum number of deliveries to show')
@click.option('--status', type=click.Choice(['pending', 'success', 'failed']),
              help='Filter by delivery status')
@click.pass_context
def deliveries(ctx, webhook_id, limit, status):
    """View webhook delivery history"""
    client = get_client(ctx)
    
    try:
        params = {'limit': limit}
        if status:
            params['status'] = status
        
        deliveries_data = client.get(f'/api/v1/webhooks/{webhook_id}/deliveries', params=params)
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(deliveries_data, indent=2))
            return
        
        deliveries_list = deliveries_data if isinstance(deliveries_data, list) else deliveries_data.get('deliveries', [])
        
        if not deliveries_list:
            console.print("[yellow]No deliveries found[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Webhook Deliveries ({len(deliveries_list)})")
        table.add_column("ID", style="cyan")
        table.add_column("Event", style="white")
        table.add_column("Status", style="green")
        table.add_column("Attempts", style="yellow", justify="right")
        table.add_column("Timestamp", style="dim")
        
        for delivery in deliveries_list:
            status_icon = {
                'success': '✓',
                'failed': '✗',
                'pending': '⏳'
            }.get(delivery.get('status', 'pending'), '?')
            
            table.add_row(
                delivery.get('delivery_id', 'N/A')[:8],
                delivery.get('event', 'N/A'),
                f"{status_icon} {delivery.get('status', 'pending')}",
                str(delivery.get('attempts', 0)),
                delivery.get('created_at', 'N/A')[:19] if delivery.get('created_at') else 'N/A'
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to fetch deliveries: {e}[/red]")
        raise click.Abort()


@webhooks.command()
@click.pass_context
def events(ctx):
    """List available webhook event types"""
    client = get_client(ctx)
    
    try:
        events_data = client.get('/api/v1/webhooks/events/available')
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(events_data, indent=2))
            return
        
        events_list = events_data if isinstance(events_data, list) else events_data.get('events', [])
        
        # Group events by category
        categories = {}
        for event in events_list:
            category = event.split('.')[0] if '.' in event else 'other'
            if category not in categories:
                categories[category] = []
            categories[category].append(event)
        
        for category, category_events in sorted(categories.items()):
            console.print(f"\n[bold cyan]{category.upper()}[/bold cyan]")
            for event in sorted(category_events):
                console.print(f"  • {event}")
        
        console.print(f"\n[dim]Total: {len(events_list)} events[/dim]\n")
        
    except Exception as e:
        console.print(f"[red]Failed to fetch available events: {e}[/red]")
        raise click.Abort()
