#!/usr/bin/env python3
"""
Web Search functionality for NOVA-CLI-AGENT using Tavily
"""

import json
import time
import os
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # dotenv is optional

try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

console = Console()

class WebSearcher:
    """Web search functionality using Tavily"""
    
    def __init__(self):
        self.api_key = os.getenv('TAVILY_API_KEY')
        if not self.api_key:
            console.print(Panel(
                "[red]TAVILY_API_KEY not found in environment variables.[/red]\n"
                "[yellow]Please set TAVILY_API_KEY in your .env file or environment.[/yellow]",
                title="❌ Missing API Key",
                border_style="red"
            ))
        self.client = TavilyClient(self.api_key) if (TAVILY_AVAILABLE and self.api_key) else None
        self.last_search_time = 0
        self.min_search_interval = 1.0  # Minimum 1 second between searches (Tavily is less restrictive)
    
    def is_available(self) -> bool:
        """Check if web search is available"""
        return TAVILY_AVAILABLE and self.api_key is not None
    
    def _wait_for_rate_limit(self):
        """Wait to respect rate limiting"""
        current_time = time.time()
        time_since_last_search = current_time - self.last_search_time
        
        if time_since_last_search < self.min_search_interval:
            wait_time = self.min_search_interval - time_since_last_search
            console.print(f"⏳ Waiting {wait_time:.1f}s to respect rate limits...")
            time.sleep(wait_time)
        
        self.last_search_time = time.time()
    
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search the web using Tavily
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of search results with title, body, and href
        """
        if not self.is_available():
            console.print(Panel(
                "[red]Web search not available. Install tavily-python:[/red]\n"
                "[yellow]pip install tavily-python[/yellow]",
                title="❌ Web Search Error",
                border_style="red"
            ))
            return []
        
        try:
            # Wait to respect rate limits
            self._wait_for_rate_limit()
            
            console.print(f"🔍 Searching the web for: [cyan]{query}[/cyan]")
            
            # Use Tavily search
            response = self.client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
                include_answer=True,
                include_raw_content=False
            )
            
            results = []
            
            # Extract results from Tavily response
            if 'results' in response:
                for result in response['results']:
                    results.append({
                        'title': result.get('title', ''),
                        'body': result.get('content', ''),
                        'href': result.get('url', ''),
                        'source': 'Tavily',
                        'score': result.get('score', 0)
                    })
            
            console.print(f"✅ Found {len(results)} results")
            return results
            
        except Exception as e:
            error_msg = str(e)
            if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                console.print(Panel(
                    "[red]Rate limit exceeded. Please wait a few minutes before searching again.[/red]\n"
                    "[yellow]Try reducing search frequency or waiting longer between searches.[/yellow]",
                    title="❌ Rate Limit Error",
                    border_style="red"
                ))
            else:
                console.print(Panel(
                    f"[red]Search error: {error_msg}[/red]",
                    title="❌ Web Search Error",
                    border_style="red"
                ))
            return []
    
    def search_news(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for news using Tavily
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of news results
        """
        if not self.is_available():
            console.print(Panel(
                "[red]Web search not available. Install tavily-python:[/red]\n"
                "[yellow]pip install tavily-python[/yellow]",
                title="❌ Web Search Error",
                border_style="red"
            ))
            return []
        
        try:
            # Wait to respect rate limits
            self._wait_for_rate_limit()
            
            console.print(f"📰 Searching news for: [cyan]{query}[/cyan]")
            
            # Use Tavily news search with topic filter
            response = self.client.search(
                query=f"news {query}",
                max_results=max_results,
                search_depth="basic",
                include_answer=True,
                include_raw_content=False,
                topic="news"
            )
            
            results = []
            
            # Extract results from Tavily response
            if 'results' in response:
                for result in response['results']:
                    results.append({
                        'title': result.get('title', ''),
                        'body': result.get('content', ''),
                        'href': result.get('url', ''),
                        'date': result.get('published_date', ''),
                        'source': 'Tavily News',
                        'score': result.get('score', 0)
                    })
            
            console.print(f"✅ Found {len(results)} news results")
            return results
            
        except Exception as e:
            error_msg = str(e)
            if "rate" in error_msg.lower() or "limit" in error_msg.lower():
                console.print(Panel(
                    "[red]Rate limit exceeded. Please wait a few minutes before searching again.[/red]\n"
                    "[yellow]Try reducing search frequency or waiting longer between searches.[/yellow]",
                    title="❌ Rate Limit Error",
                    border_style="red"
                ))
            else:
                console.print(Panel(
                    f"[red]News search error: {error_msg}[/red]",
                    title="❌ Web Search Error",
                    border_style="red"
                ))
            return []
    
    def format_results(self, results: List[Dict[str, Any]], query: str) -> str:
        """
        Format search results for AI processing
        
        Args:
            results: List of search results
            query: Original search query
            
        Returns:
            Formatted string with search results
        """
        if not results:
            return f"No search results found for: {query}"
        
        formatted = f"Web search results for: {query}\n\n"
        
        for i, result in enumerate(results, 1):
            formatted += f"Result {i}:\n"
            formatted += f"Title: {result.get('title', 'N/A')}\n"
            formatted += f"URL: {result.get('href', 'N/A')}\n"
            formatted += f"Summary: {result.get('body', 'N/A')}\n"
            
            if result.get('date'):
                formatted += f"Date: {result.get('date')}\n"
            
            formatted += f"Source: {result.get('source', 'Tavily')}\n"
            formatted += "-" * 50 + "\n\n"
        
        return formatted
    
    def display_results(self, results: List[Dict[str, Any]], query: str):
        """
        Display search results in a nice format
        
        Args:
            results: List of search results
            query: Original search query
        """
        if not results:
            console.print(Panel(
                f"[yellow]No results found for: {query}[/yellow]",
                title="🔍 Search Results",
                border_style="yellow"
            ))
            return
        
        console.print(Panel(
            f"[green]Found {len(results)} results for: [bold]{query}[/bold][/green]",
            title="🔍 Search Results",
            border_style="green"
        ))
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            url = result.get('href', 'No URL')
            body = result.get('body', 'No description')
            source = result.get('source', 'Tavily')
            
            # Truncate body if too long
            if len(body) > 200:
                body = body[:200] + "..."
            
            result_text = f"[bold blue]{title}[/bold blue]\n"
            result_text += f"[dim]{url}[/dim]\n"
            result_text += f"{body}\n"
            result_text += f"[dim]Source: {source}[/dim]"
            
            if result.get('date'):
                result_text += f" | [dim]Date: {result.get('date')}[/dim]"
            
            console.print(Panel(
                result_text,
                title=f"Result {i}",
                border_style="blue",
                padding=(0, 1)
            ))

# Global instance
web_searcher = WebSearcher()

def search_web(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Convenience function for web search"""
    return web_searcher.search(query, max_results)

def search_news(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Convenience function for news search"""
    return web_searcher.search_news(query, max_results)

def format_search_results(results: List[Dict[str, Any]], query: str) -> str:
    """Convenience function for formatting results"""
    return web_searcher.format_results(results, query)

def display_search_results(results: List[Dict[str, Any]], query: str):
    """Convenience function for displaying results"""
    web_searcher.display_results(results, query)

def is_web_search_available() -> bool:
    """Check if web search functionality is available"""
    return web_searcher.is_available() 