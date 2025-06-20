#!/usr/bin/env python3
import os
import sys
import ast
import difflib
from typing import Dict, List, Optional, Tuple, Any
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table
from rich.panel import Panel
import json
import base64
import hashlib
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # dotenv is optional

console = Console()

def capture_execution(file_path: str) -> Tuple[str, Optional[str]]:
    """Execute a Python file and capture output and errors"""
    import io
    import contextlib
    from types import ModuleType
    
    stdout = io.StringIO()
    stderr = io.StringIO()
    error_info = None
    
    try:
        # Create a temporary module for execution
        module_name = os.path.basename(file_path).replace('.py', '')
        module = ModuleType(module_name)
        module.__file__ = file_path
        
        # Read the file content
        with open(file_path, 'r') as f:
            code = f.read()
        
        # Redirect stdout and stderr
        with contextlib.redirect_stdout(stdout):
            with contextlib.redirect_stderr(stderr):
                # Execute the code in the module's namespace
                exec(code, module.__dict__)
                
        output = stdout.getvalue()
        error_output = stderr.getvalue()
        
        return output + error_output, None
        
    except Exception as e:
        import traceback
        error_info = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        return stderr.getvalue(), error_info

def show_diff(original: str, modified: str, filename: str) -> None:
    """Show the difference between original and modified code"""
    original_lines = original.splitlines(True)
    modified_lines = modified.splitlines(True)
    
    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"{filename} (original)",
        tofile=f"{filename} (modified)",
        lineterm=''
    )
    
    diff_text = ''.join(diff)
    if diff_text:
        console.print(Panel.fit(Syntax(diff_text, "diff"), title="Changes", border_style="green"))
    else:
        console.print("[yellow]No changes made[/yellow]")

def check_python_version() -> bool:
    """Check if Python version is compatible"""
    major, minor = sys.version_info[:2]
    if major < 3 or (major == 3 and minor < 7):
        console.print("[red]Error: This tool requires Python 3.7 or higher[/red]")
        return False
    return True

def get_code_complexity_metrics(code: str) -> Dict[str, Any]:
    """Calculate code complexity metrics"""
    try:
        tree = ast.parse(code)
        
        # Count various code elements
        metrics = {
            "lines": len(code.splitlines()),
            "functions": 0,
            "classes": 0,
            "imports": 0,
            "comments": len([line for line in code.splitlines() if line.strip().startswith('#')]),
            "cyclomatic_complexity": 0,  # Simplified version
        }
        
        # Count control flow statements for a simplified cyclomatic complexity
        control_flow_count = 0
        
        class ComplexityVisitor(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                nonlocal metrics
                metrics["functions"] += 1
                self.generic_visit(node)
                
            def visit_ClassDef(self, node):
                nonlocal metrics
                metrics["classes"] += 1
                self.generic_visit(node)
                
            def visit_Import(self, node):
                nonlocal metrics
                metrics["imports"] += len(node.names)
                self.generic_visit(node)
                
            def visit_ImportFrom(self, node):
                nonlocal metrics
                metrics["imports"] += len(node.names)
                self.generic_visit(node)
                
            def visit_If(self, node):
                nonlocal control_flow_count
                control_flow_count += 1
                self.generic_visit(node)
                
            def visit_For(self, node):
                nonlocal control_flow_count
                control_flow_count += 1
                self.generic_visit(node)
                
            def visit_While(self, node):
                nonlocal control_flow_count
                control_flow_count += 1
                self.generic_visit(node)
                
            def visit_Try(self, node):
                nonlocal control_flow_count
                control_flow_count += 1 + len(node.handlers)  # +1 for each except block
                self.generic_visit(node)
        
        ComplexityVisitor().visit(tree)
        metrics["cyclomatic_complexity"] = control_flow_count + 1  # Base complexity is 1
        
        return metrics
        
    except SyntaxError:
        # Return basic metrics if code has syntax errors
        return {
            "lines": len(code.splitlines()),
            "comments": len([line for line in code.splitlines() if line.strip().startswith('#')]),
            "error": "Syntax error in code"
        }

def display_complexity_report(metrics: Dict[str, Any]) -> None:
    """Display a code complexity report"""
    table = Table(title="Code Complexity Metrics")
    
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Rating", style="yellow")
    
    for metric, value in metrics.items():
        if metric == "error":
            continue
            
        rating = "N/A"
        
        # Generate ratings based on common thresholds
        if metric == "lines":
            if value < 100:
                rating = "Good"
            elif value < 300:
                rating = "Moderate"
            else:
                rating = "High"
                
        elif metric == "cyclomatic_complexity":
            if value < 5:
                rating = "Low"
            elif value < 10:
                rating = "Moderate"
            else:
                rating = "High"
                
        elif metric == "functions":
            if value < 5:
                rating = "Simple"
            elif value < 15:
                rating = "Moderate"
            else:
                rating = "Complex"
        
        table.add_row(metric, str(value), rating)
    
    console.print(table)

def check_dependencies() -> List[str]:
    """Check if all required dependencies are installed"""
    missing_dependencies = []
    
    required_packages = [
        "openai",
        "rich"
    ]
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_dependencies.append(package)
    
    return missing_dependencies

# Secure API Key Storage Functions
def _get_config_dir() -> Path:
    """Get the configuration directory for storing encrypted API keys"""
    if sys.platform == "win32":
        config_dir = Path(os.environ.get("APPDATA", "")) / "nova-cli"
    elif sys.platform == "darwin":
        config_dir = Path.home() / "Library" / "Application Support" / "nova-cli"
    else:  # Linux and other Unix-like systems
        config_dir = Path.home() / ".config" / "nova-cli"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir

def _get_machine_id() -> str:
    """Generate a unique machine identifier for encryption"""
    import platform
    import uuid
    
    # Create a unique identifier based on machine characteristics
    machine_info = f"{platform.node()}-{platform.machine()}-{platform.processor()}"
    
    # Try to get MAC address as additional entropy
    try:
        mac = uuid.getnode()
        machine_info += f"-{mac}"
    except:
        pass
    
    # Hash the machine info to create a consistent key
    return hashlib.sha256(machine_info.encode()).hexdigest()[:32]

def _simple_encrypt(data: str, key: str) -> str:
    """Simple XOR encryption (not cryptographically secure but better than plaintext)"""
    key_bytes = key.encode()
    data_bytes = data.encode()
    
    encrypted = bytearray()
    for i, byte in enumerate(data_bytes):
        encrypted.append(byte ^ key_bytes[i % len(key_bytes)])
    
    return base64.b64encode(encrypted).decode()

def _simple_decrypt(encrypted_data: str, key: str) -> str:
    """Simple XOR decryption"""
    try:
        key_bytes = key.encode()
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        
        decrypted = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ key_bytes[i % len(key_bytes)])
        
        return decrypted.decode()
    except:
        return ""

