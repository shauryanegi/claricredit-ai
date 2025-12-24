"""
ReAct Agent for Credit Memo Generation
=======================================

🎯 WHAT IS ReAct?
-----------------
ReAct = Reasoning + Acting

Normal LLM: "Here's the answer" (one shot)
ReAct LLM: "Let me think... I need to search for X... 
           Got result Y... Now I can answer..."

It's like the difference between:
- Answering a test question immediately
- Showing your work step by step

📊 THE REACT LOOP:
------------------
1. THOUGHT: "I need to find the company's debt ratio"
2. ACTION: Call retrieve_documents(query="debt ratio")
3. OBSERVATION: "The debt ratio is 45% as stated on page 12"
4. THOUGHT: "That's not enough, I should verify with other metrics"
5. ACTION: Call retrieve_documents(query="total debt liabilities")
6. OBSERVATION: "Total debt is $5M, total assets $11M"
7. THOUGHT: "Now I have enough info"
8. FINAL ANSWER: "The debt ratio is 45%..."

🔧 WHY IS THIS BETTER?
---------------------
- More accurate: Agent verifies before answering
- Transparent: You can see the reasoning
- Flexible: Agent decides what tools to use
- Self-correcting: Agent can re-search if first try fails

📚 INTERVIEW TALKING POINT:
---------------------------
"The ReAct pattern allows the agent to dynamically decide which
retrieval queries to run. Unlike fixed pipeline where we hardcode
queries per section, ReAct lets the agent reason about what
information is missing and fetch it on demand."
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AgentAction(Enum):
    """Actions the agent can take."""
    RETRIEVE = "retrieve"       # Search documents
    WEB_SEARCH = "web_search"   # Search the web
    CALCULATE = "calculate"     # Do math
    FINAL_ANSWER = "final_answer"


@dataclass
class AgentStep:
    """A single step in the agent's reasoning."""
    thought: str
    action: Optional[AgentAction] = None
    action_input: Optional[Dict[str, Any]] = None
    observation: Optional[str] = None


