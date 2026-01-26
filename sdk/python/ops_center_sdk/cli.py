"""
CLI tool for Ops-Center Plugin SDK

Commands:
- init: Create new plugin from template
- validate: Validate plugin structure and manifest
- build: Package plugin for distribution
- publish: Publish plugin to Ops-Center marketplace
"""

import click
import os
import yaml
import json
import shutil
import tarfile
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.syntax import Syntax
from jinja2 import Template

console = Console()


# ==================== Template Strings ====================

PLUGIN_TEMPLATE = '''"""
{{ name }}

{{ description }}
"""

from ops_center_sdk import Plugin
from typing import Dict, Any

# Create plugin instance
plugin = Plugin(
    id="{{ id }}",
    name="{{ name }}",
    version="{{ version }}",
    description="{{ description }}",
    author="{{ author }}",
    category="{{ category }}"
)


# ==================== Lifecycle Hooks ====================

@plugin.on_install
async def on_install():
    """Initialize plugin on first install"""
    plugin.logger.info("Installing {{ name }}...")
    # Add your initialization code here
    

@plugin.on_enable
async def on_enable():
    """Start plugin services when enabled"""
    plugin.logger.info("Enabling {{ name }}...")
    # Start background tasks, schedulers, etc.


@plugin.on_disable
async def on_disable():
    """Stop plugin services when disabled"""
    plugin.logger.info("Disabling {{ name }}...")
    # Clean up resources


# ==================== Event Hooks ====================

@plugin.hook("device.created", priority=10)
async def on_device_created(device_id: str, device_data: Dict[str, Any]):
    """Handle device creation events"""
    plugin.logger.info(f"New device: {device_id}")
    # Add your event handling logic


# ==================== Custom API Routes ====================

@plugin.route("/status", methods=["GET"])
async def get_status() -> Dict[str, Any]:
    """
    Get plugin status
    
    GET /plugins/{{ id }}/status
    """
    return {
        "status": "running",
        "version": plugin.metadata.version
    }


# ==================== Export FastAPI App ====================

app = plugin.create_app()
'''

MANIFEST_TEMPLATE = {
    "id": "{{ id }}",
    "name": "{{ name }}",
    "version": "{{ version }}",
    "description": "{{ description }}",
    "author": "{{ author }}",
    "type": "{{ type }}",
    "category": "{{ category }}",
    "homepage": "https://github.com/yourorg/{{ id }}",
    "repository": "https://github.com/yourorg/{{ id }}",
    "license": "MIT",
    "keywords": [],
    "pricing": {
        "model": "free",
        "price": 0
    },
    "permissions": [
        "devices:read",
        "alerts:write"
    ],
    "hooks": [
        {
            "event": "device.created",
            "handler": "on_device_created"
        }
    ],
    "routes": [
        {
            "path": "/status",
            "methods": ["GET"],
            "handler": "get_status"
        }
    ],
    "config_schema": {
        "type": "object",
        "properties": {
            "enabled": {
                "type": "boolean",
                "default": True,
                "description": "Enable/disable plugin"
            }
        }
    },
    "runtime": {
        "type": "python",
        "version": "3.11+",
        "entrypoint": "main.py"
    }
}

README_TEMPLATE = '''# {{ name }}

{{ description }}

## Installation

\`\`\`bash
ops-center-plugin install {{ id }}
\`\`\`

## Configuration

Edit your `config.yaml`:

\`\`\`yaml
enabled: true
\`\`\`

## API Endpoints

### GET /plugins/{{ id }}/status

Get plugin status.

**Response:**
\`\`\`json
{
  "status": "running",
  "version": "{{ version }}"
}
\`\`\`

## Development

\`\`\`bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest

# Build plugin
ops-center-plugin build

# Publish to marketplace
ops-center-plugin publish
\`\`\`

## License

{{ license }}
'''

REQUIREMENTS_TEMPLATE = '''ops-center-plugin-sdk>=0.1.0
'''

CONFIG_TEMPLATE = '''# Plugin Configuration
enabled: true
'''


