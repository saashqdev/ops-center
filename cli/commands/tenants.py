"""
Tenant management commands for Ops-Center CLI

Commands for managing multi-tenant organizations in Ops-Center.
"""

import click
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from cli.api_client import APIClient
from cli.config import ConfigManager

console = Console()


@click.group()
def tenants():
    """Manage multi-tenant organizations"""
    pass


@tenants.command('list')
@click.option('--tier', type=click.Choice(['trial', 'starter', 'professional', 'enterprise']),
              help='Filter by subscription tier')
@click.option('--active-only/--all', default=True, help='Show only active tenants')
@click.option('--search', '-s', help='Search by name or subdomain')
@click.option('--page', default=1, help='Page number')
@click.option('--page-size', default=20, help='Results per page')
@click.pass_context
def list_tenants(ctx, tier, active_only, search, page, page_size):
    """List all tenants"""
    config = ConfigManager(ctx.obj.get('config_path'))
    client = APIClient(config, ctx.obj.get('api_url'), ctx.obj.get('api_key'))
    
    params = {
        'page': page,
        'page_size': page_size,
        'active_only': active_only
    }
    
    if tier:
        params['tier'] = tier
    if search:
        params['search'] = search
    
    with Progress(SpinnerColumn(), TextColumn("[cyan]Loading tenants...")) as progress:
        progress.add_task("fetch", total=None)
        response = client.get('/api/v1/admin/tenants', params=params)
    
    if ctx.obj.get('output_format') == 'json':
        console.print_json(data=response)
        return
    
    if ctx.obj.get('output_format') == 'yaml':
        import yaml
        console.print(yaml.dump(response, default_flow_style=False))
        return
    
    # Table output
    tenants = response.get('tenants', [])
    total = response.get('total', 0)
    
    if not tenants:
        console.print("[yellow]No tenants found[/yellow]")
        return
    
    table = Table(title=f"Tenants (Page {page}, Total: {total})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold")
    table.add_column("Subdomain", style="magenta")
    table.add_column("Tier", style="green")
    table.add_column("Members", justify="right")
    table.add_column("Status", style="yellow")
    
    for tenant in tenants:
        status = "🟢 Active" if tenant.get('is_active') else "🔴 Inactive"
        table.add_row(
            tenant.get('id', '')[:8],
            tenant.get('name', 'N/A'),
            tenant.get('subdomain', 'N/A'),
            tenant.get('subscription_tier', 'N/A'),
            str(tenant.get('member_count', 0)),
            status
        )
    
    console.print(table)
    
    # Pagination info
    total_pages = (total + page_size - 1) // page_size
    if total_pages > 1:
        console.print(f"\n[dim]Page {page} of {total_pages}[/dim]")


@tenants.command('create')
@click.option('--name', required=True, help='Organization name')
@click.option('--subdomain', required=True, help='Subdomain (e.g., acme for acme.ops-center.com)')
@click.option('--tier', type=click.Choice(['trial', 'starter', 'professional', 'enterprise']),
              default='trial', help='Subscription tier')
@click.option('--custom-domain', help='Custom domain (optional)')
@click.option('--admin-email', required=True, help='Admin user email')
@click.option('--admin-name', required=True, help='Admin user name')
@click.option('--admin-password', prompt=True, hide_input=True, 
              confirmation_prompt=True, help='Admin user password')
@click.pass_context
def create_tenant(ctx, name, subdomain, tier, custom_domain, admin_email, admin_name, admin_password):
    """Create a new tenant"""
    config = ConfigManager(ctx.obj.get('config_path'))
    client = APIClient(config, ctx.obj.get('api_url'), ctx.obj.get('api_key'))
    
    data = {
        'name': name,
        'subdomain': subdomain,
        'tier': tier,
        'admin_email': admin_email,
        'admin_name': admin_name,
        'admin_password': admin_password
    }
    
    if custom_domain:
        data['custom_domain'] = custom_domain
    
    console.print(f"\n[cyan]Creating tenant '{name}'...[/cyan]")
    
    try:
        response = client.post('/api/v1/admin/tenants', json=data)
        
        if ctx.obj.get('output_format') == 'json':
            console.print_json(data=response)
            return
        
        # Success panel
        tenant_id = response.get('id', '')
        panel_content = f"""[green]✓[/green] Tenant created successfully!

[bold]Organization:[/bold] {name}
[bold]ID:[/bold] {tenant_id}
[bold]Subdomain:[/bold] {subdomain}.ops-center.com
[bold]Tier:[/bold] {tier}
[bold]Admin Email:[/bold] {admin_email}

[cyan]Access URL:[/cyan] https://{subdomain}.ops-center.com
"""
        
        console.print(Panel(panel_content, title="[bold green]Tenant Created[/bold green]", 
                           border_style="green"))
        
    except Exception as e:
        console.print(f"[red]✗ Error creating tenant: {e}[/red]")
        raise click.Abort()


