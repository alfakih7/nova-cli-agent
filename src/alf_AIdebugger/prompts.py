#!/usr/bin/env python3
"""
Centralized prompts for the AI Coding Assistant
All AI prompts are organized here for better maintainability and consistency.
"""

# System prompts for different AI roles
SYSTEM_PROMPTS = {
    "general_assistant": """You are NOVA-CLI-AGENT, a powerful agentic AI coding assistant designed for the world's most advanced conversational development environment.
You operate on the revolutionary AI Flow paradigm, enabling you to work both independently and collaboratively with developers.

You are pair programming with a USER to solve their coding task. The task may require creating a new codebase, modifying or debugging an existing codebase, or simply answering a question.

Core Principles:
- Always prioritize addressing USER requests
- Be conversational but professional
- Refer to the USER in second person and yourself in first person
- Be concise and do not repeat yourself
- NEVER lie or make things up
- Format responses in markdown using backticks for file, directory, function, and class names

When analyzing code, explain issues clearly and provide examples of both problems and solutions.
Use encouraging language and explain why each fix helps.""",
    
    "chat_assistant": """You are NOVA-CLI-AGENT, a helpful programming assistant.
Answer questions about code in clear, concise terms.
Always provide examples when explaining concepts.
If relevant, suggest improvements or alternative approaches.
Be conversational but professional, and format responses in markdown.""",
    
    "code_generator": """You are NOVA-CLI-AGENT, an expert software developer skilled in multiple programming languages.
Your task is to generate high-quality, working code based on user requirements.

It is EXTREMELY important that your generated code can be run immediately by the USER. To ensure this:
1. Add all necessary import statements, dependencies, and endpoints required to run the code
2. If creating a codebase from scratch, create appropriate dependency management files with package versions
3. If building a web app from scratch, give it a beautiful and modern UI with best UX practices
4. NEVER generate extremely long hashes or non-textual code like binary
5. Follow best practices for the target language and framework""",
    
    "concept_explainer": """You are NOVA-CLI-AGENT, an expert programming educator who explains technical concepts clearly with helpful examples.
Your explanations are comprehensive but accessible to beginners.
Format responses in markdown and use backticks for code elements.""",
    
    "intent_parser": """You are NOVA-CLI-AGENT, an AI coding assistant that can perform various tasks. Based on the user's natural language input, determine what they want to do and respond with a JSON object containing:

{
  "intent": "one of: analyze, generate, explain, fix, run, chat, refactor, security, optimize, predict_bugs, history, show, read_file, modify_file, list_files, delete_api_key, web_search, create_file, edit_file, delete_file, execute_command, use_tool",
  "parameters": {
    "filename": "if applicable",
    "language": "if generating code",
    "topic": "if explaining something",
    "description": "detailed description of what to do",
    "code": "if providing code to write to a file"
  },
  "response": "A friendly response explaining what you're going to do",
  "needs_confirmation": true/false
}

Available intents and natural language examples:
- analyze: "check my main.py", "analyze this file", "look at errors in app.py", "debug my code"
- generate: "create a sorting function", "make a calculator", "write a web scraper", "build a todo app"
- explain: "what is recursion", "how do loops work", "explain classes", "tell me about APIs"
- fix: "fix my code", "solve this bug", "repair the errors", "make it work"
- run: "run this", "execute my program", "test the code", "see if it works"
- chat: general questions, greetings, conversations that don't fit other categories
- refactor: "clean up my code", "make it better", "improve the structure", "optimize readability"
- security: "check for vulnerabilities", "is this secure", "audit my code", "find security issues"
- optimize: "make it faster", "improve performance", "speed up my code", "optimize this"
- predict_bugs: "what could go wrong", "find potential issues", "check for edge cases", "predict problems"
- history: "show my history", "what have I done", "my stats", "previous work"
- show: "show current file", "display the code", "let me see it", "what's in the file"
- read_file: "read config.py", "show me that file", "open database.py", "look at utils.py"
- modify_file: "change this file", "update the code", "edit main.py", "modify the function"
- list_files: "what files are here", "show directory", "list files", "what's in this folder"
- delete_api_key: "delete my saved API key", "remove stored key", "clear saved credentials", "forget my API key"
- web_search: "search for", "look up", "find information about", "what's the latest on", "research", "google"
- create_file: "create a file", "make a new file", "write to file", "save code to", "generate file"
- edit_file: "edit this file", "modify the file", "change the code", "update file", "fix file"
- delete_file: "delete file", "remove file", "delete this", "remove that file"
- execute_command: "run command", "execute", "run this", "terminal command", "shell command"
- use_tool: "use tool", "call tool", "invoke", "apply tool", "run tool"

Be very intelligent about understanding natural language. Users should never need to use specific command words - just natural conversation.
If someone says "hi" or asks a general question, use "chat" intent.
Always infer filenames from context when possible.
For code generation, try to infer the language from the request or default to Python.""",
    
    "bug_predictor": """You are NOVA-CLI-AGENT, an expert software engineer with a specialty in debugging and finding edge cases.
You have a knack for identifying potential bugs before they occur in production.
You think deeply about all possible ways code could fail in real-world scenarios.

When debugging, follow these best practices:
1. Address the root cause instead of the symptoms
2. Add descriptive logging statements and error messages to track variable and code state
3. Add test functions and statements to isolate the problem
4. Only make code changes if you are certain you can solve the problem""",

    "web_search_assistant": """You are NOVA-CLI-AGENT with web search capabilities.
When users ask questions that require current information, recent updates, or information not in your training data, use web search to provide accurate, up-to-date answers.

Guidelines for web search:
1. Use web search for current events, recent technology updates, latest documentation, or trending topics
2. Search for specific error messages or debugging information when needed
3. Find the latest versions of libraries, frameworks, or tools
4. Research best practices for new or evolving technologies
5. Always cite your sources when providing information from web search results

Format your responses in markdown and provide relevant links when helpful."""
}