def save_api_key(api_key: str) -> bool:
    """Securely save the API key to local storage"""
    try:
        config_dir = _get_config_dir()
        config_file = config_dir / "config.json"
        
        # Get machine-specific encryption key
        machine_key = _get_machine_id()
        
        # Encrypt the API key
        encrypted_key = _simple_encrypt(api_key, machine_key)
        
        # Save to config file
        config_data = {
            "encrypted_api_key": encrypted_key,
            "version": "1.0"
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Set restrictive permissions (Unix-like systems only)
        if hasattr(os, 'chmod'):
            os.chmod(config_file, 0o600)  # Read/write for owner only
        
        console.print(f"[green]✅ API key saved securely to {config_file}[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Failed to save API key: {str(e)}[/red]")
        return False

def load_api_key() -> Optional[str]:
    """Load and decrypt the saved API key"""
    try:
        config_dir = _get_config_dir()
        config_file = config_dir / "config.json"
        
        if not config_file.exists():
            return None
        
        # Load config file
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        encrypted_key = config_data.get("encrypted_api_key")
        if not encrypted_key:
            return None
        
        # Get machine-specific decryption key
        machine_key = _get_machine_id()
        
        # Decrypt the API key
        api_key = _simple_decrypt(encrypted_key, machine_key)
        
        if api_key:
            console.print("[green]🔓 API key loaded from secure storage[/green]")
            return api_key
        else:
            console.print("[yellow]⚠️ Failed to decrypt saved API key[/yellow]")
            return None
            
    except Exception as e:
        console.print(f"[red]❌ Failed to load API key: {str(e)}[/red]")
        return None

def delete_saved_api_key() -> bool:
    """Delete the saved API key"""
    try:
        config_dir = _get_config_dir()
        config_file = config_dir / "config.json"
        
        if config_file.exists():
            config_file.unlink()
            console.print("[green]🗑️ Saved API key deleted[/green]")
            return True
        else:
            console.print("[yellow]No saved API key found[/yellow]")
            return False
            
    except Exception as e:
        console.print(f"[red]❌ Failed to delete API key: {str(e)}[/red]")
        return False

def get_api_key_interactive() -> str:
    """Get API key interactively with option to save"""
    from rich.prompt import Prompt, Confirm
    
    # First try to load saved API key
    saved_key = load_api_key()
    if saved_key:
        if Confirm.ask("Use saved API key?", default=True):
            return saved_key
        else:
            console.print("[yellow]Enter a new API key...[/yellow]")
    
    # Get new API key
    api_key = Prompt.ask(
        "[cyan]Please enter your SambaNova API Key[/cyan]",
        password=True  # Hide input
    )
    
    if not api_key.strip():
        console.print("[red]API Key cannot be empty. Exiting.[/red]")
        sys.exit(1)
    
    # Ask if user wants to save it
    if Confirm.ask("Save this API key securely for future use?", default=True):
        if save_api_key(api_key.strip()):
            console.print("[green]✅ API key will be loaded automatically next time![/green]")
        else:
            console.print("[yellow]⚠️ API key not saved, you'll need to enter it again next time[/yellow]")
    
    return api_key.strip() 