@tenants.command('get')
@click.argument('tenant_id')
@click.option('--quota/--no-quota', default=False, help='Include quota information')
@click.pass_context
def get_tenant(ctx, tenant_id, quota):
    """Get tenant details"""
    config = ConfigManager(ctx.obj.get('config_path'))
    client = APIClient(config, ctx.obj.get('api_url'), ctx.obj.get('api_key'))
    
    params = {'include_quota': quota}
    response = client.get(f'/api/v1/admin/tenants/{tenant_id}', params=params)
    
    if ctx.obj.get('output_format') == 'json':
        console.print_json(data=response)
        return
    
    if ctx.obj.get('output_format') == 'yaml':
        import yaml
        console.print(yaml.dump(response, default_flow_style=False))
        return
    
    # Formatted output
    console.print(f"\n[bold cyan]Tenant Details[/bold cyan]\n")
    
    info_table = Table(show_header=False, box=None)
    info_table.add_column("Field", style="bold")
    info_table.add_column("Value")
    
    info_table.add_row("ID", response.get('id', 'N/A'))
    info_table.add_row("Name", response.get('name', 'N/A'))
    info_table.add_row("Subdomain", response.get('subdomain', 'N/A'))
    info_table.add_row("Custom Domain", response.get('custom_domain') or 'Not configured')
    info_table.add_row("Tier", response.get('subscription_tier', 'N/A'))
    info_table.add_row("Members", str(response.get('member_count', 0)))
    info_table.add_row("Status", "🟢 Active" if response.get('is_active') else "🔴 Inactive")
    info_table.add_row("Created", response.get('created_at', 'N/A'))
    
    console.print(info_table)
    
    # Quota information if requested
    if quota and 'quota' in response:
        console.print(f"\n[bold cyan]Resource Quotas[/bold cyan]\n")
        
        quota_table = Table()
        quota_table.add_column("Resource", style="bold")
        quota_table.add_column("Current", justify="right")
        quota_table.add_column("Max", justify="right")
        quota_table.add_column("Usage", justify="right")
        
        for resource, quota_info in response['quota'].items():
            current = quota_info.get('current', 0)
            max_allowed = quota_info.get('max', 0)
            percentage = quota_info.get('percentage', 0)
            
            max_str = "Unlimited" if max_allowed == -1 else str(max_allowed)
            usage_str = f"{percentage:.1f}%" if max_allowed != -1 else "N/A"
            
            quota_table.add_row(
                resource.replace('_', ' ').title(),
                str(current),
                max_str,
                usage_str
            )
        
        console.print(quota_table)


@tenants.command('update')
@click.argument('tenant_id')
@click.option('--name', help='Update organization name')
@click.option('--tier', type=click.Choice(['trial', 'starter', 'professional', 'enterprise']),
              help='Update subscription tier')