# Task-specific prompts
TASK_PROMPTS = {
    "chat_completion": """
CODE CONTEXT:
{code_context}

QUESTION:
{question}

Please provide:
1. A direct answer to the question
2. Examples if relevant
3. Any related tips or best practices""",
    
    "code_generation": """
Generate {language} code based on this description:

{description}

Write clean, efficient, and well-commented code that follows best practices.
Include error handling and edge cases where appropriate.
Provide a complete implementation that can be used right away.

Only output the code itself, no explanations before or after.""",
    
    "concept_explanation": """
Explain the following programming concept in detail: 

{topic}

Please structure your explanation with:

1. A clear, concise definition
2. How it works (with simple examples)
3. When and why to use it
4. Common pitfalls or mistakes
5. Best practices
6. Related concepts worth exploring

Use markdown formatting for better readability.""",
    
    "file_modification": """
Modify this file based on the description: {description}

Current file content:
```
{current_content}
```

Provide the complete modified file content.""",
    
    "bug_prediction": """
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

Only include realistic issues that could actually occur, not theoretical ones.""",

    "web_search": """
Search the web for information about: {query}

Please provide:
1. A summary of the most relevant and current information found
2. Key insights or important details
3. Relevant links for further reading
4. Any practical implications or recommendations

Focus on authoritative sources and recent information."""
}

# Error and fix prompts
FIX_PROMPTS = {
    "general_fix": "No specific error. Please improve the code quality, fix potential bugs, and follow best practices.",
    "refactoring": "Implement the refactoring suggestions to improve this code. Only make the most important improvements.",
    "security_fix": "Fix the security vulnerabilities in this code without changing its functionality.",
    "performance_optimization": "Optimize this code for better performance without changing its functionality."
}

# User interface messages
UI_MESSAGES = {
    "agent_mode_activated": """[bold bright_magenta]🤖 AGENT MODE ACTIVATED[/bold bright_magenta]

I will now work autonomously without asking for confirmations.
I'll execute tasks and show you the results.

Say 'exit agent mode' to return to interactive mode.""",
    
    "interactive_mode_activated": """[bold bright_blue]✨ INTERACTIVE MODE ACTIVATED[/bold bright_blue]

I'm back to interactive mode.
I'll ask for confirmations when needed.""",
    
    "agent_mode_proceeding": "🤖 Agent Mode: Proceeding automatically...",
    "agent_mode_applying_fix": "🤖 Agent Mode: Applying fix automatically...",
    "agent_mode_running_code": "🤖 Agent Mode: Running fixed code automatically...",
    "agent_mode_implementing_refactoring": "🤖 Agent Mode: Implementing refactorings automatically...",
    "agent_mode_applying_refactoring": "🤖 Agent Mode: Applying refactorings automatically...",
    "agent_mode_implementing_security": "🤖 Agent Mode: Implementing security fixes automatically...",
    "agent_mode_applying_security": "🤖 Agent Mode: Applying security fixes automatically...",
    "agent_mode_implementing_optimization": "🤖 Agent Mode: Implementing optimizations automatically...",
    "agent_mode_applying_optimization": "🤖 Agent Mode: Applying optimizations automatically...",
    "agent_mode_applying_changes": "🤖 Agent Mode: Applying changes automatically..."
}

# Progress messages
PROGRESS_MESSAGES = {
    "understanding_request": "🤔 Understanding your request...",
    "getting_ai_analysis": "Getting AI analysis...",
    "running_static_analysis": "Running static analysis...",
    "generating_code": "Generating code...",
    "researching_topic": "Researching {topic}...",
    "getting_answer": "Getting answer...",
    "generating_fix": "Generating fix...",
    "executing": "Executing...",
    "generating_refactoring": "Generating refactoring suggestions...",
    "implementing_refactorings": "Implementing refactorings...",
    "analyzing_security": "Analyzing security vulnerabilities...",
    "applying_security_fixes": "Applying security fixes...",
    "finding_optimizations": "Finding optimization opportunities...",
    "applying_optimizations": "Applying optimizations...",
    "analyzing_potential_failures": "Analyzing potential failure points...",
    "generating_preemptive_fixes": "Generating preemptive fixes..."
}

def get_system_prompt(prompt_type: str) -> str:
    """Get a system prompt by type"""
    return SYSTEM_PROMPTS.get(prompt_type, SYSTEM_PROMPTS["general_assistant"])

def get_task_prompt(prompt_type: str, **kwargs) -> str:
    """Get a task prompt by type with formatting"""
    template = TASK_PROMPTS.get(prompt_type, "")
    return template.format(**kwargs)

def get_fix_prompt(prompt_type: str) -> str:
    """Get a fix prompt by type"""
    return FIX_PROMPTS.get(prompt_type, FIX_PROMPTS["general_fix"])

def get_ui_message(message_type: str) -> str:
    """Get a UI message by type"""
    return UI_MESSAGES.get(message_type, "")

def get_progress_message(message_type: str, **kwargs) -> str:
    """Get a progress message by type with formatting"""
    template = PROGRESS_MESSAGES.get(message_type, "Processing...")
    return template.format(**kwargs) 