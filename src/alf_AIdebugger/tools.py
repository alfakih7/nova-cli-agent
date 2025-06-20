#!/usr/bin/env python3
"""
Tools system for NOVA-CLI-AGENT
All AI capabilities are treated as individual tools that can be invoked as needed.
"""

import os
import sys
import json
import subprocess
import shutil
from typing import Dict, Any, List, Optional, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress
from rich.markdown import Markdown
from rich.prompt import Confirm, Prompt
from rich.table import Table
import openai

from .prompts import get_system_prompt, get_task_prompt, get_fix_prompt
from .web_search import search_web, search_news, format_search_results, display_search_results, is_web_search_available
from .utils import capture_execution, show_diff

console = Console()

class ToolResult:
    """Result object for tool execution"""
    def __init__(self, success: bool, data: Any = None, message: str = "", error: str = ""):
        self.success = success
        self.data = data
        self.message = message
        self.error = error

class AIToolkit:
    """Comprehensive toolkit for AI-powered development operations"""
    
    def __init__(self, client: openai.OpenAI):
        self.client = client
        self.console = console
        
    def get_available_tools(self) -> List[str]:
        """Get list of all available tools"""
        return [
            "analyze_code", "generate_code", "fix_code", "refactor_code", "optimize_code",
            "predict_bugs", "explain_concept", "web_search", "create_file", "edit_file",
            "read_file", "delete_file", "list_files", "execute_command", "chat_completion"
        ]
    
    def describe_tool(self, tool_name: str) -> str:
        """Get description of a specific tool"""
        descriptions = {
            "analyze_code": "Analyze code for bugs, issues, and improvements",
            "generate_code": "Generate new code based on requirements",
            "fix_code": "Fix bugs and issues in existing code",
            "refactor_code": "Improve code structure and readability",
            "optimize_code": "Optimize code for better performance",
            "predict_bugs": "Predict potential bugs and edge cases",
            "explain_concept": "Explain programming concepts and topics",
            "web_search": "Search the web for current information",
            "create_file": "Create new files with content",
            "edit_file": "Edit existing files with AI assistance",
            "read_file": "Read and display file contents",
            "delete_file": "Delete files safely",
            "list_files": "List files and directories",
            "execute_command": "Execute shell commands safely",
            "chat_completion": "General AI chat and assistance"
        }
        return descriptions.get(tool_name, "Unknown tool")
    
    def analyze_code(self, code: str, filename: str = "") -> ToolResult:
        """Analyze code for issues and improvements"""
        try:
            console.print("[cyan]🔍 Analyzing code...[/cyan]")
            
            prompt = f"""
            Analyze this code for:
            1. Bugs and potential issues
            2. Code quality problems
            3. Performance issues
            4. Security vulnerabilities
            5. Best practice violations
            6. Suggestions for improvement
            
            Code to analyze:
            ```
            {code}
            ```
            
            Provide a detailed analysis with specific recommendations.
            """
            
            response = self.client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": get_system_prompt("general_assistant")},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            analysis = response.choices[0].message.content
            
            console.print(Panel(
                Markdown(analysis),
                title=f"🔍 Code Analysis{' - ' + filename if filename else ''}",
                border_style="bright_blue"
            ))
            
            return ToolResult(True, analysis, "Code analysis completed successfully")
            
        except Exception as e:
            error_msg = f"Error analyzing code: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def generate_code(self, description: str, language: str = "python", filename: str = "") -> ToolResult:
        """Generate new code based on requirements"""
        try:
            console.print(f"[cyan]⚡ Generating {language} code...[/cyan]")
            
            prompt = get_task_prompt("code_generation", language=language, description=description)
            
            response = self.client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": get_system_prompt("code_generator")},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            generated_code = response.choices[0].message.content
            
            # Extract code block if present
            if "```" in generated_code:
                code_blocks = generated_code.split("```")
                for i, block in enumerate(code_blocks):
                    if i % 2 == 1:  # Odd-indexed blocks are code
                        if block.strip().startswith(language) or block.strip().startswith(f"{language}\n"):
                            block = block.split('\n', 1)[1] if '\n' in block else ""
                        generated_code = block.strip()
                        break
            
            # Display generated code
            console.print(Panel(
                Syntax(generated_code, language, theme="github-dark", line_numbers=True),
                title=f"⚡ Generated {language.title()} Code",
                border_style="bright_green"
            ))
            
            return ToolResult(True, generated_code, f"Successfully generated {language} code")
            
        except Exception as e:
            error_msg = f"Error generating code: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def fix_code(self, code: str, error_info: str = "", filename: str = "") -> ToolResult:
        """Fix bugs and issues in code"""
        try:
            console.print("[cyan]🔧 Fixing code issues...[/cyan]")
            
            prompt = f"""
            Fix the issues in this code:
            
            Code:
            ```
            {code}
            ```
            
            {f"Error information: {error_info}" if error_info else ""}
            
            Provide the complete fixed code with explanations of what was changed.
            """
            
            response = self.client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": get_system_prompt("general_assistant")},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            fix_response = response.choices[0].message.content
            
            # Extract fixed code
            fixed_code = self._extract_code_block(fix_response)
            if not fixed_code:
                fixed_code = fix_response
            
            console.print(Panel(
                Markdown(fix_response),
                title=f"🔧 Code Fix{' - ' + filename if filename else ''}",
                border_style="bright_green"
            ))
            
            return ToolResult(True, {"fixed_code": fixed_code, "explanation": fix_response}, "Code fixed successfully")
            
        except Exception as e:
            error_msg = f"Error fixing code: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def refactor_code(self, code: str, filename: str = "") -> ToolResult:
        """Refactor code for better structure and readability"""
        try:
            console.print("[cyan]🔄 Refactoring code...[/cyan]")
            
            prompt = f"""
            Refactor this code to improve:
            1. Code structure and organization
            2. Readability and maintainability
            3. Performance where possible
            4. Following best practices
            
            Original code:
            ```
            {code}
            ```
            
            Provide the refactored code with explanations of improvements made.
            """
            
            response = self.client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": get_system_prompt("general_assistant")},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            refactor_response = response.choices[0].message.content
            refactored_code = self._extract_code_block(refactor_response)
            
            console.print(Panel(
                Markdown(refactor_response),
                title=f"🔄 Code Refactoring{' - ' + filename if filename else ''}",
                border_style="bright_cyan"
            ))
            
            return ToolResult(True, {"refactored_code": refactored_code, "explanation": refactor_response}, "Code refactored successfully")
            
        except Exception as e:
            error_msg = f"Error refactoring code: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def optimize_code(self, code: str, filename: str = "") -> ToolResult:
        """Optimize code for better performance"""
        try:
            console.print("[cyan]⚡ Optimizing code performance...[/cyan]")
            
            prompt = f"""
            Optimize this code for better performance:
            1. Identify performance bottlenecks
            2. Suggest algorithmic improvements
            3. Optimize data structures usage
            4. Reduce time and space complexity where possible
            
            Code to optimize:
            ```
            {code}
            ```
            
            Provide optimized code with performance improvement explanations.
            """
            
            response = self.client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": get_system_prompt("general_assistant")},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            optimization_response = response.choices[0].message.content
            optimized_code = self._extract_code_block(optimization_response)
            
            console.print(Panel(
                Markdown(optimization_response),
                title=f"⚡ Performance Optimization{' - ' + filename if filename else ''}",
                border_style="bright_yellow"
            ))
            
            return ToolResult(True, {"optimized_code": optimized_code, "explanation": optimization_response}, "Code optimized successfully")
            
        except Exception as e:
            error_msg = f"Error optimizing code: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def predict_bugs(self, code: str, filename: str = "") -> ToolResult:
        """Predict potential bugs and edge cases"""
        try:
            console.print("[cyan]🔮 Predicting potential bugs...[/cyan]")
            
            prompt = get_task_prompt("bug_prediction", code=code)
            
            response = self.client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": get_system_prompt("bug_predictor")},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=1500
            )
            
            prediction = response.choices[0].message.content
            
            console.print(Panel(
                Markdown(prediction),
                title=f"🔮 Bug Prediction{' - ' + filename if filename else ''}",
                border_style="bright_magenta"
            ))
            
            return ToolResult(True, prediction, "Bug prediction completed successfully")
            
        except Exception as e:
            error_msg = f"Error predicting bugs: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def explain_concept(self, topic: str) -> ToolResult:
        """Explain programming concepts and topics"""
        try:
            console.print(f"[cyan]📚 Explaining: {topic}...[/cyan]")
            
            prompt = get_task_prompt("concept_explanation", topic=topic)
            
            response = self.client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": get_system_prompt("concept_explainer")},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            explanation = response.choices[0].message.content
            
            console.print(Panel(
                Markdown(explanation),
                title=f"📚 Concept Explanation: {topic}",
                border_style="bright_blue"
            ))
            
            return ToolResult(True, explanation, f"Successfully explained: {topic}")
            
        except Exception as e:
            error_msg = f"Error explaining concept: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def web_search(self, query: str, include_news: bool = False) -> ToolResult:
        """Search the web for information"""
        try:
            if not is_web_search_available():
                error_msg = "Web search not available. Install duckduckgo-search: pip install -U duckduckgo-search"
                console.print(f"[red]{error_msg}[/red]")
                return ToolResult(False, error=error_msg)
            
            console.print(f"[cyan]🔍 Searching the web for: {query}[/cyan]")
            
            # Perform searches
            results = search_web(query, max_results=5)
            news_results = []
            
            if include_news or any(keyword in query.lower() for keyword in ['news', 'latest', 'recent', 'update', 'current']):
                news_results = search_news(query, max_results=3)
            
            all_results = results + news_results
            
            if not all_results:
                message = f"No search results found for: {query}"
                console.print(f"[yellow]{message}[/yellow]")
                return ToolResult(False, message=message)
            
            # Display results
            display_search_results(all_results, query)
            
            # Get AI analysis
            search_context = format_search_results(all_results, query)
            prompt = get_task_prompt("web_search", query=query)
            full_prompt = f"{prompt}\n\nSearch Results:\n{search_context}"
            
            response = self.client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": get_system_prompt("web_search_assistant")},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            ai_analysis = response.choices[0].message.content
            
            console.print(Panel(
                Markdown(ai_analysis),
                title="🤖 AI Analysis of Search Results",
                border_style="bright_green"
            ))
            
            return ToolResult(True, {"results": all_results, "analysis": ai_analysis}, "Web search completed successfully")
            
        except Exception as e:
            error_msg = f"Error performing web search: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def create_file(self, filename: str, content: str = "", description: str = "", language: str = "") -> ToolResult:
        """Create a new file with optional AI-generated content"""
        try:
            # Check if file already exists
            if os.path.exists(filename):
                if not Confirm.ask(f"File {filename} already exists. Overwrite?"):
                    return ToolResult(False, message="File creation cancelled by user")
            
            # Generate content if description provided but no content
            if description and not content:
                console.print(f"[cyan]⚡ Generating content for {filename}...[/cyan]")
                
                # Infer language from filename if not provided
                if not language and '.' in filename:
                    ext_to_lang = {
                        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
                        '.java': 'java', '.cpp': 'cpp', '.c': 'c', '.cs': 'csharp',
                        '.go': 'go', '.rs': 'rust', '.php': 'php', '.rb': 'ruby',
                        '.html': 'html', '.css': 'css', '.sql': 'sql',
                        '.md': 'markdown', '.txt': 'text'
                    }
                    ext = '.' + filename.split('.')[-1].lower()
                    language = ext_to_lang.get(ext, 'text')
                
                # Generate content
                gen_result = self.generate_code(description, language, filename)
                if gen_result.success:
                    content = gen_result.data
                else:
                    return gen_result
            
            # Create directory if it doesn't exist
            directory = os.path.dirname(filename)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                console.print(f"[green]Created directory: {directory}[/green]")
            
            # Write file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Display created file
            file_size = os.path.getsize(filename)
            console.print(Panel(
                f"[green]✅ File created successfully![/green]\n"
                f"📄 **Filename:** {filename}\n"
                f"📊 **Size:** {file_size} bytes\n"
                f"📝 **Lines:** {len(content.splitlines()) if content else 0}",
                title="📁 File Creation",
                border_style="bright_green"
            ))
            
            # Show file content if it's not too long
            if content and len(content) < 2000:
                ext = filename.split('.')[-1] if '.' in filename else 'text'
                console.print(Panel(
                    Syntax(content, ext, theme="github-dark", line_numbers=True),
                    title=f"📄 {filename}",
                    border_style="blue"
                ))
            
            return ToolResult(True, {"filename": filename, "content": content, "size": file_size}, f"File {filename} created successfully")
            
        except Exception as e:
            error_msg = f"Error creating file {filename}: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def edit_file(self, filename: str, changes: str = "", line_number: int = None, search_replace: Dict[str, str] = None) -> ToolResult:
        """Edit an existing file with AI assistance"""
        try:
            if not os.path.exists(filename):
                return ToolResult(False, error=f"File {filename} does not exist")
            
            # Read current content
            with open(filename, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Create backup
            backup_filename = f"{filename}.backup"
            with open(backup_filename, 'w', encoding='utf-8') as f:
                f.write(original_content)
            console.print(f"[dim]Created backup: {backup_filename}[/dim]")
            
            new_content = original_content
            
            # Handle different edit modes
            if search_replace:
                # Search and replace mode
                for search_text, replace_text in search_replace.items():
                    if search_text in new_content:
                        new_content = new_content.replace(search_text, replace_text)
                        console.print(f"[green]Replaced: {search_text[:50]}...[/green]")
                    else:
                        console.print(f"[yellow]Text not found: {search_text[:50]}...[/yellow]")
            
            elif line_number is not None and changes:
                # Line-specific edit mode
                lines = new_content.splitlines()
                if 1 <= line_number <= len(lines):
                    lines[line_number - 1] = changes
                    new_content = '\n'.join(lines)
                    console.print(f"[green]Modified line {line_number}[/green]")
                else:
                    return ToolResult(False, error=f"Line number {line_number} is out of range")
            
            elif changes:
                # AI-assisted edit mode
                console.print(f"[cyan]🤖 AI editing {filename}...[/cyan]")
                
                prompt = get_task_prompt("file_modification", 
                                       description=changes, 
                                       current_content=original_content)
                
                response = self.client.chat.completions.create(
                    model="Meta-Llama-3.1-8B-Instruct",
                    messages=[
                        {"role": "system", "content": get_system_prompt("general_assistant")},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.2,
                    max_tokens=3000
                )
                
                ai_response = response.choices[0].message.content
                new_content = self._extract_code_block(ai_response) or ai_response
                
                console.print(Panel(
                    Markdown(ai_response),
                    title=f"🤖 AI File Edit - {filename}",
                    border_style="bright_cyan"
                ))
            
            # Show diff if content changed
            if new_content != original_content:
                show_diff(original_content, new_content, filename)
                
                # Confirm changes
                if not Confirm.ask("Apply these changes?"):
                    os.remove(backup_filename)
                    return ToolResult(False, message="Changes cancelled by user")
                
                # Write new content
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                console.print(f"[green]✅ File {filename} updated successfully![/green]")
                return ToolResult(True, {"filename": filename, "original": original_content, "new": new_content}, f"File {filename} edited successfully")
            else:
                console.print("[yellow]No changes made to the file[/yellow]")
                os.remove(backup_filename)
                return ToolResult(True, message="No changes were necessary")
                
        except Exception as e:
            error_msg = f"Error editing file {filename}: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def read_file(self, filename: str, start_line: int = None, end_line: int = None) -> ToolResult:
        """Read and display file contents"""
        try:
            if not os.path.exists(filename):
                return ToolResult(False, error=f"File {filename} does not exist")
            
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Handle line range
            if start_line is not None or end_line is not None:
                lines = content.splitlines()
                start_idx = (start_line - 1) if start_line else 0
                end_idx = end_line if end_line else len(lines)
                content = '\n'.join(lines[start_idx:end_idx])
            
            # Determine file extension for syntax highlighting
            ext = filename.split('.')[-1] if '.' in filename else 'text'
            
            # Display file content
            console.print(Panel(
                Syntax(content, ext, theme="github-dark", line_numbers=True),
                title=f"📄 {filename}",
                border_style="royal_blue1"
            ))
            
            file_info = {
                "filename": filename,
                "content": content,
                "size": len(content),
                "lines": len(content.splitlines())
            }
            
            return ToolResult(True, file_info, f"Successfully read {filename}")
            
        except Exception as e:
            error_msg = f"Error reading file {filename}: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def delete_file(self, filename: str, confirm: bool = True) -> ToolResult:
        """Delete a file safely"""
        try:
            if not os.path.exists(filename):
                return ToolResult(False, error=f"File {filename} does not exist")
            
            if confirm and not Confirm.ask(f"Are you sure you want to delete {filename}?"):
                return ToolResult(False, message="File deletion cancelled by user")
            
            # Create backup before deletion
            backup_filename = f"{filename}.deleted_backup"
            shutil.copy2(filename, backup_filename)
            
            # Delete the file
            os.remove(filename)
            
            console.print(Panel(
                f"[green]✅ File deleted successfully![/green]\n"
                f"📄 **Deleted:** {filename}\n"
                f"💾 **Backup:** {backup_filename}",
                title="🗑️ File Deletion",
                border_style="bright_red"
            ))
            
            return ToolResult(True, {"deleted_file": filename, "backup": backup_filename}, f"File {filename} deleted successfully")
            
        except Exception as e:
            error_msg = f"Error deleting file {filename}: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def list_files(self, directory: str = ".", pattern: str = "*", show_hidden: bool = False) -> ToolResult:
        """List files and directories"""
        try:
            import glob
            
            if not os.path.exists(directory):
                return ToolResult(False, error=f"Directory {directory} does not exist")
            
            # Get files matching pattern
            search_pattern = os.path.join(directory, pattern)
            all_items = glob.glob(search_pattern)
            
            # Filter hidden files if requested
            if not show_hidden:
                all_items = [item for item in all_items if not os.path.basename(item).startswith('.')]
            
            # Separate files and directories
            files = []
            directories = []
            
            for item in sorted(all_items):
                rel_path = os.path.relpath(item, directory)
                if os.path.isdir(item):
                    directories.append({
                        "name": rel_path,
                        "type": "directory",
                        "path": item
                    })
                else:
                    size = os.path.getsize(item)
                    files.append({
                        "name": rel_path,
                        "type": "file",
                        "path": item,
                        "size": size
                    })
            
            # Create display table
            table = Table(title=f"📁 Directory: {os.path.abspath(directory)}")
            table.add_column("Type", style="dim")
            table.add_column("Name", style="bold")
            table.add_column("Size", justify="right")
            
            for dir_item in directories:
                table.add_row("📁", f"[bold blue]{dir_item['name']}/[/bold blue]", "")
            
            for file_item in files:
                size_str = self._format_file_size(file_item['size'])
                table.add_row("📄", f"[green]{file_item['name']}[/green]", size_str)
            
            console.print(table)
            
            result_data = {
                "directory": directory,
                "files": files,
                "directories": directories,
                "total_files": len(files),
                "total_directories": len(directories)
            }
            
            return ToolResult(True, result_data, f"Listed {len(files)} files and {len(directories)} directories")
            
        except Exception as e:
            error_msg = f"Error listing files in {directory}: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def execute_command(self, command: str, working_dir: str = None, timeout: int = 30) -> ToolResult:
        """Execute shell commands safely"""
        try:
            # Security check for dangerous commands
            dangerous_commands = ['rm -rf', 'del /f', 'format', 'fdisk', 'mkfs', 'dd if=']
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                return ToolResult(False, error=f"Dangerous command blocked: {command}")
            
            console.print(f"[cyan]⚡ Executing: {command}[/cyan]")
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir
            )
            
            # Display results
            if result.stdout:
                console.print(Panel(
                    result.stdout,
                    title="📤 Command Output",
                    border_style="bright_green"
                ))
            
            if result.stderr:
                console.print(Panel(
                    result.stderr,
                    title="⚠️ Command Errors",
                    border_style="bright_red"
                ))
            
            success = result.returncode == 0
            
            command_result = {
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "working_dir": working_dir or os.getcwd()
            }
            
            status_msg = f"Command {'succeeded' if success else 'failed'} with return code {result.returncode}"
            
            return ToolResult(success, command_result, status_msg)
            
        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out after {timeout} seconds: {command}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
        except Exception as e:
            error_msg = f"Error executing command '{command}': {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def chat_completion(self, message: str, context: str = "") -> ToolResult:
        """General AI chat and assistance"""
        try:
            console.print("[cyan]🤖 Processing your request...[/cyan]")
            
            full_prompt = f"{context}\n\n{message}" if context else message
            
            response = self.client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[
                    {"role": "system", "content": get_system_prompt("chat_assistant")},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            ai_response = response.choices[0].message.content
            
            console.print(Panel(
                Markdown(ai_response),
                title="🤖 NOVA-CLI-AGENT",
                border_style="bright_green"
            ))
            
            return ToolResult(True, ai_response, "Chat completion successful")
            
        except Exception as e:
            error_msg = f"Error in chat completion: {str(e)}"
            console.print(f"[red]{error_msg}[/red]")
            return ToolResult(False, error=error_msg)
    
    def _extract_code_block(self, text: str) -> str:
        """Extract code block from markdown response"""
        if "```" in text:
            blocks = text.split("```")
            for i, block in enumerate(blocks):
                if i % 2 == 1:  # Odd-indexed blocks are code
                    # Remove language identifier if present
                    lines = block.split('\n')
                    if lines and lines[0].strip() in ['python', 'javascript', 'java', 'cpp', 'c', 'go', 'rust']:
                        return '\n'.join(lines[1:]).strip()
                    return block.strip()
        return ""
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f} {size_names[i]}"

# Global toolkit instance
toolkit = None

def get_toolkit(client: openai.OpenAI) -> AIToolkit:
    """Get or create the global toolkit instance"""
    global toolkit
    if toolkit is None:
        toolkit = AIToolkit(client)
    return toolkit

def list_available_tools() -> List[str]:
    """Get list of all available tools"""
    return [
        "analyze_code", "generate_code", "fix_code", "refactor_code", "optimize_code",
        "predict_bugs", "explain_concept", "web_search", "create_file", "edit_file",
        "read_file", "delete_file", "list_files", "execute_command", "chat_completion"
    ] 