@click.option('--subdomain', help='Update subdomain')
@click.option('--custom-domain', help='Update custom domain')
@click.option('--activate/--deactivate', default=None, help='Activate or deactivate tenant')
@click.pass_context
def update_tenant(ctx, tenant_id, name, tier, subdomain, custom_domain, activate):
    """Update tenant configuration"""
    config = ConfigManager(ctx.obj.get('config_path'))
    client = APIClient(config, ctx.obj.get('api_url'), ctx.obj.get('api_key'))
    
    data = {}
    
    if name:
        data['name'] = name
    if tier:
        data['tier'] = tier
    if subdomain:
        data['subdomain'] = subdomain
    if custom_domain:
        data['custom_domain'] = custom_domain
    if activate is not None:
        data['is_active'] = activate
    
    if not data:
        console.print("[yellow]No updates specified[/yellow]")
        return
    
    console.print(f"[cyan]Updating tenant {tenant_id}...[/cyan]")
    
    try:
        response = client.patch(f'/api/v1/admin/tenants/{tenant_id}', json=data)
        
        if ctx.obj.get('output_format') == 'json':
            console.print_json(data=response)
            return
        
        console.print(f"[green]✓ Tenant updated successfully[/green]")
        
        # Show updated fields
        if name:
            console.print(f"  Name: {name}")
        if tier:
            console.print(f"  Tier: {tier}")
        if subdomain:
            console.print(f"  Subdomain: {subdomain}")
        if custom_domain:
            console.print(f"  Custom Domain: {custom_domain}")
        if activate is not None:
            console.print(f"  Status: {'Active' if activate else 'Inactive'}")
            
    except Exception as e:
        console.print(f"[red]✗ Error updating tenant: {e}[/red]")
        raise click.Abort()


@tenants.command('delete')
@click.argument('tenant_id')
@click.option('--permanent', is_flag=True, help='Permanently delete (hard delete)')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation')
@click.pass_context
def delete_tenant(ctx, tenant_id, permanent, yes):
    """Delete a tenant"""
    config = ConfigManager(ctx.obj.get('config_path'))
    client = APIClient(config, ctx.obj.get('api_url'), ctx.obj.get('api_key'))
    
    # Get tenant info first
    try:
        tenant = client.get(f'/api/v1/admin/tenants/{tenant_id}')
        tenant_name = tenant.get('name', tenant_id)
    except:
        tenant_name = tenant_id
    
    # Confirmation
    delete_type = "PERMANENTLY DELETE" if permanent else "deactivate"
    
    if not yes:
        if permanent:
            console.print(f"\n[bold red]⚠️  WARNING: This will PERMANENTLY delete all data for '{tenant_name}'[/bold red]")
            console.print("[yellow]This action CANNOT be undone![/yellow]\n")
        else:
            console.print(f"\n[yellow]This will deactivate '{tenant_name}'[/yellow]")
            console.print("[dim]Data will be preserved and can be reactivated later.[/dim]\n")
        
        if not click.confirm(f"Are you sure you want to {delete_type} this tenant?"):
            console.print("[yellow]Cancelled[/yellow]")
            return
    
    console.print(f"[cyan]Deleting tenant {tenant_name}...[/cyan]")
    
    try:
        params = {'permanent': permanent}
        client.delete(f'/api/v1/admin/tenants/{tenant_id}', params=params)
        
        if permanent:
            console.print(f"[green]✓ Tenant permanently deleted[/green]")
        else:
            console.print(f"[green]✓ Tenant deactivated[/green]")
            console.print(f"[dim]Reactivate with: ops-center tenants update {tenant_id} --activate[/dim]")
            
    except Exception as e:
        console.print(f"[red]✗ Error deleting tenant: {e}[/red]")
        raise click.Abort()


@tenants.command('stats')
@click.argument('tenant_id')
@click.pass_context
def tenant_stats(ctx, tenant_id):
    """Get tenant usage statistics"""
    config = ConfigManager(ctx.obj.get('config_path'))
    client = APIClient(config, ctx.obj.get('api_url'), ctx.obj.get('api_key'))
    
    response = client.get(f'/api/v1/admin/tenants/{tenant_id}/stats')
    
    if ctx.obj.get('output_format') == 'json':
        console.print_json(data=response)
        return
    
    if ctx.obj.get('output_format') == 'yaml':
        import yaml
        console.print(yaml.dump(response, default_flow_style=False))
        return
    
    # Table output
    console.print(f"\n[bold cyan]Tenant Statistics[/bold cyan]\n")
    
    stats_table = Table(show_header=False, box=None)
    stats_table.add_column("Metric", style="bold")
    stats_table.add_column("Value", justify="right")
    
    stats_table.add_row("Total Users", str(response.get('total_users', 0)))
    stats_table.add_row("Total Devices", str(response.get('total_devices', 0)))
    stats_table.add_row("Total Webhooks", str(response.get('total_webhooks', 0)))
    stats_table.add_row("Storage Used", f"{response.get('storage_used_gb', 0):.2f} GB")
    stats_table.add_row("API Calls (30d)", str(response.get('api_calls_last_30_days', 0)))
    stats_table.add_row("Active Users (7d)", str(response.get('active_users_last_7_days', 0)))
    
    console.print(stats_table)


