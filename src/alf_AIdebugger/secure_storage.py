# Create src/alf_AIdebugger/secure_storage.py

#!/usr/bin/env python3
import os
import sys
import json
import base64
import hashlib
import platform
import uuid
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()

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