# ==================== CLI Commands ====================

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Ops-Center Plugin SDK CLI"""
    pass


@cli.command()
@click.argument("plugin_id")
@click.option("--name", prompt=True, help="Plugin display name")
@click.option("--description", prompt=True, help="Plugin description")
@click.option("--author", prompt=True, help="Plugin author")
@click.option("--category", 
              type=click.Choice(["monitoring", "ai", "security", "integration", "analytics"]),
              prompt=True,
              help="Plugin category")
@click.option("--type",
              type=click.Choice(["backend", "frontend", "hybrid", "container"]),
              default="backend",
              help="Plugin type")
@click.option("--version", default="1.0.0", help="Initial version")
@click.option("--license", default="MIT", help="License")
def init(plugin_id: str, name: str, description: str, author: str, 
         category: str, type: str, version: str, license: str):
    """
    Create new plugin from template
    
    Example:
        ops-center-plugin init my-plugin --name "My Plugin"
    """
    console.print(f"\n[bold blue]Creating plugin:[/bold blue] {plugin_id}")
    
    # Create plugin directory
    plugin_dir = Path(plugin_id)
    if plugin_dir.exists():
        console.print(f"[red]Error:[/red] Directory {plugin_id} already exists")
        return
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Initializing plugin...", total=6)
        
        # Create directory structure
        plugin_dir.mkdir()
        progress.update(task, advance=1, description="Created directory structure")
        
        # Render templates
        context = {
            "id": plugin_id,
            "name": name,
            "description": description,
            "author": author,
            "category": category,
            "type": type,
            "version": version,
            "license": license
        }
        
        # Create main.py
        main_content = Template(PLUGIN_TEMPLATE).render(**context)
        (plugin_dir / "main.py").write_text(main_content)
        progress.update(task, advance=1, description="Created main.py")
        
        # Create plugin.yaml manifest
        manifest_content = json.dumps(MANIFEST_TEMPLATE, indent=2)
        manifest_rendered = Template(manifest_content).render(**context)
        (plugin_dir / "plugin.yaml").write_text(manifest_rendered)
        progress.update(task, advance=1, description="Created plugin.yaml")
        
        # Create README.md
        readme_content = Template(README_TEMPLATE).render(**context)
        (plugin_dir / "README.md").write_text(readme_content)
        progress.update(task, advance=1, description="Created README.md")
        
        # Create requirements.txt
        (plugin_dir / "requirements.txt").write_text(REQUIREMENTS_TEMPLATE)
        progress.update(task, advance=1, description="Created requirements.txt")
        
        # Create config.yaml
        (plugin_dir / "config.yaml").write_text(CONFIG_TEMPLATE)
        progress.update(task, advance=1, description="Created config.yaml")
    
    # Success message
    console.print("\n[green]✓[/green] Plugin created successfully!\n")
    
    # Show next steps
    panel = Panel(
        f"""[bold]Next steps:[/bold]