class ReActAgent:
    """
    ReAct Agent for Credit Memo Generation.
    
    Simple Usage:
    -------------
    # Create agent with tools
    agent = ReActAgent(
        llm=YourLLM(),
        tools={
            "retrieve": your_retrieve_function,
            "web_search": your_search_function
        }
    )
    
    # Run agent on a question
    answer, steps = agent.run(
        query="What is the company's debt ratio?",
        max_steps=5
    )
    
    # See the reasoning
    for step in steps:
        print(f"Thought: {step.thought}")
        print(f"Action: {step.action}")
        print(f"Result: {step.observation}")
    """
    
    def __init__(
        self,
        llm,  # LLM adapter instance
        tools: Dict[str, Callable],
        max_steps: int = 5
    ):
        """
        Initialize ReAct agent.
        
        Args:
            llm: LLM adapter (LocalLLMAdapter or similar)
            tools: Dictionary of {tool_name: tool_function}
            max_steps: Maximum reasoning steps before forcing answer
        """
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        
        # Build tool descriptions for the prompt
        self.tool_descriptions = self._build_tool_descriptions()
    
    def _build_tool_descriptions(self) -> str:
        """Create tool documentation for the LLM."""
        descriptions = []
        
        tool_docs = {
            "retrieve": "retrieve(query, k) - Search documents for relevant information",
            "web_search": "web_search(query) - Search the web for external information",
            "calculate": "calculate(expression) - Evaluate a mathematical expression"
        }
        
        for name in self.tools:
            if name in tool_docs:
                descriptions.append(f"  - {tool_docs[name]}")
            else:
                descriptions.append(f"  - {name}(...) - Custom tool")
        
        return "\n".join(descriptions)
    
    def _get_react_prompt(self, query: str, steps: List[AgentStep]) -> str:
        """Build the ReAct prompt with history."""
        
        prompt = f"""You are a financial analyst assistant. Answer the question by thinking step-by-step and using tools when needed.

Available Tools:
{self.tool_descriptions}

Question: {query}

Instructions:
1. Think about what information you need
2. Use tools to gather information
3. When you have enough information, provide the final answer

Format your response EXACTLY like this:
Thought: [your reasoning about what to do next]
Action: [tool_name]
Action Input: {{"param": "value"}}

OR when you have the final answer:
Thought: [your final reasoning]
Final Answer: [your complete answer]

"""
        # Add previous steps
        for step in steps:
            prompt += f"\nThought: {step.thought}\n"
            if step.action == AgentAction.FINAL_ANSWER:
                prompt += f"Final Answer: {step.observation}\n"
            elif step.action:
                prompt += f"Action: {step.action.value}\n"
                prompt += f"Action Input: {json.dumps(step.action_input)}\n"
                prompt += f"Observation: {step.observation}\n"
        
        return prompt
    
    def _parse_response(self, response: str) -> AgentStep:
        """Parse LLM response into an AgentStep."""
        
        # Extract thought
        thought_match = re.search(r"Thought:\s*(.+?)(?=\n(?:Action|Final Answer)|$)", 
                                   response, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else ""
        
        # Check for final answer
        final_match = re.search(r"Final Answer:\s*(.+)", response, re.DOTALL)
        if final_match:
            return AgentStep(
                thought=thought,
                action=AgentAction.FINAL_ANSWER,
                observation=final_match.group(1).strip()
            )
        
        # Extract action and input
        action_match = re.search(r"Action:\s*(\w+)", response)
        input_match = re.search(r"Action Input:\s*(\{.+?\})", response, re.DOTALL)
        
        if action_match:
            action_name = action_match.group(1).lower()
            action = AgentAction(action_name) if action_name in [a.value for a in AgentAction] else None
            
            action_input = {}
            if input_match:
                try:
                    action_input = json.loads(input_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            return AgentStep(thought=thought, action=action, action_input=action_input)
        
        # Fallback: treat as final answer
        return AgentStep(
            thought=thought,
            action=AgentAction.FINAL_ANSWER,
            observation=response
        )
    
    def _execute_tool(self, action: AgentAction, inputs: Dict[str, Any]) -> str:
        """Execute a tool and return the result."""
        
        tool_name = action.value
        if tool_name not in self.tools:
            return f"Error: Unknown tool '{tool_name}'"
        
        try:
            result = self.tools[tool_name](**inputs)
            
            # Handle different return types
            if isinstance(result, list):
                # Format list of documents
                if len(result) == 0:
                    return "No results found."
                formatted = []
                for i, item in enumerate(result[:3], 1):  # Limit to 3
                    if isinstance(item, tuple):
                        doc, meta = item
                        formatted.append(f"[{i}] (Page {meta.get('page', '?')}): {doc[:300]}...")
                    else:
                        formatted.append(f"[{i}]: {str(item)[:300]}...")
                return "\n".join(formatted)
            else:
                return str(result)[:1000]
                
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Error executing {tool_name}: {str(e)}"
    
    def run(self, query: str, context: Optional[str] = None) -> tuple[str, List[AgentStep]]:
        """
        Run the ReAct loop to answer a question.
        
        Args:
            query: The question to answer
            context: Optional additional context
            
        Returns:
            (final_answer, list_of_steps)
        """
        steps: List[AgentStep] = []
        
        if context:
            query = f"{query}\n\nAdditional Context:\n{context}"
        
        for i in range(self.max_steps):
            # Generate next step
            prompt = self._get_react_prompt(query, steps)
            response = self.llm.chat([{"role": "user", "content": prompt}])
            
            # Parse response
            step = self._parse_response(response)
            
            # If final answer, we're done
            if step.action == AgentAction.FINAL_ANSWER:
                steps.append(step)
                logger.info(f"Agent completed in {i+1} steps")
                return step.observation, steps
            
            # Execute tool if action specified
            if step.action and step.action_input:
                observation = self._execute_tool(step.action, step.action_input)
                step.observation = observation
            
            steps.append(step)
            logger.info(f"Step {i+1}: {step.action} -> {step.observation[:100] if step.observation else 'None'}...")
        
        # Max steps reached, force answer
        final_prompt = self._get_react_prompt(query, steps) + "\nYou must now provide a Final Answer based on what you've learned."
        response = self.llm.chat([{"role": "user", "content": final_prompt}])
        final_step = self._parse_response(response)
        steps.append(final_step)
        
        return final_step.observation or "Unable to determine answer.", steps


def create_credit_memo_agent(rag_pipeline) -> ReActAgent:
    """
    Factory function to create a ReAct agent for credit memo generation.
    
    Example:
        rag = RAGPipelineCosine(...)
        agent = create_credit_memo_agent(rag)
        answer, steps = agent.run("What are the key financial risks?")
    """
    
    # Define tools using the RAG pipeline
    def retrieve_tool(query: str, k: int = 5):
        return rag_pipeline.retrieve(query, n_results=k)
    
    def web_search_tool(query: str):
        try:
            from resources.tools.web_search import web_search
            return web_search(query)
        except ImportError:
            return "Web search not available"
    
    return ReActAgent(
        llm=rag_pipeline.llm,
        tools={
            "retrieve": retrieve_tool,
            "web_search": web_search_tool
        }
    )
