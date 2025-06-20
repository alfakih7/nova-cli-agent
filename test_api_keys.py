#!/usr/bin/env python3
"""
Test script to verify API keys are working correctly
"""

import os
from rich.console import Console
from rich.panel import Panel

console = Console()

def test_api_keys():
    """Test both SambaNova and Tavily API keys"""
    console.print(Panel(
        "[bold blue]🔍 Testing API Keys[/bold blue]",
        title="Nova CLI-Agent API Test",
        border_style="blue"
    ))
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        console.print("✅ [green]dotenv loaded successfully[/green]")
    except ImportError:
        console.print("⚠️  [yellow]python-dotenv not installed, using system env vars only[/yellow]")
    
    # Test SambaNova API Key
    sambanova_key = os.getenv('SAMBANOVA_API_KEY')
    console.print(f"\n🔑 **SambaNova API Key:**")
    
    if not sambanova_key:
        console.print("❌ [red]SAMBANOVA_API_KEY not found in environment[/red]")
    elif sambanova_key == "your_sambanova_api_key_here":
        console.print("❌ [red]SAMBANOVA_API_KEY is still set to placeholder value[/red]")
        console.print("   [yellow]Please replace it with your actual API key from https://cloud.sambanova.ai/[/yellow]")
    else:
        console.print(f"✅ [green]SAMBANOVA_API_KEY found: {sambanova_key[:10]}...[/green]")
        
        # Test the API key
        try:
            import openai
            client = openai.OpenAI(
                api_key=sambanova_key,
                base_url="https://api.sambanova.ai/v1"
            )
            
            response = client.chat.completions.create(
                model="Meta-Llama-3.1-8B-Instruct",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            console.print("✅ [green]SambaNova API test successful![/green]")
            
        except Exception as e:
            console.print(f"❌ [red]SambaNova API test failed: {str(e)}[/red]")
    
    # Test Tavily API Key
    tavily_key = os.getenv('TAVILY_API_KEY')
    console.print(f"\n🔍 **Tavily API Key:**")
    
    if not tavily_key:
        console.print("❌ [red]TAVILY_API_KEY not found in environment[/red]")
    elif tavily_key == "your_tavily_api_key_here":
        console.print("❌ [red]TAVILY_API_KEY is still set to placeholder value[/red]")
    else:
        console.print(f"✅ [green]TAVILY_API_KEY found: {tavily_key[:10]}...[/green]")
        
        # Test the API key
        try:
            from tavily import TavilyClient
            client = TavilyClient(tavily_key)
            
            response = client.search(query="test", max_results=1)
            console.print("✅ [green]Tavily API test successful![/green]")
            
        except Exception as e:
            console.print(f"❌ [red]Tavily API test failed: {str(e)}[/red]")
    
    console.print(Panel(
        "[bold green]Testing complete![/bold green]\n"
        "[yellow]If you see any errors above, please update your .env file with valid API keys.[/yellow]",
        title="🎉 Results",
        border_style="green"
    ))

if __name__ == "__main__":
    test_api_keys() 