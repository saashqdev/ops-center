"""Organization management commands"""

import click
import json
from rich.console import Console
from rich.table import Table
from cli.commands.server import get_client

console = Console()


@click.group()
def orgs():
    """Organization management commands"""
    pass


@orgs.command()
@click.option('--limit', default=50, help='Maximum number of organizations to return')
@click.pass_context
def list(ctx, limit):
    """List all organizations"""
    client = get_client(ctx)
    
    try:
        params = {'limit': limit}
        orgs_data = client.get('/api/v1/org', params=params)
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(orgs_data, indent=2))
            return
        
        orgs_list = orgs_data if isinstance(orgs_data, list) else orgs_data.get('organizations', [])
        
        if not orgs_list:
            console.print("[yellow]No organizations found[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Organizations ({len(orgs_list)})")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Plan", style="green")
        table.add_column("Members", style="yellow", justify="right")
        table.add_column("Created", style="dim")
        
        for org in orgs_list:
            table.add_row(
                org.get('organization_id', 'N/A'),
                org.get('name', 'N/A'),
                org.get('plan_tier', 'N/A'),
                str(org.get('member_count', 0)),
                org.get('created_at', 'N/A')[:10] if org.get('created_at') else 'N/A'
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to list organizations: {e}[/red]")
        raise click.Abort()


@orgs.command()
@click.argument('org_id')
@click.pass_context
def get(ctx, org_id):
    """Get organization details"""
    client = get_client(ctx)
    
    try:
        org = client.get(f'/api/v1/org/{org_id}')
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(org, indent=2))
            return
        
        # Display org details
        table = Table(show_header=False, title=f"Organization: {org.get('name')}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Organization ID", org.get('organization_id', 'N/A'))
        table.add_row("Name", org.get('name', 'N/A'))
        table.add_row("Plan Tier", org.get('plan_tier', 'N/A'))
        table.add_row("Member Count", str(org.get('member_count', 0)))
        table.add_row("Created", org.get('created_at', 'N/A'))
        table.add_row("Owner", org.get('owner_email', 'N/A'))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to get organization: {e}[/red]")
        raise click.Abort()


@orgs.command()
@click.option('--name', prompt=True, help='Organization name')
@click.option('--plan', default='starter', help='Plan tier')
@click.pass_context
def create(ctx, name, plan):
    """Create a new organization"""
    client = get_client(ctx)
    
    try:
        org_data = {
            'name': name,
            'plan_tier': plan
        }
        
        result = client.post('/api/v1/org', json=org_data)
        
        console.print(f"\n[green]✅ Organization created successfully![/green]")
        console.print(f"[cyan]Organization ID:[/cyan] {result.get('organization_id')}")
        console.print(f"[cyan]Name:[/cyan] {result.get('name')}\n")
        
    except Exception as e:
        console.print(f"[red]Failed to create organization: {e}[/red]")
        raise click.Abort()


@orgs.command()
@click.argument('org_id')
@click.option('--name', help='New organization name')
@click.option('--plan', help='New plan tier')
@click.pass_context
def update(ctx, org_id, name, plan):
    """Update organization details"""
    client = get_client(ctx)
    
    try:
        update_data = {}
        if name:
            update_data['name'] = name
        if plan:
            update_data['plan_tier'] = plan
        
        if not update_data:
            console.print("[yellow]No updates specified[/yellow]")
            return
        
        result = client.patch(f'/api/v1/org/{org_id}', json=update_data)
        
        console.print(f"[green]✅ Organization updated successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to update organization: {e}[/red]")
        raise click.Abort()


@orgs.command()
@click.argument('org_id')
@click.confirmation_option(prompt='Are you sure you want to delete this organization?')
@click.pass_context
def delete(ctx, org_id):
    """Delete an organization"""
    client = get_client(ctx)
    
    try:
        client.delete(f'/api/v1/org/{org_id}')
        console.print(f"[green]✅ Organization deleted successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to delete organization: {e}[/red]")
        raise click.Abort()


@orgs.command()
@click.argument('org_id')
@click.pass_context
def members(ctx, org_id):
    """List organization members"""
    client = get_client(ctx)
    
    try:
        members = client.get(f'/api/v1/org/{org_id}/members')
        
        if ctx.obj['output_format'] == 'json':
            console.print(json.dumps(members, indent=2))
            return
        
        members_list = members if isinstance(members, list) else members.get('members', [])
        
        if not members_list:
            console.print("[yellow]No members found[/yellow]")
            return
        
        table = Table(title=f"Members of {org_id}")
        table.add_column("Email", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Role", style="green")
        table.add_column("Joined", style="dim")
        
        for member in members_list:
            table.add_row(
                member.get('email', 'N/A'),
                member.get('name', 'N/A'),
                member.get('role', 'N/A'),
                member.get('joined_at', 'N/A')[:10] if member.get('joined_at') else 'N/A'
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to list members: {e}[/red]")
        raise click.Abort()
