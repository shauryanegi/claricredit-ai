"""
Web Search Tool for Agentic RAG
===============================

🎯 WHAT IS THIS?
----------------
Your RAG pipeline reads uploaded PDFs. But what if:
- PDF mentions "Q3 2024 market conditions" without explaining
- You need current stock prices or news
- Document references external reports

This tool lets the agent "Google" for missing information.

🔧 HOW IT WORKS (Simple):
-------------------------
1. Agent realizes: "I don't have enough info in the PDF"
2. Agent calls: web_search("Malaysia construction industry Q3 2024")
3. Gets back: Summarized web results
4. Uses this + PDF context to generate better answer

This is what makes it "Agentic" - the agent decides when to use tools!
"""

import os
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    content: str
    score: float = 0.0


class WebSearchTool:
    """
    Web search tool for augmenting RAG with external knowledge.
    
    Supports multiple backends:
    - Tavily (recommended for AI apps - pre-summarized)
    - SerpAPI (Google results)
    - DuckDuckGo (free, no API key)
    
    Simple Usage:
    -------------
    search = WebSearchTool()
    results = search.search("Malaysia GDP growth 2024")
    # Returns: ["Malaysia's GDP grew 5.1% in Q3 2024...", ...]
    """
    
    def __init__(self, backend: str = "duckduckgo"):
        """
        Initialize web search.
        
        Args:
            backend: Which search to use
                - "tavily": Best for AI (needs TAVILY_API_KEY)
                - "duckduckgo": Free, no API key needed
        """
        self.backend = backend
        self._validate_backend()
    
    def _validate_backend(self):
        """Check if backend is properly configured."""
        if self.backend == "tavily":
            if not os.getenv("TAVILY_API_KEY"):
                logger.warning("TAVILY_API_KEY not set. Falling back to DuckDuckGo.")
                self.backend = "duckduckgo"
    
    def search(
        self, 
        query: str, 
        max_results: int = 3,
        search_depth: str = "basic"
    ) -> List[str]:
        """
        Search the web and return relevant content.
        
        Args:
            query: What to search for
            max_results: How many results to return
            search_depth: "basic" or "advanced" (Tavily only)
            
        Returns:
            List of relevant text snippets from the web
            
        Example:
            >>> tool = WebSearchTool()
            >>> tool.search("Maybank credit rating 2024")
            ["Maybank maintains AA3 rating according to RAM...", ...]
        """
        if self.backend == "tavily":
            return self._search_tavily(query, max_results, search_depth)
        else:
            return self._search_duckduckgo(query, max_results)
    
    def _search_tavily(self, query: str, max_results: int, depth: str) -> List[str]:
        """Search using Tavily API (best for AI applications)."""
        try:
            from tavily import TavilyClient
            
            client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth=depth,
                include_answer=True  # Get AI-summarized answer too
            )
            
            results = []
            
            # Add the AI-generated answer first (if available)
            if response.get("answer"):
                results.append(f"Summary: {response['answer']}")
            
            # Add individual results
            for result in response.get("results", []):
                results.append(result.get("content", ""))
            
            logger.info(f"Tavily search returned {len(results)} results for: {query}")
            return results
            
        except ImportError:
            logger.warning("Tavily not installed. Run: pip install tavily-python")
            return self._search_duckduckgo(query, max_results)
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []
    
    def _search_duckduckgo(self, query: str, max_results: int) -> List[str]:
        """Search using DuckDuckGo (free, no API key)."""
        try:
            from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            
            contents = [r.get("body", "") for r in results if r.get("body")]
            logger.info(f"DuckDuckGo search returned {len(contents)} results for: {query}")
            return contents
            
        except ImportError:
            logger.warning("duckduckgo-search not installed. Run: pip install duckduckgo-search")
            return []
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    def search_and_format(self, query: str, max_results: int = 3) -> str:
        """
        Search and return as a formatted string for LLM context.
        
        This is what you'd inject into your RAG prompt when document
        context is insufficient.
        
        Example Output:
            "Web Search Results for 'Malaysia construction 2024':
             1. The construction industry grew 8% in 2024...
             2. Major projects include MRT3 and ECRL..."
        """
        results = self.search(query, max_results)
        
        if not results:
            return f"No web results found for: {query}"
        
        formatted = f"Web Search Results for '{query}':\n"
        for i, result in enumerate(results, 1):
            # Truncate long results
            truncated = result[:500] + "..." if len(result) > 500 else result
            formatted += f"\n{i}. {truncated}\n"
        
        return formatted


# Convenience function for simple usage
def web_search(query: str, max_results: int = 3) -> List[str]:
    """Quick web search without creating an instance."""
    tool = WebSearchTool()
    return tool.search(query, max_results)