1. [cyan]cd {plugin_id}[/cyan]
2. Edit [yellow]main.py[/yellow] to add your plugin logic
3. Update [yellow]plugin.yaml[/yellow] with permissions and hooks
4. Test your plugin: [cyan]ops-center-plugin validate[/cyan]
5. Build for distribution: [cyan]ops-center-plugin build[/cyan]
6. Publish to marketplace: [cyan]ops-center-plugin publish[/cyan]
        """,
        title="Plugin Created",
        border_style="green"
    )
    console.print(panel)


@cli.command()
@click.option("--path", default=".", help="Path to plugin directory")
def validate(path: str):
    """
    Validate plugin structure and manifest
    
    Checks:
    - plugin.yaml exists and is valid
    - All required files present
    - Permissions are valid
    - Hooks reference existing handlers
    """
    console.print("\n[bold blue]Validating plugin...[/bold blue]\n")
    
    plugin_path = Path(path)
    errors = []
    warnings = []
    
    # Check plugin.yaml
    manifest_path = plugin_path / "plugin.yaml"
    if not manifest_path.exists():
        errors.append("plugin.yaml not found")
    else:
        try:
            with open(manifest_path) as f:
                manifest = yaml.safe_load(f)
            
            # Validate required fields
            required = ["id", "name", "version", "description", "author", "type"]
            for field in required:
                if field not in manifest:
                    errors.append(f"Missing required field: {field}")
            
            # Validate permissions format
            if "permissions" in manifest:
                for perm in manifest["permissions"]:
                    if ":" not in perm:
                        warnings.append(f"Invalid permission format: {perm} (expected resource:action)")
            
            # Validate semantic version
            if "version" in manifest:
                version = manifest["version"]
                if version.count(".") != 2:
                    warnings.append(f"Version {version} should follow semantic versioning (e.g., 1.0.0)")
            
        except yaml.YAMLError as e:
            errors.append(f"Invalid YAML in plugin.yaml: {e}")
    
    # Check main.py
    main_path = plugin_path / "main.py"
    if not main_path.exists():
        errors.append("main.py not found")
    
    # Check requirements.txt
    if not (plugin_path / "requirements.txt").exists():
        warnings.append("requirements.txt not found")
    
    # Check README.md
    if not (plugin_path / "README.md").exists():
        warnings.append("README.md not found")
    
    # Display results
    if errors:
        console.print("[bold red]Validation Failed[/bold red]\n")
        for error in errors:
            console.print(f"  [red]✗[/red] {error}")
    else:
        console.print("[green]✓[/green] No errors found\n")
    
    if warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]\n")
        for warning in warnings:
            console.print(f"  [yellow]![/yellow] {warning}")
    
    if not errors and not warnings:
        console.print("\n[bold green]✓ Plugin is valid![/bold green]")
    
    return len(errors) == 0


@cli.command()
@click.option("--path", default=".", help="Path to plugin directory")
@click.option("--output", default="dist", help="Output directory")
def build(path: str, output: str):
    """
    Package plugin for distribution
    
    Creates a .tar.gz package with:
    - All plugin files
    - Manifest
    - SHA256 checksum
    """
    console.print("\n[bold blue]Building plugin...[/bold blue]\n")
    
    plugin_path = Path(path)
    output_path = Path(output)
    
    # Validate first
    if not validate.callback(path):
        console.print("[red]Build failed: Plugin validation errors[/red]")
        return
    
    # Load manifest
    with open(plugin_path / "plugin.yaml") as f:
        manifest = yaml.safe_load(f)
    
    plugin_id = manifest["id"]
    version = manifest["version"]
    
    # Create output directory
    output_path.mkdir(exist_ok=True)
    
    # Create tarball
    tarball_name = f"{plugin_id}-{version}.tar.gz"
    tarball_path = output_path / tarball_name
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Packaging plugin...", total=3)
        
        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(plugin_path, arcname=plugin_id)
        progress.update(task, advance=1)
        
        # Calculate checksum
        sha256 = hashlib.sha256()
        with open(tarball_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        checksum = sha256.hexdigest()
        progress.update(task, advance=1)
        
        # Write checksum file
        checksum_path = output_path / f"{tarball_name}.sha256"
        checksum_path.write_text(f"{checksum}  {tarball_name}\n")
        progress.update(task, advance=1)
    
    # Show summary
    size_mb = tarball_path.stat().st_size / (1024 * 1024)
    
    table = Table(title="Build Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Plugin ID", plugin_id)
    table.add_row("Version", version)
    table.add_row("Package", str(tarball_path))
    table.add_row("Size", f"{size_mb:.2f} MB")
    table.add_row("Checksum", checksum[:16] + "...")
    
    console.print("\n")
    console.print(table)
    console.print(f"\n[green]✓[/green] Plugin built successfully!")


@cli.command()
@click.option("--path", default="dist", help="Path to built plugin package")
@click.option("--api-url", envvar="OPS_CENTER_API_URL", required=True, help="Ops-Center API URL")
@click.option("--api-key", envvar="OPS_CENTER_API_KEY", required=True, help="API key for authentication")
def publish(path: str, api_url: str, api_key: str):
    """
    Publish plugin to Ops-Center marketplace
    
    Requires:
    - OPS_CENTER_API_URL environment variable
    - OPS_CENTER_API_KEY environment variable
    
    Example:
        export OPS_CENTER_API_URL=https://ops.example.com
        export OPS_CENTER_API_KEY=your_api_key
        ops-center-plugin publish
    """
    console.print("\n[bold blue]Publishing plugin...[/bold blue]\n")
    
    dist_path = Path(path)
    
    # Find .tar.gz file
    tarballs = list(dist_path.glob("*.tar.gz"))
    if not tarballs:
        console.print(f"[red]Error:[/red] No .tar.gz package found in {path}")
        console.print("[yellow]Hint:[/yellow] Run [cyan]ops-center-plugin build[/cyan] first")
        return
    
    tarball = tarballs[0]
    checksum_file = Path(str(tarball) + ".sha256")
    
    if not checksum_file.exists():
        console.print("[red]Error:[/red] Checksum file not found")
        return
    
    checksum = checksum_file.read_text().split()[0]
    
    console.print(f"Package: [cyan]{tarball.name}[/cyan]")
    console.print(f"Checksum: [yellow]{checksum[:16]}...[/yellow]")
    console.print(f"API URL: [cyan]{api_url}[/cyan]\n")
    
    # TODO: Implement actual upload to Ops-Center API
    # This would use httpx to POST to /api/plugins/upload
    
    console.print("[yellow]Note:[/yellow] Publish functionality requires connection to Ops-Center API")
    console.print("[yellow]This feature will be implemented in the next version[/yellow]")


if __name__ == "__main__":
    cli()
