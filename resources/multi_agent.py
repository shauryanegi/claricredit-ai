"""
Multi-Agent System for Credit Memo Generation
==============================================

🎯 WHY MULTIPLE AGENTS?
- Specialization: Each agent is an expert in their domain
- Parallel: Agents work simultaneously  
- Quality: Specialist > generalist
- Connects to interviewer's multi-agent RL background!
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class AgentRole(Enum):
    FINANCIAL_ANALYST = "financial_analyst"
    RISK_ANALYST = "risk_analyst"
    COMPLIANCE_REVIEWER = "compliance_reviewer"
    ORCHESTRATOR = "orchestrator"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    from_agent: AgentRole
    to_agent: AgentRole
    content: str
    metadata: Dict[str, Any] = None


class SpecializedAgent:
    """A specialized agent that uses MCP tools."""
    
    SYSTEM_PROMPTS = {
        AgentRole.FINANCIAL_ANALYST: """You are an expert Financial Analyst. 
Extract and analyze: revenue, EBITDA, margins, balance sheet metrics.
ALWAYS cite page numbers. NEVER make up values.""",

        AgentRole.RISK_ANALYST: """You are an expert Risk Analyst.
Identify: financial, operational, market risks. Provide SWOT analysis.
Be balanced - highlight both risks AND mitigants.""",

        AgentRole.COMPLIANCE_REVIEWER: """You are a Compliance Reviewer.
Assess: collateral adequacy, loan terms, regulatory concerns.
Flag any missing information or compliance gaps.""",

        AgentRole.ORCHESTRATOR: """You are the Lead Credit Analyst.
Synthesize all specialist inputs. Write Executive Summary.
Provide clear Recommendation: Approve, Conditional, or Decline."""
    }
    
    def __init__(self, role: AgentRole, llm, mcp_server):
        self.role = role
        self.llm = llm
        self.mcp_server = mcp_server
        self.system_prompt = self.SYSTEM_PROMPTS[role]
    
    async def process(self, task: str, context: Optional[str] = None) -> str:
        """Process a task using MCP tools."""
        prompt = f"{self.system_prompt}\n\nTask: {task}"
        if context:
            prompt = f"Context from other analysts:\n{context}\n\n{prompt}"
        
        # Simple generation (extend with ReAct loop for tool use)
        return self.llm.chat([
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ])


class MultiAgentOrchestrator:
    """Coordinates multiple agents via shared MCP tools."""
    
    def __init__(self, llm, mcp_server):
        self.agents = {
            role: SpecializedAgent(role, llm, mcp_server)
            for role in AgentRole
        }
    
    async def generate_credit_memo(self, context: str) -> Dict[str, str]:
        """Generate memo using parallel specialized agents."""
        
        # Phase 1: Parallel specialist analysis
        tasks = {
            AgentRole.FINANCIAL_ANALYST: "Analyze financial statements and ratios.",
            AgentRole.RISK_ANALYST: "Identify risks and provide SWOT analysis.",
            AgentRole.COMPLIANCE_REVIEWER: "Review collateral and compliance."
        }
        
        results = await asyncio.gather(*[
            self.agents[role].process(task, context)
            for role, task in tasks.items()
        ])
        
        specialist_outputs = dict(zip(tasks.keys(), results))
        
        # Phase 2: Orchestrator synthesis
        combined = "\n\n".join([
            f"=== {role.value} ===\n{content}"
            for role, content in specialist_outputs.items()
        ])
        
        summary = await self.agents[AgentRole.ORCHESTRATOR].process(
            "Write Executive Summary and Recommendation", combined
        )
        
        return {**{r.value: c for r, c in specialist_outputs.items()}, 
                "summary": summary}


def create_multi_agent_system(llm, mcp_server):
    """Factory function to create multi-agent system."""
    return MultiAgentOrchestrator(llm, mcp_server)
