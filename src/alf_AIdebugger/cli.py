#!/usr/bin/env python3
import os
import sys
import cmd
import openai
import traceback
from typing import Optional, Dict, Any
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from rich.prompt import Confirm
from rich.rule import Rule

from .analyzer import CodeAnalyzer
from .utils import (
    capture_execution,
    show_diff,
    check_python_version,
    get_code_complexity_metrics,
    display_complexity_report,
    check_dependencies,
)

console = Console()

class AICodingAssistantCLI(cmd.Cmd):
    intro = """
    🚀 AI Coding Assistant (powered by SambaNova) 🚀
    Your AI pair programmer for coding, debugging, and learning.
    
    Type help or ? to list commands.
    Use 'analyze <filename>' to analyze a file.
    Use 'generate' to create new code.
    Use 'explain <topic>' to learn about programming concepts.
    """
    prompt = '(nova-cli) '

    def __init__(self):
        super().__init__()
        self.current_file: Optional[str] = None
        self.file_content: Optional[str] = None
        self.analyzer: Optional[CodeAnalyzer] = None
        self.history: Dict[str, Any] = {
            "analyzed_files": [],
            "fixes_applied": 0,
            "successful_runs": 0,
            "generated_files": [],
        }
        self.setup_client()
        self._display_initial_directory_listing()
        
    def _display_initial_directory_listing(self):
        """Display the contents of the current directory at startup."""
        try:
            cwd = os.getcwd()
            console.print(Rule(f"[bold sky_blue1]Current Directory: {cwd}[/bold sky_blue1]"))
            
            items = os.listdir(".")
            if not items:
                console.print(Panel("[dim]Directory is empty.[/dim]", border_style="grey70"))
                return

            table = Table(box=None, show_header=False, padding=(0, 1))
            table.add_column("Type", style="dim")
            table.add_column("Name")

            dirs = sorted([item for item in items if os.path.isdir(item)])
            files = sorted([item for item in items if os.path.isfile(item)])

            for item_name in dirs:
                if not item_name.startswith('.'): # Basic filter for hidden files/dirs
                    table.add_row("📁", f"[bold blue]{item_name}/[/bold blue]")
            
            for item_name in files:
                if not item_name.startswith('.'): # Basic filter for hidden files/dirs
                    table.add_row("📄", f"[green]{item_name}[/green]")
            
            console.print(Panel(table, border_style="sky_blue1", expand=False))
            console.print(" ") # Add a blank line for spacing before the prompt

        except Exception as e:
            console.print(f"[red]Could not display directory listing: {e}[/red]")
            console.print(" ") # Add a blank line for spacing

    def setup_client(self):
        """Set up the OpenAI client with SambaNova configuration"""
        api_key = os.environ.get("SAMBANOVA_API_KEY")
        if not api_key:
            console.print("[yellow]Warning: SAMBANOVA_API_KEY not set. Please set it to use the debugger.[/yellow]")
            sys.exit(1)
        
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.sambanova.ai/v1"
        )
        
        self.analyzer = CodeAnalyzer(api_key)

    def get_completion(self, prompt: str) -> str:
        """Get completion from SambaNova API"""
        try:
            response = self.client.chat.completions.create(
                model='Meta-Llama-3.1-8B-Instruct',
                messages=[
                    {"role": "system", "content": """You are a helpful and friendly programming teacher. 
                    When analyzing code, explain issues in simple terms as if teaching a beginner.
                    Structure your analysis clearly and always provide examples of both the problem and solution.
                    Use friendly, encouraging language and explain why each fix helps."""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                top_p=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            console.print(f"[red]Error calling SambaNova API: {str(e)}[/red]")
            return ""

    def do_analyze(self, arg):
        """Analyze errors in a file: analyze <filename>"""
        if not arg:
            console.print("[red]Please specify a filename to analyze[/red]")
            return

        try:
            with open(arg, 'r') as f:
                self.file_content = f.read()
            self.current_file = arg
            
            if self.current_file not in self.history["analyzed_files"]:
                self.history["analyzed_files"].append(self.current_file)
                
            console.print(Rule(f"[bold white on royal_blue1] Analyzing file: {arg} [/bold white on royal_blue1]"))
            self.print_file_content()
        except FileNotFoundError:
            console.print(f"[red]File not found: {arg}[/red]")
            return

        console.print(Rule("[bold bright_cyan]Static Analysis[/bold bright_cyan]"))
        with Progress(transient=True) as progress:
            task = progress.add_task("[cyan]Running static analysis...", total=100)
            progress.update(task, advance=70)
            static_issues = self.analyzer.static_analysis(self.file_content)
            progress.update(task, completed=100)
        
        self.show_static_analysis_results(static_issues)
        
        error_context = self.get_error_context()
        
        console.print(Rule("[bold bright_magenta]AI-Powered Analysis[/bold bright_magenta]"))
        ai_analysis_content = "Fetching AI analysis..."
        with Progress(transient=True) as progress:
            task = progress.add_task("[cyan]Getting AI analysis...", total=100)
            progress.update(task, advance=70)
            analysis = self.analyzer.analyze_code(self.file_content, error_context)
            ai_analysis_content = analysis if analysis else "[yellow]No AI analysis provided.[/yellow]"
            progress.update(task, completed=100)
            
        console.print(Panel(Markdown(ai_analysis_content), title="💡 AI Insights", border_style="bright_blue", expand=False))
        
        console.print(Rule("[bold yellow3]Code Complexity Metrics[/bold yellow3]"))
        metrics = get_code_complexity_metrics(self.file_content)
        display_complexity_report(metrics)
        
        self.show_available_actions()

    def show_static_analysis_results(self, issues):
        """Display static analysis results in a structured way"""
        has_issues = any(issues.values())
        
        if not has_issues:
            console.print(Panel("[green]✔️ No static issues found.[/green]", border_style="green", expand=False))
            return
            
        output_table = Table(show_header=False, box=None, padding=(0,1))
        output_table.add_column(style="dim")
        output_table.add_column()

        if issues["syntax_errors"]:
            output_table.add_row("[bright_red]❌ Syntax Errors:", "")
            for error in issues["syntax_errors"]:
                output_table.add_row("", f"  Line {error['line']}: {error['message']}")
        
        if issues["undefined_names"]:
            output_table.add_row("[yellow]⚠️ Undefined Names:", "")
            for item in issues["undefined_names"]:
                output_table.add_row("", f"  {item['name']}: {item['message']}")
        
        if issues["unused_variables"]:
            output_table.add_row("[cyan]ℹ️ Unused Variables:", "")
            for item in issues["unused_variables"]:
                output_table.add_row("", f"  {item['name']}: {item['message']}")
        
        if issues["complexity_issues"]:
            output_table.add_row("[magenta]📈 Complexity Issues:", "")
            for item in issues["complexity_issues"]:
                output_table.add_row("", f"  {item['name']}: {item['message']}")
        
        console.print(Panel(output_table, title="Static Analysis Summary", border_style="royal_blue1", expand=False))

    def show_available_actions(self):
        """Show available actions after analysis"""
        console.print("\n[green]Available actions:[/green]")
        table = Table(show_header=False, box=None)
        table.add_column(style="cyan")
        table.add_column(style="yellow")
        
        table.add_row("analyze <file>", "Analyze a code file for issues")
        table.add_row("fix", "Generate and apply a fix for the current error")
        table.add_row("run", "Run the current file")
        table.add_row("chat <question>", "Ask a question about the code")
        table.add_row("predict_bugs", "Identify potential bugs before they occur")
        table.add_row("refactor", "Get refactoring suggestions")
        table.add_row("security", "Perform a security audit")
        table.add_row("optimize", "Get performance optimization suggestions")
        table.add_row("generate <lang> <file>", "Generate new code from a description")
        table.add_row("explain <topic>", "Explain a programming concept")
        table.add_row("show", "Show current file content")
        table.add_row("history", "Show your coding history")
        
        console.print(table)

    def do_show(self, arg):
        """Show current file content"""
        self.print_file_content()

    def get_chat_completion(self, question: str, code_context: str) -> str:
        """Get chat completion for specific questions about the code"""
        try:
            response = self.client.chat.completions.create(
                model='Meta-Llama-3.1-8B-Instruct',
                messages=[
                    {"role": "system", "content": """You are a helpful programming teacher.
                    Answer questions about code in simple, clear terms.
                    Always provide examples when explaining concepts.
                    If relevant, suggest improvements or alternative approaches."""},
                    {"role": "user", "content": f"""
                    CODE CONTEXT:
                    {code_context}
                    
                    QUESTION:
                    {question}
                    
                    Please provide:
                    1. A direct answer to the question
                    2. Examples if relevant
                    3. Any related tips or best practices"""}
                ],
                temperature=0.1,
                top_p=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            console.print(f"[red]Error calling SambaNova API: {str(e)}[/red]")
            return ""

    def do_chat(self, arg):
        """Chat about the current file: chat <your question>
        Example: chat Why might this code crash with large numbers?"""
        if not self.current_file:
            console.print("[red]No file is currently being analyzed. Use 'analyze <filename>' first.[/red]")
            return
        
        if not arg:
            console.print("[yellow]Please ask a question about the code. For example:[/yellow]")
            console.print("chat Why might this code crash?")
            console.print("chat How can I make this function safer?")
            console.print("chat What's wrong with line 10?")
            return
        
        try:
            console.print(f"\n[cyan]Question: {arg}[/cyan]")
            
            with Progress() as progress:
                task = progress.add_task("[cyan]Getting answer...", total=100)
                progress.update(task, advance=50)
                
                response = self.get_chat_completion(arg, self.file_content)
                progress.update(task, completed=100)
                
            console.print(Markdown(response))
            
            # Ask if they want to ask another question
            console.print("\n[green]Ask another question or use other commands:[/green]")
            console.print("- chat <your question>")
            console.print("- fix")
            console.print("- run")
            
        except Exception as e:
            console.print(f"[red]Error processing chat request: {str(e)}[/red]")

    def do_fix(self, arg):
        """Generate and apply a fix for the current error"""
        if not self.current_file:
            console.print("[red]No file is currently being analyzed. Use 'analyze <filename>' first.[/red]")
            return

        error_context = self.get_error_context()
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Generating fix...", total=100)
            progress.update(task, advance=33)
            
            if not error_context:
                console.print("[yellow]No runtime error detected. Looking for other improvements...[/yellow]")
                fixed_code, explanation = self.analyzer.fix_error(self.file_content, "No specific error. Please improve the code quality, fix potential bugs, and follow best practices.")
            else:
                console.print("\n[red]Error detected:[/red]")
                console.print(Markdown(f"```\n{error_context}\n```"))
                fixed_code, explanation = self.analyzer.fix_error(self.file_content, error_context)
                
            progress.update(task, completed=100)
        
        if not fixed_code:
            console.print("[red]Could not generate a fix[/red]")
            return
        
        # Show the diff between original and fixed code
        show_diff(self.file_content, fixed_code, self.current_file)
        
        # Show explanation
        console.print("\n[cyan]Explanation of the fix:[/cyan]")
        console.print(Markdown(explanation))
        
        if Confirm.ask("Apply this fix?"):
            # Backup the original file
            backup_file = f"{self.current_file}.bak"
            with open(backup_file, 'w') as f:
                f.write(self.file_content)
                
            # Apply the fix
            with open(self.current_file, 'w') as f:
                f.write(fixed_code)
                
            console.print(f"[green]Fix applied successfully! Original code backed up to {backup_file}[/green]")
            self.file_content = fixed_code
            
            self.history["fixes_applied"] += 1
            
            # Offer to run the fixed code
            if Confirm.ask("Run the fixed code?"):
                self.do_run("")

    def do_run(self, arg):
        """Run the current file"""
        if not self.current_file:
            console.print("[red]No file is currently being analyzed. Use 'analyze <filename>' first.[/red]")
            return

        console.print(f"\n[cyan]Running {self.current_file}...[/cyan]")
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Executing...", total=100)
            progress.update(task, advance=50)
            
            output, error = capture_execution(self.current_file)
            progress.update(task, completed=100)
        
        if error:
            console.print("[red]Error occurred:[/red]")
            console.print(Markdown(f"```\n{error}\n```"))
        else:
            console.print("[green]Program ran successfully![/green]")
            self.history["successful_runs"] += 1
            
            if output.strip():
                console.print("[green]Program output:[/green]")
                console.print(Markdown(f"```\n{output}\n```"))
            else:
                console.print("[yellow]No output produced[/yellow]")

    def do_refactor(self, arg):
        """Get refactoring suggestions for cleaner code"""
        if not self.current_file:
            console.print("[red]No file is currently being analyzed. Use 'analyze <filename>' first.[/red]")
            return
        
        console.print("\n[cyan]Analyzing code for refactoring opportunities...[/cyan]")
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Generating refactoring suggestions...", total=100)
            progress.update(task, advance=50)
            
            suggestions = self.analyzer.get_refactoring_suggestions(self.file_content)
            progress.update(task, completed=100)
        
        console.print("\n[green]Refactoring Suggestions:[/green]")
        console.print(Markdown(suggestions))
        
        # Ask if user wants to implement any of these refactorings
        if Confirm.ask("Would you like me to implement these refactorings for you?"):
            with Progress() as progress:
                task = progress.add_task("[cyan]Implementing refactorings...", total=100)
                progress.update(task, advance=50)
                
                refactored_code, explanation = self.analyzer.fix_error(
                    self.file_content, 
                    "Implement the refactoring suggestions to improve this code. Only make the most important improvements."
                )
                progress.update(task, completed=100)
            
            # Show diff and apply if confirmed
            show_diff(self.file_content, refactored_code, self.current_file)
            
            if Confirm.ask("Apply these refactorings?"):
                # Backup the original file
                backup_file = f"{self.current_file}.bak"
                with open(backup_file, 'w') as f:
                    f.write(self.file_content)
                    
                # Apply the refactorings
                with open(self.current_file, 'w') as f:
                    f.write(refactored_code)
                    
                console.print(f"[green]Refactoring applied! Original code backed up to {backup_file}[/green]")
                self.file_content = refactored_code

    def do_security(self, arg):
        """Perform a security audit on the current file"""
        if not self.current_file:
            console.print("[red]No file is currently being analyzed. Use 'analyze <filename>' first.[/red]")
            return
        
        console.print("\n[cyan]Performing security audit...[/cyan]")
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Analyzing security vulnerabilities...", total=100)
            progress.update(task, advance=50)
            
            audit_results = self.analyzer.security_audit(self.file_content)
            progress.update(task, completed=100)
        
        console.print("\n[red]Security Audit Results:[/red]")
        console.print(Markdown(audit_results))
        
        # Ask if user wants to implement security fixes
        if Confirm.ask("Would you like me to implement security fixes?"):
            with Progress() as progress:
                task = progress.add_task("[cyan]Applying security fixes...", total=100)
                progress.update(task, advance=50)
                
                secured_code, explanation = self.analyzer.fix_error(
                    self.file_content, 
                    "Fix the security vulnerabilities in this code without changing its functionality."
                )
                progress.update(task, completed=100)
            
            # Show diff and apply if confirmed
            show_diff(self.file_content, secured_code, self.current_file)
            
            if Confirm.ask("Apply these security fixes?"):
                # Backup the original file
                backup_file = f"{self.current_file}.bak"
                with open(backup_file, 'w') as f:
                    f.write(self.file_content)
                    
                # Apply the security fixes
                with open(self.current_file, 'w') as f:
                    f.write(secured_code)
                    
                console.print(f"[green]Security fixes applied! Original code backed up to {backup_file}[/green]")
                self.file_content = secured_code

    def do_optimize(self, arg):
        """Get performance optimization suggestions"""
        if not self.current_file:
            console.print("[red]No file is currently being analyzed. Use 'analyze <filename>' first.[/red]")
            return
        
        console.print("\n[cyan]Analyzing code for performance optimizations...[/cyan]")
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Finding optimization opportunities...", total=100)
            progress.update(task, advance=50)
            
            optimization_results = self.analyzer.optimize_performance(self.file_content)
            progress.update(task, completed=100)
        
        console.print("\n[green]Performance Optimization Suggestions:[/green]")
        console.print(Markdown(optimization_results))
        
        # Ask if user wants to implement optimizations
        if Confirm.ask("Would you like me to implement these optimizations?"):
            with Progress() as progress:
                task = progress.add_task("[cyan]Applying optimizations...", total=100)
                progress.update(task, advance=50)
                
                optimized_code, explanation = self.analyzer.fix_error(
                    self.file_content, 
                    "Optimize this code for better performance without changing its functionality."
                )
                progress.update(task, completed=100)
            
            # Show diff and apply if confirmed
            show_diff(self.file_content, optimized_code, self.current_file)
            
            if Confirm.ask("Apply these optimizations?"):
                # Backup the original file
                backup_file = f"{self.current_file}.bak"
                with open(backup_file, 'w') as f:
                    f.write(self.file_content)
                    
                # Apply the optimizations
                with open(self.current_file, 'w') as f:
                    f.write(optimized_code)
                    
                console.print(f"[green]Optimizations applied! Original code backed up to {backup_file}[/green]")
                self.file_content = optimized_code

    def do_predict_bugs(self, arg):
        """Predict potential bugs or issues that might occur in the current file
        This analyzes the code to find edge cases, race conditions, and other potential problems
        that might not be immediately apparent.
        """
        if not self.current_file:
            console.print("[red]No file is currently being analyzed. Use 'analyze <filename>' first.[/red]")
            return
        
        console.print("\n[cyan]Predicting potential bugs and edge cases...[/cyan]")
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Analyzing potential failure points...", total=100)
            progress.update(task, advance=50)
            
            predictions = self._predict_bugs(self.file_content)
            progress.update(task, completed=100)
        
        console.print("\n[yellow]Potential Bug Predictions:[/yellow]")
        console.print(Markdown(predictions))
        
        # Ask if the user wants to fix any of the predicted issues
        if Confirm.ask("Would you like me to fix any of these potential issues?"):
            with Progress() as progress:
                task = progress.add_task("[cyan]Generating preemptive fixes...", total=100)
                progress.update(task, advance=50)
                
                fixed_code, explanation = self.analyzer.fix_error(
                    self.file_content, 
                    "Fix the potential bugs and edge cases identified in the bug prediction analysis."
                )
                progress.update(task, completed=100)
            
            # Show diff and apply if confirmed
            show_diff(self.file_content, fixed_code, self.current_file)
            
            if Confirm.ask("Apply these preemptive fixes?"):
                # Backup the original file
                backup_file = f"{self.current_file}.bak"
                with open(backup_file, 'w') as f:
                    f.write(self.file_content)
                    
                # Apply the fixes
                with open(self.current_file, 'w') as f:
                    f.write(fixed_code)
                    
                console.print(f"[green]Preemptive fixes applied! Original code backed up to {backup_file}[/green]")
                self.file_content = fixed_code
                self.history["fixes_applied"] += 1
    
    def _predict_bugs(self, code: str) -> str:
        """Predict potential bugs and edge cases in the code"""
        try:
            prompt = f"""
            Analyze this code for potential bugs, edge cases, and failure points that might not be immediately apparent:
            
            ```
            {code}
            ```
            
            Focus on:
            1. Edge cases that aren't handled
            2. Input validation issues
            3. Potential race conditions
            4. Memory leaks or resource management issues
            5. Error handling gaps
            6. Boundary conditions
            7. Potential security vulnerabilities
            8. Scalability issues with large inputs
            9. Concurrency problems
            10. Assumptions that could be violated
            
            For each potential issue:
            - Describe the specific scenario where it could fail
            - Explain why it's problematic
            - Suggest how to prevent or fix it
            - Rate the severity (Critical, High, Medium, Low)
            
            Only include realistic issues that could actually occur, not theoretical ones.
            """
            
            response = self.client.chat.completions.create(
                model='Meta-Llama-3.1-8B-Instruct',
                messages=[
                    {"role": "system", "content": """You are an expert software engineer with a specialty in debugging and finding edge cases.
                    You have a knack for identifying potential bugs before they occur in production.
                    You think deeply about all possible ways code could fail in real-world scenarios."""},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                top_p=0.1
            )
            
            return response.choices[0].message.content
                
        except Exception as e:
            console.print(f"[red]Error predicting bugs: {str(e)}[/red]")
            return "Failed to predict potential bugs"

    def do_history(self, arg):
        """Show debugging history"""
        console.print("\n[cyan]Debugging History:[/cyan]")
        
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Files Analyzed", str(len(self.history["analyzed_files"])))
        table.add_row("Fixes Applied", str(self.history["fixes_applied"]))
        table.add_row("Successful Runs", str(self.history["successful_runs"]))
        table.add_row("Generated Files", str(len(self.history.get("generated_files", []))))
        
        console.print(table)
        
        if self.history["analyzed_files"]:
            console.print("\n[cyan]Analyzed Files:[/cyan]")
            for i, file in enumerate(self.history["analyzed_files"]):
                console.print(f"{i+1}. {file}")
        
        if self.history.get("generated_files"):
            console.print("\n[cyan]Generated Files:[/cyan]")
            for i, file in enumerate(self.history.get("generated_files", [])):
                console.print(f"{i+1}. {file}")

    def do_generate(self, arg):
        """Generate new code from a description: generate [language] [filename]
        After entering this command, you'll be prompted to describe what you want to create.
        
        Examples:
        - generate python sort_algorithm.py
        - generate javascript simple_calculator.js
        - generate html landing_page.html
        """
        if not arg:
            console.print("[yellow]Please specify a language and filename:[/yellow]")
            console.print("generate [language] [filename]")
            console.print("\nExamples:")
            console.print("generate python fibonacci.py")
            console.print("generate javascript todo_app.js")
            console.print("generate html profile_page.html")
            return
            
        parts = arg.split()
        if len(parts) < 2:
            console.print("[red]Please specify both language and filename[/red]")
            return
            
        language = parts[0].lower()
        filename = parts[1]
        
        # Check if file already exists and confirm overwrite
        if os.path.exists(filename):
            if not Confirm.ask(f"File {filename} already exists. Overwrite?"):
                return
        
        # Get description from user
        console.print("[cyan]Describe what you want to generate (press Enter twice to finish):[/cyan]")
        lines = []
        while True:
            line = input()
            if not line and lines and not lines[-1]:
                break
            lines.append(line)
        
        description = "\n".join(lines).strip()
        if not description:
            console.print("[red]Description cannot be empty[/red]")
            return
            
        with Progress() as progress:
            task = progress.add_task("[cyan]Generating code...", total=100)
            progress.update(task, advance=50)
            
            code = self._generate_code(language, description)
            progress.update(task, completed=100)
            
        if not code:
            console.print("[red]Failed to generate code[/red]")
            return
            
        # Preview the generated code
        console.print("\n[green]Generated Code:[/green]")
        console.print(Syntax(code, language))
        
        # Ask to save
        if Confirm.ask("Save this code to file?"):
            with open(filename, 'w') as f:
                f.write(code)
                
            console.print(f"[green]Code saved to {filename}[/green]")
            
            if "generated_files" not in self.history:
                self.history["generated_files"] = []
                
            self.history["generated_files"].append(filename)
            
            # Set as current file for further operations
            self.current_file = filename
            self.file_content = code
    
    def _generate_code(self, language: str, description: str) -> str:
        """Generate code in the specified language based on the description"""
        try:
            prompt = f"""
            Generate {language} code based on this description:
            
            {description}
            
            Write clean, efficient, and well-commented code that follows best practices.
            Include error handling and edge cases where appropriate.
            Provide a complete implementation that can be used right away.
            
            Only output the code itself, no explanations before or after.
            """
            
            response = self.client.chat.completions.create(
                model='Meta-Llama-3.1-8B-Instruct',
                messages=[
                    {"role": "system", "content": "You are an expert software developer skilled in multiple programming languages. Your task is to generate high-quality, working code based on user requirements."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                top_p=0.1
            )
            
            generated_code = response.choices[0].message.content
            
            # Extract code block if present
            if "```" in generated_code:
                code_blocks = generated_code.split("```")
                for i, block in enumerate(code_blocks):
                    if i % 2 == 1:  # Odd-indexed blocks are code
                        # Remove language identifier if present
                        if block.strip().startswith(language) or block.strip().startswith(f"{language}\n"):
                            block = block.split('\n', 1)[1] if '\n' in block else ""
                        return block.strip()
                        
                # If no code blocks found, return the whole response
                return generated_code
            else:
                return generated_code
                
        except Exception as e:
            console.print(f"[red]Error generating code: {str(e)}[/red]")
            return ""

    def do_quit(self, arg):
        """Exit the debugger"""
        console.print("\n[yellow]Goodbye! 👋[/yellow]")
        return True

    def do_explain(self, arg):
        """Explain a programming concept or language feature: explain <topic>
        
        Examples:
        - explain recursion
        - explain python decorators
        - explain javascript promises
        - explain big o notation
        """
        if not arg:
            console.print("[yellow]Please specify a topic to explain:[/yellow]")
            console.print("explain <topic>")
            console.print("\nExamples:")
            console.print("explain recursion")
            console.print("explain python generators")
            console.print("explain react hooks")
            return
            
        topic = arg.strip()
        
        with Progress() as progress:
            task = progress.add_task(f"[cyan]Researching {topic}...", total=100)
            progress.update(task, advance=50)
            
            explanation = self._get_explanation(topic)
            progress.update(task, completed=100)
            
        if explanation:
            console.print(f"\n[green]Explanation of {topic}:[/green]")
            console.print(Markdown(explanation))
            
            # Offer to save the explanation to a file
            if Confirm.ask("Save this explanation to a file?"):
                filename = f"{topic.replace(' ', '_')}_explanation.md"
                
                # Check if file exists
                if os.path.exists(filename):
                    if not Confirm.ask(f"File {filename} already exists. Overwrite?"):
                        filename = input("Enter a different filename: ")
                        
                with open(filename, 'w') as f:
                    f.write(explanation)
                    
                console.print(f"[green]Explanation saved to {filename}[/green]")
        else:
            console.print("[red]Failed to get explanation[/red]")
    
    def _get_explanation(self, topic: str) -> str:
        """Get an explanation of a programming concept"""
        try:
            prompt = f"""
            Explain the following programming concept in detail: 
            
            {topic}
            
            Please structure your explanation with:
            
            1. A clear, concise definition
            2. How it works (with simple examples)
            3. When and why to use it
            4. Common pitfalls or mistakes
            5. Best practices
            6. Related concepts worth exploring
            
            Use markdown formatting for better readability.
            """
            
            response = self.client.chat.completions.create(
                model='Meta-Llama-3.1-8B-Instruct',
                messages=[
                    {"role": "system", "content": "You are an expert programming educator who explains technical concepts clearly with helpful examples. Your explanations are comprehensive but accessible to beginners."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                top_p=0.1
            )
            
            return response.choices[0].message.content
                
        except Exception as e:
            console.print(f"[red]Error getting explanation: {str(e)}[/red]")
            return ""

    def print_file_content(self):
        """Print the current file content with syntax highlighting"""
        if not self.current_file or not self.file_content:
            return
        
        console.print(Panel(Syntax(self.file_content, "python", theme="github-dark", line_numbers=True, background_color="#2b2b2b"),
                          title=f"📄 {self.current_file}", 
                          border_style="royal_blue1",
                          expand=False))

    def get_error_context(self) -> str:
        """Run the file and capture any error message"""
        if not self.current_file:
            return ""
        
        _, error_info = capture_execution(self.current_file)
        return error_info or ""

    def extract_code_block(self, response: str) -> str:
        """Extract code block from markdown response"""
        if "```python" in response:
            blocks = response.split("```python")
        else:
            blocks = response.split("```")
        
        if len(blocks) > 1:
            return blocks[1].split("```")[0].strip()
        return ""

def main():
    """Entry point for the AI coding assistant CLI."""
    # Check Python version
    if not check_python_version():
        sys.exit(1)
        
    # Check for missing dependencies
    missing_deps = check_dependencies()
    if missing_deps:
        console.print("[red]Error: Missing required dependencies:[/red]")
        for dep in missing_deps:
            console.print(f"  - {dep}")
        console.print("[yellow]Please install them using: pip install " + " ".join(missing_deps) + "[/yellow]")
        sys.exit(1)
    
    # Check for API key
    if "SAMBANOVA_API_KEY" not in os.environ:
        console.print("[yellow]SAMBANOVA_API_KEY environment variable not set.[/yellow]")
        api_key_input = console.input("Please enter your SambaNova API Key: ")
        if not api_key_input.strip():
            console.print("[red]API Key cannot be empty. Exiting.[/red]")
            sys.exit(1)
        os.environ["SAMBANOVA_API_KEY"] = api_key_input.strip()
        console.print("[green]SambaNova API Key set for this session.[/green]")
        
    try:
        AICodingAssistantCLI().cmdloop()
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye! 👋[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        console.print(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()