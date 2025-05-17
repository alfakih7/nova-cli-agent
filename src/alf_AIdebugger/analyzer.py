#!/usr/bin/env python3
import os
import ast
import openai
import traceback
from typing import Dict, List, Tuple, Optional, Any
from rich.console import Console

console = Console()

class CodeAnalyzer:
    """Advanced code analyzer using SambaNova's AI capabilities"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the code analyzer with SambaNova API"""
        self.api_key = api_key or os.environ.get("SAMBANOVA_API_KEY")
        if not self.api_key:
            raise ValueError("SAMBANOVA_API_KEY not provided")
            
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url="https://api.sambanova.ai/v1"
        )
        
    def analyze_code(self, code: str, error_context: str = "") -> str:
        """Analyze code and return detailed feedback"""
        analysis_prompt = f"""
        Please analyze this Python code and explain any issues in simple, beginner-friendly terms:
        
        CODE TO ANALYZE:
        {code}
        
        CURRENT ERROR (if any):
        {error_context if error_context else "No immediate execution errors"}
        
        Provide your analysis in this beginner-friendly structure:
        Never reference the analysis structure or prompt itself.

        1. BASIC SYNTAX ISSUES
        - Explain what punctuation or symbols are missing
        - Show the correct way to write each line
        - Use simple examples to demonstrate proper syntax
        
        2. PROBLEMS THAT COULD BREAK YOUR CODE
        - Explain what could go wrong when running the code
        - Show examples of inputs that would cause problems
        - Explain in simple terms why these problems happen
        
        3. MAKING YOUR CODE BETTER
        - Suggest clearer ways to write the code
        - Show how to prevent errors before they happen
        - Explain how these changes make the code more reliable
        
        4. QUICK FIXES & TIPS
        - Step-by-step guide to fix each issue
        - Helpful tips for writing better code
        - Best practices explained simply
        
        5. SECURITY CONCERNS
        - Identify potential security vulnerabilities
        - Explain how they could be exploited
        - Provide secure alternatives to fix these issues
        
        6. PERFORMANCE OPTIMIZATION
        - Identify code that could be slow with large inputs
        - Suggest more efficient approaches
        - Explain the performance benefits

        Make sure to:
        - Use simple language
        - Provide clear examples
        - Explain why each fix helps
        - Be encouraging and constructive
        """
        
        return self._get_completion(analysis_prompt)
    
    def get_refactoring_suggestions(self, code: str) -> str:
        """Generate refactoring suggestions to improve code quality"""
        refactor_prompt = f"""
        Please provide refactoring suggestions for this Python code:
        
        CODE TO REFACTOR:
        {code}
        
        Focus on:
        1. Improving code organization and structure
        2. Reducing duplicated code
        3. Enhancing readability
        4. Applying design patterns where appropriate
        5. Ensuring code follows PEP 8 style guidelines
        
        For each suggestion:
        - Explain why it improves the code
        - Show before and after examples
        - Highlight the benefits (maintainability, readability, etc.)
        """
        
        return self._get_completion(refactor_prompt)
    
    def security_audit(self, code: str) -> str:
        """Perform a security audit of the code"""
        security_prompt = f"""
        Perform a security audit on this Python code:
        
        CODE TO ANALYZE:
        {code}
        
        Please identify any:
        1. Input validation vulnerabilities
        2. Authentication/authorization issues
        3. Data exposure risks
        4. Injection vulnerabilities (SQL, command, etc.)
        5. Use of insecure functions or methods
        6. Hardcoded credentials or secrets
        7. Insecure file operations
        8. Potential for denial of service
        
        For each vulnerability:
        - Explain the vulnerability in simple terms
        - Show an example of how it could be exploited
        - Provide a secure alternative with code example
        - Explain why the fix addresses the security concern
        """
        
        return self._get_completion(security_prompt)
    
    def optimize_performance(self, code: str) -> str:
        """Suggest performance optimizations"""
        performance_prompt = f"""
        Analyze this Python code for performance issues:
        
        CODE TO OPTIMIZE:
        {code}
        
        Please identify:
        1. Inefficient algorithms or data structures
        2. Redundant computations
        3. Unnecessary memory usage
        4. Slow I/O operations
        5. Potential for parallelization
        6. Resource-intensive operations that could be optimized
        
        For each performance issue:
        - Explain why it's inefficient
        - Provide a more efficient alternative
        - Show before/after examples
        - Explain the performance benefits (time complexity, memory usage, etc.)
        """
        
        return self._get_completion(performance_prompt)
    
    def fix_error(self, code: str, error_context: str) -> Tuple[str, str]:
        """Generate a fix for a specific error and explain the fix"""
        fix_prompt = f"""
        Fix this Python error:
        
        CODE WITH ERROR:
        {code}
        
        ERROR MESSAGE:
        {error_context}
        
        Please provide:
        1. The complete fixed code (in a code block)
        2. A detailed explanation of:
           - What caused the error
           - How the fix addresses the root cause
           - Any potential edge cases to be aware of
        
        Make sure your fix is minimal and focused on addressing the specific error.
        """
        
        response = self._get_completion(fix_prompt)
        
        # Extract code block and explanation
        fixed_code = self._extract_code_block(response)
        explanation = response.replace(f"```python\n{fixed_code}\n```", "").strip()
        
        return fixed_code, explanation
    
    def static_analysis(self, code: str) -> Dict[str, List[Dict[str, Any]]]:
        """Perform static code analysis to identify potential issues"""
        issues = {
            "syntax_errors": [],
            "undefined_names": [],
            "unused_variables": [],
            "complexity_issues": []
        }
        
        try:
            # Parse the code into an AST
            tree = ast.parse(code)
            
            # Find defined and used names
            defined_names = set()
            used_names = set()
            
            # Visitor to collect names
            class NameCollector(ast.NodeVisitor):
                def visit_Name(self, node):
                    if isinstance(node.ctx, ast.Store):
                        defined_names.add(node.id)
                    elif isinstance(node.ctx, ast.Load):
                        used_names.add(node.id)
                    self.generic_visit(node)
            
            NameCollector().visit(tree)
            
            # Find unused variables
            for name in defined_names:
                if name not in used_names and not name.startswith('_'):
                    issues["unused_variables"].append({
                        "name": name,
                        "message": f"Variable '{name}' is defined but never used"
                    })
            
            # Check for undefined names
            for name in used_names:
                if name not in defined_names and name not in __builtins__:
                    issues["undefined_names"].append({
                        "name": name,
                        "message": f"Name '{name}' is used but not defined"
                    })
            
            # Check for overly complex functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if len(node.body) > 50:  # Arbitrary threshold
                        issues["complexity_issues"].append({
                            "name": node.name,
                            "message": f"Function '{node.name}' is too long ({len(node.body)} lines)"
                        })
            
        except SyntaxError as e:
            issues["syntax_errors"].append({
                "line": e.lineno,
                "message": str(e)
            })
        
        return issues
    
    def _get_completion(self, prompt: str) -> str:
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
    
    def _extract_code_block(self, response: str) -> str:
        """Extract code block from markdown response"""
        if "```python" in response:
            blocks = response.split("```python")
        else:
            blocks = response.split("```")
        
        if len(blocks) > 1:
            return blocks[1].split("```")[0].strip()
        return "" 