@tenants.command('quota')
@click.argument('tenant_id')
@click.pass_context
def tenant_quota(ctx, tenant_id):
    """Get tenant quota status"""
    config = ConfigManager(ctx.obj.get('config_path'))
    client = APIClient(config, ctx.obj.get('api_url'), ctx.obj.get('api_key'))
    
    response = client.get(f'/api/v1/admin/tenants/{tenant_id}/quota')
    
    if ctx.obj.get('output_format') == 'json':
        console.print_json(data=response)
        return
    
    # Table output
    console.print(f"\n[bold cyan]Quota Status[/bold cyan]\n")
    
    quota_table = Table()
    quota_table.add_column("Resource", style="bold")
    quota_table.add_column("Current", justify="right")
    quota_table.add_column("Maximum", justify="right")
    quota_table.add_column("Available", justify="right")
    quota_table.add_column("Usage", justify="right", style="yellow")
    quota_table.add_column("Status", justify="center")
    
    for resource, quota_info in response.items():
        current = quota_info.get('current_usage', 0)
        max_allowed = quota_info.get('max_allowed', 0)
        percentage = quota_info.get('percentage_used', 0)
        is_at_limit = quota_info.get('is_at_limit', False)
        
        max_str = "Unlimited" if max_allowed == -1 else str(max_allowed)
        available = max_allowed - current if max_allowed > 0 else "Unlimited"
        available_str = str(available) if isinstance(available, int) else available
        usage_str = f"{percentage:.1f}%" if max_allowed != -1 else "N/A"
        
        # Status indicator
        if max_allowed == -1:
            status = "⚪"
        elif is_at_limit:
            status = "🔴"
        elif percentage >= 80:
            status = "🟡"
        else:
            status = "🟢"
        
        quota_table.add_row(
            resource.replace('_', ' ').title(),
            str(current),
            max_str,
            available_str,
            usage_str,
            status
        )
    
    console.print(quota_table)
    
    # Legend
    console.print("\n[dim]Status: 🟢 OK  🟡 Warning (>80%)  🔴 At Limit  ⚪ Unlimited[/dim]")


@tenants.command('platform-stats')
@click.pass_context
def platform_stats(ctx):
    """Get platform-wide tenant statistics"""
    config = ConfigManager(ctx.obj.get('config_path'))
    client = APIClient(config, ctx.obj.get('api_url'), ctx.obj.get('api_key'))
    
    response = client.get('/api/v1/admin/analytics/platform-stats')
    
    if ctx.obj.get('output_format') == 'json':
        console.print_json(data=response)
        return
    
    # Panel output
    console.print(f"\n[bold cyan]Platform Statistics[/bold cyan]\n")
    
    # Main stats
    stats_table = Table(show_header=False, box=None)
    stats_table.add_column("Metric", style="bold cyan")
    stats_table.add_column("Value", justify="right", style="bold")
    
    stats_table.add_row("Total Tenants", str(response.get('total_tenants', 0)))
    stats_table.add_row("Active Tenants", str(response.get('active_tenants', 0)))
    stats_table.add_row("Total Users", str(response.get('total_users', 0)))
    stats_table.add_row("Total Devices", str(response.get('total_devices', 0)))
    stats_table.add_row("Total Webhooks", str(response.get('total_webhooks', 0)))
    stats_table.add_row("Growth (30d)", str(response.get('growth_last_30_days', 0)))
    
    console.print(stats_table)
    
    # Tier distribution
    tier_dist = response.get('tier_distribution', {})
    if tier_dist:
        console.print(f"\n[bold cyan]Tier Distribution[/bold cyan]\n")
        
        tier_table = Table()
        tier_table.add_column("Tier", style="bold")
        tier_table.add_column("Count", justify="right")
        tier_table.add_column("Percentage", justify="right")
        
        total = sum(tier_dist.values())
        for tier, count in tier_dist.items():
            percentage = (count / total * 100) if total > 0 else 0
            tier_table.add_row(
                tier.title(),
                str(count),
                f"{percentage:.1f}%"
            )
        
        console.print(tier_table)


if __name__ == '__main__':
    tenants()
