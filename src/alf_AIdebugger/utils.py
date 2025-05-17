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