#!/usr/bin/env python3
import os
import sys
import cmd
import openai
import traceback
import json
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.text import Text
from rich.align import Align

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # dotenv is optional

from .analyzer import CodeAnalyzer
from .utils import (
    capture_execution,
    show_diff,
    check_python_version,
    get_code_complexity_metrics,
    display_complexity_report,
    check_dependencies,
    get_api_key_interactive,
    delete_saved_api_key,
)
from .prompts import (
    get_system_prompt,
    get_task_prompt,
    get_fix_prompt,
    get_ui_message,
    get_progress_message,
)
from .web_search import (
    search_web,
    search_news,
    format_search_results,
    display_search_results,
    is_web_search_available,
)
from .tools import get_toolkit, list_available_tools, ToolResult

console = Console()

class AICodingAssistantCLI(cmd.Cmd):
    intro = """
    🤖 NOVA-CLI-AGENT - Natural Conversation Mode 🤖
    Your intelligent pair programmer that understands natural language.
    
    Just talk to me naturally! I understand what you want to do. Examples:
    
    💬 "Check my main.py file for errors"
    💬 "Create a sorting algorithm in Python"  
    💬 "What is recursion and how does it work?"
    💬 "Fix the bugs in my current code"
    💬 "Make my code run faster"
    💬 "Create a new file called utils.py"
    💬 "Edit my config file to add logging"
    💬 "Run the command 'pip install requests'"
    💬 "Search for the latest Python best practices"
    💬 "Hi, can you help me with my project?"
    
    🤖 AGENT MODE: Say "agent mode" for autonomous execution without confirmations!
    ✨ INTERACTIVE MODE: Default mode with confirmations for safety.
    🔍 WEB SEARCH: I can search the web for current information and documentation!
    🛠️ TOOLS SYSTEM: Advanced file operations, command execution, and AI-powered development tools!
    
    No commands needed - just tell me what you want to do!
    """
    prompt = ''  # We'll handle prompting ourselves

    def __init__(self):
        super().__init__()
        self.current_file: Optional[str] = None
        self.file_content: Optional[str] = None
        self.analyzer: Optional[CodeAnalyzer] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.agent_mode: bool = False  # New agent mode flag
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
        from .utils import get_api_key_interactive
        
        # Try to get API key from environment first, then from secure storage
        api_key = os.environ.get("SAMBANOVA_API_KEY")
        
        if not api_key:
            console.print(Panel(
                "[yellow]SAMBANOVA_API_KEY not found in environment variables.[/yellow]\n"
                "[blue]Please set it in your .env file or environment.[/blue]",
                title="⚠️  API Key Required",
                border_style="yellow"
            ))
            # Use interactive secure storage as fallback
            api_key = get_api_key_interactive()
        
        if not api_key or api_key.strip() == "your_sambanova_api_key_here":
            console.print(Panel(
                "[red]Invalid or placeholder API key detected![/red]\n"
                "[yellow]Please set a valid SAMBANOVA_API_KEY in your .env file.[/yellow]\n"
                "[blue]Get your API key from: https://cloud.sambanova.ai/[/blue]",
                title="❌ Invalid API Key",
                border_style="red"
            ))
            sys.exit(1)
        
        try:
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.sambanova.ai/v1"
            )
            
            # Test the API key with a simple request
            test_response = self.client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            self.analyzer = CodeAnalyzer(api_key)
            self.toolkit = get_toolkit(self.client)
            
            console.print(Panel(
                "[green]✅ API key validated successfully![/green]\n"
                "[blue]Connected to SambaNova AI[/blue]",
                title="🚀 Ready to Go",
                border_style="green"
            ))
            
        except Exception as e:
            error_msg = str(e)
            if "Unauthorized" in error_msg or "Invalid API key" in error_msg:
                console.print(Panel(
                    "[red]❌ Invalid SambaNova API key![/red]\n"
                    "[yellow]Please check your SAMBANOVA_API_KEY in the .env file.[/yellow]\n"
                    "[blue]Get a valid API key from: https://cloud.sambanova.ai/[/blue]\n\n"
                    "[dim]Current API key starts with: " + (api_key[:10] + "..." if len(api_key) > 10 else api_key) + "[/dim]",
                    title="🔑 API Key Error",
                    border_style="red"
                ))
            else:
                console.print(Panel(
                    f"[red]❌ Failed to connect to SambaNova API:[/red]\n"
                    f"[yellow]{error_msg}[/yellow]\n"
                    "[blue]Please check your internet connection and API key.[/blue]",
                    title="🌐 Connection Error",
                    border_style="red"
                ))
            sys.exit(1)

    def cmdloop(self, intro=None):
        """Override cmdloop to use our custom input handling"""
        if intro is not None:
            self.intro = intro
        if self.intro:
            console.print(Panel(self.intro, border_style="bright_blue", title="🚀 Welcome", title_align="center"))
        
        stop = None
        while not stop:
            try:
                # Create beautiful input box
                user_input = self._get_user_input()
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    break
                
                # Handle the input conversationally
                stop = self._handle_conversational_input(user_input)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Use 'quit' or 'exit' to leave. Press Ctrl+C again to force exit.[/yellow]")
                try:
                    input()  # Wait for another Ctrl+C
                except KeyboardInterrupt:
                    break
            except EOFError:
                break

    def _get_user_input(self) -> str:
        """Get user input with a beautiful blue-bordered box"""
        console.print()  # Add spacing
        
        # Create the input prompt box
        mode_indicator = "🤖 AGENT MODE" if self.agent_mode else "✨ Nova-cli Assistant"
        input_text = Text("💬 What would you like me to help you with?", style="bold bright_blue")
        input_panel = Panel(
            Align.center(input_text),
            border_style="bright_blue" if not self.agent_mode else "bright_magenta",
            padding=(1, 2),
            title=f"[bold bright_blue]{mode_indicator}[/bold bright_blue]",
            title_align="center"
        )
        console.print(input_panel)
        
        # Get the actual input
        user_input = Prompt.ask(
            "[bright_blue]>[/bright_blue]" if not self.agent_mode else "[bright_magenta]🤖>[/bright_magenta]",
            console=console
        )
        
        return user_input.strip()

    def _handle_conversational_input(self, user_input: str) -> bool:
        """Handle user input conversationally by determining intent and executing actions"""
        if not user_input:
            return False
        
        # Check for agent mode commands
        if user_input.lower() in ['agent mode', 'enable agent mode', 'turn on agent mode', 'autonomous mode']:
            self.agent_mode = True
            console.print(Panel(
                "[bold bright_magenta]🤖 AGENT MODE ACTIVATED[/bold bright_magenta]\n\n"
                "I will now work autonomously without asking for confirmations.\n"
                "I'll execute tasks and show you the results.\n\n"
                "Say 'exit agent mode' to return to interactive mode.",
                title="🤖 Agent Mode",
                border_style="bright_magenta"
            ))
            return False
            
        if user_input.lower() in ['exit agent mode', 'disable agent mode', 'turn off agent mode', 'interactive mode']:
            self.agent_mode = False
            console.print(Panel(
                "[bold bright_blue]✨ INTERACTIVE MODE ACTIVATED[/bold bright_blue]\n\n"
                "I'm back to interactive mode.\n"
                "I'll ask for confirmations when needed.",
                title="✨ Interactive Mode",
                border_style="bright_blue"
            ))
            return False
            
        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Get context about current state
        context = self._gather_context()
        
        # Determine intent and get response
        with Progress() as progress:
            task = progress.add_task("[cyan]🤔 Understanding your request...", total=100)
            progress.update(task, advance=30)
            
            intent_response = self._get_intent_and_response(user_input, context)
            progress.update(task, advance=70)
            
            # Execute the determined actions
            self._execute_intent(intent_response)
            progress.update(task, completed=100)
        
        return False  # Continue the loop

    def _gather_context(self) -> str:
        """Gather current context for the AI"""
        context_parts = []
        
        # Current directory
        cwd = os.getcwd()
        context_parts.append(f"Current directory: {cwd}")
        
        # List files in current directory
        try:
            files = [f for f in os.listdir(".") if not f.startswith('.')]
            context_parts.append(f"Available files: {', '.join(files[:10])}")  # Limit to first 10
        except:
            pass
        
        # Current file being worked on
        if self.current_file:
            context_parts.append(f"Currently working on: {self.current_file}")
        
        # Recent conversation context
        if len(self.conversation_history) > 0:
            recent_messages = self.conversation_history[-3:]  # Last 3 messages
            context_parts.append("Recent conversation:")
            for msg in recent_messages:
                context_parts.append(f"  {msg['role']}: {msg['content'][:100]}...")
        
        return "\n".join(context_parts)

    def _get_intent_and_response(self, user_input: str, context: str) -> Dict[str, Any]:
        """Determine user intent and get appropriate response"""
        try:
            response = self.client.chat.completions.create(
                model='Meta-Llama-3.1-8B-Instruct',
                messages=[
                    {"role": "system", "content": get_system_prompt("intent_parser")},
                    {"role": "user", "content": f"User input: {user_input}\n\nContext: {context}"}
                ],
                temperature=0.1,
                top_p=0.1
            )
            
            response_text = response.choices[0].message.content
            
            # Try to parse JSON response
            try:
                # Extract JSON from response if it's wrapped in markdown
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif "```" in response_text:
                    json_start = response_text.find("```") + 3
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback to chat if JSON parsing fails
                return {
                    "intent": "chat",
                    "parameters": {},
                    "response": response_text,
                    "needs_confirmation": False
                }
                
        except Exception as e:
            console.print(f"[red]Error getting AI response: {str(e)}[/red]")
            return {
                "intent": "chat",
                "parameters": {},
                "response": "I'm having trouble understanding that request. Could you please rephrase it?",
                "needs_confirmation": False
            }

    def _execute_intent(self, intent_data: Dict[str, Any]):
        """Execute the determined intent"""
        intent = intent_data.get("intent", "chat")
        parameters = intent_data.get("parameters", {})
        response = intent_data.get("response", "")
        needs_confirmation = intent_data.get("needs_confirmation", False)
        
        # Show the AI's response
        if response:
            console.print(Panel(Markdown(response), title="🤖 NOVA-CLI-AGENT", border_style="bright_green"))
        
        # Ask for confirmation if needed (skip in agent mode)
        if needs_confirmation and not self.agent_mode:
            if not Confirm.ask("Proceed with this action?"):
                console.print("[yellow]Action cancelled.[/yellow]")
                return
        elif self.agent_mode and needs_confirmation:
            console.print("[bright_magenta]🤖 Agent Mode: Proceeding automatically...[/bright_magenta]")
        
        # Execute the appropriate action
        try:
            if intent == "analyze":
                filename = parameters.get("filename", "")
                if filename:
                    # Use toolkit for analysis
                    try:
                        with open(filename, 'r') as f:
                            code = f.read()
                        result = self.toolkit.analyze_code(code, filename)
                        if not result.success:
                            console.print(f"[red]{result.error}[/red]")
                    except FileNotFoundError:
                        console.print(f"[red]File not found: {filename}[/red]")
                    except Exception as e:
                        console.print(f"[red]Error reading file: {str(e)}[/red]")
                else:
                    console.print("[red]Please specify a filename to analyze.[/red]")
                    
            elif intent == "generate":
                language = parameters.get("language", "python")
                filename = parameters.get("filename", "")
                description = parameters.get("description", "")
                if filename and description:
                    # Use toolkit for code generation and file creation
                    result = self.toolkit.create_file(filename, "", description, language)
                    if result.success:
                        self.current_file = filename
                        self.file_content = result.data.get("content", "")
                    else:
                        console.print(f"[red]{result.error}[/red]")
                else:
                    console.print("[red]Please provide both filename and description for code generation.[/red]")
                    
            elif intent == "explain":
                topic = parameters.get("topic", parameters.get("description", ""))
                if topic:
                    result = self.toolkit.explain_concept(topic)
                    if not result.success:
                        console.print(f"[red]{result.error}[/red]")
                else:
                    console.print("[red]Please specify a topic to explain.[/red]")
                    
            elif intent == "fix":
                self.do_fix("")
                
            elif intent == "run":
                self.do_run("")
                
            elif intent == "refactor":
                self.do_refactor("")
                
            elif intent == "security":
                self.do_security("")
                
            elif intent == "optimize":
                self.do_optimize("")
                
            elif intent == "predict_bugs":
                self.do_predict_bugs("")
                
            elif intent == "history":
                self.do_history("")
                
            elif intent == "show":
                self.do_show("")
                
            elif intent == "read_file":
                filename = parameters.get("filename", "")
                if filename:
                    result = self.toolkit.read_file(filename)
                    if result.success:
                        # Update current file
                        self.current_file = filename
                        self.file_content = result.data.get("content", "")
                    else:
                        console.print(f"[red]{result.error}[/red]")
                else:
                    console.print("[red]Please specify a filename to read.[/red]")
                    
            elif intent == "modify_file":
                filename = parameters.get("filename", "")
                code = parameters.get("code", "")
                description = parameters.get("description", "")
                if filename:
                    self._modify_file(filename, code, description)
                else:
                    console.print("[red]Please specify a filename to modify.[/red]")
                    
            elif intent == "list_files":
                result = self.toolkit.list_files()
                if not result.success:
                    console.print(f"[red]{result.error}[/red]")
                
            elif intent == "chat":
                # Already handled by showing the response
                pass
                
            elif intent == "delete_api_key":
                self.do_delete_api_key()
                
            elif intent == "web_search":
                query = parameters.get("description", parameters.get("topic", ""))
                if query:
                    result = self.toolkit.web_search(query)
                    if not result.success:
                        console.print(f"[red]{result.error}[/red]")
                else:
                    console.print("[red]Please specify what to search for.[/red]")
                    
            elif intent == "create_file":
                filename = parameters.get("filename", "")
                description = parameters.get("description", "")
                code = parameters.get("code", "")
                language = parameters.get("language", "")
                
                if filename:
                    result = self.toolkit.create_file(filename, code, description, language)
                    if result.success:
                        # Update current file
                        self.current_file = filename
                        self.file_content = result.data.get("content", "")
                    else:
                        console.print(f"[red]{result.error}[/red]")
                else:
                    console.print("[red]Please specify a filename.[/red]")
                    
            elif intent == "edit_file":
                filename = parameters.get("filename", self.current_file)
                changes = parameters.get("description", "")
                
                if filename:
                    if not self.agent_mode:
                        result = self.toolkit.edit_file(filename, changes)
                    else:
                        console.print("[bright_magenta]🤖 Agent Mode: Editing file automatically...[/bright_magenta]")
                        result = self.toolkit.edit_file(filename, changes)
                    
                    if result.success and result.data:
                        # Update current file content
                        self.current_file = filename
                        self.file_content = result.data.get("new", "")
                    elif not result.success:
                        console.print(f"[red]{result.error}[/red]")
                else:
                    console.print("[red]Please specify a filename to edit.[/red]")
                    
            elif intent == "delete_file":
                filename = parameters.get("filename", "")
                if filename:
                    confirm = not self.agent_mode  # Skip confirmation in agent mode
                    result = self.toolkit.delete_file(filename, confirm)
                    if not result.success:
                        console.print(f"[red]{result.error}[/red]")
                else:
                    console.print("[red]Please specify a filename to delete.[/red]")
                    
            elif intent == "execute_command":
                command = parameters.get("description", "")
                if command:
                    result = self.toolkit.execute_command(command)
                    if not result.success:
                        console.print(f"[red]{result.error}[/red]")
                else:
                    console.print("[red]Please specify a command to execute.[/red]")
                    
            elif intent == "use_tool":
                tool_name = parameters.get("tool_name", "")
                tool_args = parameters.get("tool_args", {})
                
                if tool_name in self.toolkit.get_available_tools():
                    self._use_specific_tool(tool_name, tool_args)
                else:
                    console.print(f"[red]Unknown tool: {tool_name}[/red]")
                    console.print(f"[yellow]Available tools: {', '.join(self.toolkit.get_available_tools())}[/yellow]")
                
            else:
                console.print(f"[yellow]Unknown intent: {intent}[/yellow]")
                
        except Exception as e:
            console.print(f"[red]Error executing action: {str(e)}[/red]")
            console.print(traceback.format_exc())

    def _generate_from_description(self, language: str, filename: str, description: str):
        """Generate code from description and save to file"""
        console.print(f"\n[cyan]Generating {language} code for: {filename}[/cyan]")
        
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
        
        # Save the code
        try:
            with open(filename, 'w') as f:
                f.write(code)
                
            console.print(f"[green]Code saved to {filename}[/green]")
            
            if "generated_files" not in self.history:
                self.history["generated_files"] = []
                
            self.history["generated_files"].append(filename)
            
            # Set as current file for further operations
            self.current_file = filename
            self.file_content = code
            
        except Exception as e:
            console.print(f"[red]Error saving file: {str(e)}[/red]")

    def _read_and_display_file(self, filename: str):
        """Read and display a file"""
        try:
            with open(filename, 'r') as f:
                content = f.read()
            
            # Determine file extension for syntax highlighting
            ext = filename.split('.')[-1] if '.' in filename else 'text'
            
            console.print(f"\n[green]Contents of {filename}:[/green]")
            console.print(Panel(
                Syntax(content, ext, theme="github-dark", line_numbers=True),
                title=f"📄 {filename}",
                border_style="royal_blue1"
            ))
            
            # Set as current file
            self.current_file = filename
            self.file_content = content
            
        except FileNotFoundError:
            console.print(f"[red]File not found: {filename}[/red]")
        except Exception as e:
            console.print(f"[red]Error reading file: {str(e)}[/red]")

    def _modify_file(self, filename: str, code: str, description: str):
        """Modify an existing file"""
        try:
            # Read current file content
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    current_content = f.read()
            else:
                current_content = ""
            
            # If code is provided, use it directly
            if code:
                new_content = code
            else:
                # Generate modifications based on description
                console.print(f"[cyan]Modifying {filename} based on: {description}[/cyan]")
                
                prompt = f"""
                Modify this file based on the description: {description}
                
                Current file content:
                ```
                {current_content}
                ```
                
                Provide the complete modified file content.
                """
                
                new_content = self.get_completion(prompt)
                
                # Extract code block if present
                if "```" in new_content:
                    code_blocks = new_content.split("```")
                    for i, block in enumerate(code_blocks):
                        if i % 2 == 1:  # Odd-indexed blocks are code
                            new_content = block.strip()
                            break
            
            # Show diff if file exists
            if current_content:
                show_diff(current_content, new_content, filename)
                
                # Skip confirmation in agent mode
                if not self.agent_mode:
                    if not Confirm.ask("Apply these changes?"):
                        console.print("[yellow]Changes cancelled.[/yellow]")
                        return
                else:
                    console.print("[bright_magenta]🤖 Agent Mode: Applying changes automatically...[/bright_magenta]")
            
            # Backup original file if it exists
            if os.path.exists(filename):
                backup_file = f"{filename}.bak"
                with open(backup_file, 'w') as f:
                    f.write(current_content)
                console.print(f"[dim]Original backed up to {backup_file}[/dim]")
            
            # Write new content
            with open(filename, 'w') as f:
                f.write(new_content)
            
            console.print(f"[green]Successfully modified {filename}[/green]")
            
            # Update current file
            self.current_file = filename
            self.file_content = new_content
            
        except Exception as e:
            console.print(f"[red]Error modifying file: {str(e)}[/red]")

    def _list_files(self):
        """List files in current directory"""
        try:
            items = os.listdir(".")
            
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Type", style="dim")
            table.add_column("Name", style="green")
            table.add_column("Size", style="cyan")
            
            dirs = sorted([item for item in items if os.path.isdir(item) and not item.startswith('.')])
            files = sorted([item for item in items if os.path.isfile(item) and not item.startswith('.')])
            
            for item_name in dirs:
                table.add_row("📁 DIR", f"[bold blue]{item_name}/[/bold blue]", "-")
            
            for item_name in files:
                try:
                    size = os.path.getsize(item_name)
                    size_str = f"{size:,} bytes" if size < 1024 else f"{size/1024:.1f} KB"
                except:
                    size_str = "?"
                table.add_row("📄 FILE", item_name, size_str)
            
            console.print(Panel(table, title="📂 Directory Contents", border_style="sky_blue1"))
            
        except Exception as e:
            console.print(f"[red]Error listing files: {str(e)}[/red]")

    # Override default to handle all unrecognized commands as chat
    def default(self, line):
        """Handle any unrecognized command as conversational input"""
        return self._handle_conversational_input(line)

    # Keep all existing methods but remove the command-specific intro messages
    def get_completion(self, prompt: str) -> str:
        """Get completion from SambaNova API"""
        try:
            response = self.client.chat.completions.create(
                model='Meta-Llama-3.1-8B-Instruct',
                messages=[
                    {"role": "system", "content": get_system_prompt("general_assistant")},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                top_p=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            if "Unauthorized" in error_msg or "Invalid API key" in error_msg:
                console.print(Panel(
                    "[red]❌ API Key Authentication Failed![/red]\n"
                    "[yellow]Your SambaNova API key appears to be invalid or expired.[/yellow]\n"
                    "[blue]Please update your SAMBANOVA_API_KEY in the .env file.[/blue]\n"
                    "[blue]Get a new key from: https://cloud.sambanova.ai/[/blue]",
                    title="🔑 Authentication Error",
                    border_style="red"
                ))
            elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
                console.print(Panel(
                    "[red]❌ API Rate Limit Exceeded![/red]\n"
                    "[yellow]You've hit the API rate limit. Please wait a moment and try again.[/yellow]",
                    title="⏳ Rate Limit",
                    border_style="yellow"
                ))
            else:
                console.print(Panel(
                    f"[red]❌ API Error:[/red] {error_msg}\n"
                    "[yellow]There was an issue connecting to the AI service.[/yellow]",
                    title="🌐 Connection Error",
                    border_style="red"
                ))
            return "I'm experiencing technical difficulties. Please check your API key and try again."

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
            error_msg = str(e)
            if "Unauthorized" in error_msg or "Invalid API key" in error_msg:
                console.print(Panel(
                    "[red]❌ API Key Authentication Failed![/red]\n"
                    "[yellow]Your SambaNova API key appears to be invalid or expired.[/yellow]\n"
                    "[blue]Please update your SAMBANOVA_API_KEY in the .env file.[/blue]",
                    title="🔑 Authentication Error",
                    border_style="red"
                ))
            else:
                console.print(Panel(
                    f"[red]❌ API Error:[/red] {error_msg}\n"
                    "[yellow]There was an issue connecting to the AI service.[/yellow]",
                    title="🌐 Connection Error",
                    border_style="red"
                ))
            return "I'm experiencing technical difficulties. Please check your API key and try again."

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
        
        # Skip confirmation in agent mode
        apply_fix = True
        if not self.agent_mode:
            apply_fix = Confirm.ask("Apply this fix?")
        else:
            console.print("[bright_magenta]🤖 Agent Mode: Applying fix automatically...[/bright_magenta]")
        
        if apply_fix:
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
            
            # Offer to run the fixed code (skip in agent mode)
            if not self.agent_mode:
                if Confirm.ask("Run the fixed code?"):
                    self.do_run("")
            else:
                console.print("[bright_magenta]🤖 Agent Mode: Running fixed code automatically...[/bright_magenta]")
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
        
        # Ask if user wants to implement any of these refactorings (skip in agent mode)
        implement_refactoring = False
        if not self.agent_mode:
            implement_refactoring = Confirm.ask("Would you like me to implement these refactorings for you?")
        else:
            implement_refactoring = True
            console.print("[bright_magenta]🤖 Agent Mode: Implementing refactorings automatically...[/bright_magenta]")
        
        if implement_refactoring:
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
            
            # Skip confirmation in agent mode
            apply_refactoring = True
            if not self.agent_mode:
                apply_refactoring = Confirm.ask("Apply these refactorings?")
            else:
                console.print("[bright_magenta]🤖 Agent Mode: Applying refactorings automatically...[/bright_magenta]")
            
            if apply_refactoring:
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
        
        # Ask if user wants to implement security fixes (skip in agent mode)
        implement_fixes = False
        if not self.agent_mode:
            implement_fixes = Confirm.ask("Would you like me to implement security fixes?")
        else:
            implement_fixes = True
            console.print("[bright_magenta]🤖 Agent Mode: Implementing security fixes automatically...[/bright_magenta]")
        
        if implement_fixes:
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
            
            # Skip confirmation in agent mode
            apply_fixes = True
            if not self.agent_mode:
                apply_fixes = Confirm.ask("Apply these security fixes?")
            else:
                console.print("[bright_magenta]🤖 Agent Mode: Applying security fixes automatically...[/bright_magenta]")
            
            if apply_fixes:
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
        
        # Ask if user wants to implement optimizations (skip in agent mode)
        implement_optimizations = False
        if not self.agent_mode:
            implement_optimizations = Confirm.ask("Would you like me to implement these optimizations?")
        else:
            implement_optimizations = True
            console.print("[bright_magenta]🤖 Agent Mode: Implementing optimizations automatically...[/bright_magenta]")
        
        if implement_optimizations:
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
            
            # Skip confirmation in agent mode
            apply_optimizations = True
            if not self.agent_mode:
                apply_optimizations = Confirm.ask("Apply these optimizations?")
            else:
                console.print("[bright_magenta]🤖 Agent Mode: Applying optimizations automatically...[/bright_magenta]")
            
            if apply_optimizations:
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

    def do_delete_api_key(self):
        """Delete the saved API key"""
        from .utils import delete_saved_api_key
        
        console.print("\n[cyan]Managing API key...[/cyan]")
        
        if Confirm.ask("Are you sure you want to delete your saved API key?"):
            # Delete from secure storage
            delete_saved_api_key()
            
            # Remove from environment variables if set
            if "SAMBANOVA_API_KEY" in os.environ:
                del os.environ["SAMBANOVA_API_KEY"]
                console.print("[green]Environment variable cleared[/green]")
            
            console.print("[green]✅ API key management completed![/green]")
            console.print("[yellow]You'll need to enter your API key again next time you start the assistant.[/yellow]")
        else:
            console.print("[yellow]API key deletion cancelled.[/yellow]")

    def _perform_web_search(self, query: str):
        """Perform web search and get AI analysis of results"""
        if not is_web_search_available():
            console.print(Panel(
                "[red]Web search not available. Install duckduckgo-search:[/red]\n"
                "[yellow]pip install -U duckduckgo-search[/yellow]",
                title="❌ Web Search Error",
                border_style="red"
            ))
            return
        
        try:
            # Perform the search
            console.print(f"[cyan]🔍 Searching the web for: {query}[/cyan]")
            
            with Progress() as progress:
                task = progress.add_task("[cyan]Searching...", total=100)
                progress.update(task, advance=30)
                
                # Search for general results
                results = search_web(query, max_results=5)
                progress.update(task, advance=60)
                
                # Also search for news if it seems relevant
                news_results = []
                if any(keyword in query.lower() for keyword in ['news', 'latest', 'recent', 'update', 'current']):
                    news_results = search_news(query, max_results=3)
                
                progress.update(task, completed=100)
            
            if not results and not news_results:
                console.print(Panel(
                    f"[yellow]No search results found for: {query}[/yellow]",
                    title="🔍 Search Results",
                    border_style="yellow"
                ))
                return
            
            # Display search results
            all_results = results + news_results
            display_search_results(all_results, query)
            
            # Get AI analysis of the search results
            console.print("\n[cyan]🤖 Getting AI analysis of search results...[/cyan]")
            
            search_context = format_search_results(all_results, query)
            
            # Use the web search prompt
            prompt = get_task_prompt("web_search", query=query)
            full_prompt = f"{prompt}\n\nSearch Results:\n{search_context}"
            
            try:
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
                
            except Exception as e:
                console.print(f"[red]Error getting AI analysis: {str(e)}[/red]")
                console.print("[yellow]Search results displayed above without AI analysis.[/yellow]")
                
        except Exception as e:
            console.print(Panel(
                f"[red]Search error: {str(e)}[/red]",
                title="❌ Web Search Error",
                border_style="red"
            ))

    def _use_specific_tool(self, tool_name: str, tool_args: Dict[str, Any]):
        """Use a specific tool with given arguments"""
        try:
            console.print(f"[cyan]🔧 Using tool: {tool_name}[/cyan]")
            
            # Get the tool method
            tool_method = getattr(self.toolkit, tool_name, None)
            if not tool_method:
                console.print(f"[red]Tool method not found: {tool_name}[/red]")
                return
            
            # Call the tool with arguments
            result = tool_method(**tool_args)
            
            if not result.success:
                console.print(f"[red]Tool execution failed: {result.error}[/red]")
            else:
                console.print(f"[green]Tool executed successfully: {result.message}[/green]")
                
        except Exception as e:
            console.print(f"[red]Error using tool {tool_name}: {str(e)}[/red]")

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