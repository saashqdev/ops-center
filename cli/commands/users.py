"""User management commands"""

import click
import json
from rich.console import Console
from rich.table import Table
from cli.commands.server import get_client

console = Console()


@click.group()
def users():
    """User management commands"""
    pass


@users.command()
@click.option('--org', help='Filter by organization ID')
@click.option('--tier', help='Filter by subscription tier')
@click.option('--limit', default=50, help='Maximum number of users to return')
@click.pass_context
def list(ctx, org, tier, limit):
    """List all users"""
    client = get_client(ctx)
    
    try:
        params = {'limit': limit}
        if org:
            params['org_id'] = org
        if tier:
            params['tier'] = tier
        
        users_data = client.get('/api/v1/admin/users', params=params)
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(users_data, indent=2))
            return
        
        users_list = users_data if isinstance(users_data, list) else users_data.get('users', [])
        
        if not users_list:
            console.print("[yellow]No users found[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Users ({len(users_list)})")
        table.add_column("Email", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Tier", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="dim")
        
        for user in users_list:
            status_icon = "✓" if user.get('is_active') else "✗"
            table.add_row(
                user.get('email', 'N/A'),
                user.get('name', 'N/A'),
                user.get('subscription_tier', 'N/A'),
                status_icon,
                user.get('created_at', 'N/A')[:10] if user.get('created_at') else 'N/A'
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to list users: {e}[/red]")
        raise click.Abort()


@users.command()
@click.argument('email')
@click.pass_context
def get(ctx, email):
    """Get user details by email"""
    client = get_client(ctx)
    
    try:
        user = client.get(f'/api/v1/admin/users/{email}')
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(user, indent=2))
            return
        
        # Display user details
        table = Table(show_header=False, title=f"User: {email}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Email", user.get('email', 'N/A'))
        table.add_row("Name", user.get('name', 'N/A'))
        table.add_row("User ID", user.get('user_id', 'N/A'))
        table.add_row("Subscription Tier", user.get('subscription_tier', 'N/A'))
        table.add_row("Status", "Active" if user.get('is_active') else "Inactive")
        table.add_row("Created", user.get('created_at', 'N/A'))
        table.add_row("Last Login", user.get('last_login_at', 'Never'))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to get user: {e}[/red]")
        raise click.Abort()


@users.command()
@click.argument('email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True,
              help='User password')
@click.option('--name', prompt=True, help='User full name')
@click.option('--tier', default='trial', help='Subscription tier')
@click.pass_context
def create(ctx, email, password, name, tier):
    """Create a new user"""
    client = get_client(ctx)
    
    try:
        user_data = {
            'email': email,
            'password': password,
            'name': name,
            'subscription_tier': tier
        }
        
        result = client.post('/api/v1/admin/users', json=user_data)
        
        console.print(f"\n[green]✅ User created successfully![/green]")
        console.print(f"[cyan]Email:[/cyan] {result.get('email')}")
        console.print(f"[cyan]User ID:[/cyan] {result.get('user_id')}\n")
        
    except Exception as e:
        console.print(f"[red]Failed to create user: {e}[/red]")
        raise click.Abort()


@users.command()
@click.argument('email')
@click.option('--tier', help='New subscription tier')
@click.option('--name', help='New name')
@click.option('--active/--inactive', default=None, help='Activate or deactivate user')
@click.pass_context
def update(ctx, email, tier, name, active):
    """Update user details"""
    client = get_client(ctx)
    
    try:
        update_data = {}
        if tier:
            update_data['subscription_tier'] = tier
        if name:
            update_data['name'] = name
        if active is not None:
            update_data['is_active'] = active
        
        if not update_data:
            console.print("[yellow]No updates specified[/yellow]")
            return
        
        result = client.patch(f'/api/v1/admin/users/{email}', json=update_data)
        
        console.print(f"[green]✅ User updated successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to update user: {e}[/red]")
        raise click.Abort()


@users.command()
@click.argument('email')
@click.confirmation_option(prompt='Are you sure you want to delete this user?')
@click.pass_context
def delete(ctx, email):
    """Delete a user"""
    client = get_client(ctx)
    
    try:
        client.delete(f'/api/v1/admin/users/{email}')
        console.print(f"[green]✅ User {email} deleted successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to delete user: {e}[/red]")
        raise click.Abort()


@users.command()
@click.argument('email')
@click.pass_context
def usage(ctx, email):
    """Show user API usage statistics"""
    client = get_client(ctx)
    
    try:
        usage_data = client.get(f'/api/v1/admin/users/{email}/usage')
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(usage_data, indent=2))
            return
        
        table = Table(title=f"Usage for {email}")
        table.add_column("Period", style="cyan")
        table.add_column("Requests", style="green", justify="right")
        table.add_column("Tokens", style="yellow", justify="right")
        table.add_column("Cost", style="magenta", justify="right")
        
        for period in usage_data.get('periods', []):
            table.add_row(
                period.get('period', 'N/A'),
                str(period.get('requests', 0)),
                str(period.get('tokens', 0)),
                f"${period.get('cost', 0):.2f}"
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to fetch usage: {e}[/red]")
        raise click.Abort()
