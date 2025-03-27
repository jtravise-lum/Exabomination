"""Prompt templates for the LLM integration."""

import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)


class PromptTemplates:
    """Manages prompt templates for different types of queries."""
    
    def __init__(self):
        """Initialize the prompt templates."""
        # System prompt template
        self.system_prompt_template = """You are EXASPERATION (Exabeam Automated Search Assistant Preventing Exasperating Research And Time-wasting In Official Notes), an AI assistant for Exabeam security documentation.

Your role:
- Answer questions based on provided documentation
- Provide specific, factual information about Exabeam products, features, and security concepts
- Cite sources to support your answers
- Stay within the provided context and acknowledge if information is missing
- Focus on clarity, accuracy, and technical precision

Guidelines:
1. Only use information from the provided context
2. Cite the source of information when providing an answer
3. If the context doesn't contain the answer, acknowledge the limitation
4. Do not make up information or hallucinate facts
5. When recommending configurations or settings, reference the documentation source
6. For technical questions, provide code examples or specific settings from the documentation
7. Maintain a helpful, technically accurate tone

IMPORTANT: If you're uncertain about an answer, state your uncertainty and what would be needed to provide a complete response.
"""

        # Query prompt template
        self.query_prompt_template = """
I'll provide you with a question about Exabeam security products and relevant context from the Exabeam documentation.
Answer based ONLY on the context provided. If the answer isn't in the context, say so.

USER QUERY: {query}

CONTEXT:
{context}

Based solely on the context above, provide a clear, concise answer to the query.
Be specific and cite document sources (Document X) for key information.
If the answer isn't in the context, acknowledge the limitation rather than guessing.
"""

        # Technical query prompt template (more emphasis on technical details)
        self.technical_prompt_template = """
I'll provide you with a technical question about Exabeam security configuration or implementation, along with relevant context from the Exabeam documentation.
Answer based ONLY on the context provided. If the answer isn't in the context, say so.

TECHNICAL QUERY: {query}

TECHNICAL CONTEXT:
{context}

Based solely on the context above, provide a detailed technical answer to the query.
Include specific settings, parameters, and configuration details from the documentation.
Use structured formats like code blocks or tables if applicable.
Cite document sources (Document X) for all technical information.
If the answer isn't in the context, acknowledge the limitation rather than guessing.
"""

        # MITRE ATT&CK query prompt template
        self.mitre_prompt_template = """
I'll provide you with a question about MITRE ATT&CK techniques in relation to Exabeam, along with relevant context from the Exabeam documentation.
Answer based ONLY on the context provided. If the answer isn't in the context, say so.

MITRE QUERY: {query}

CONTEXT:
{context}

Based solely on the context above, provide a clear answer about the MITRE ATT&CK technique and how Exabeam helps detect or respond to it.
Include relevant technique IDs (e.g., T1078), tactics, and specific Exabeam capabilities mentioned in the context.
Cite document sources (Document X) for all information.
If the answer isn't in the context, acknowledge the limitation rather than guessing.
"""

    def get_system_prompt(self) -> str:
        """Get the system prompt template.
        
        Returns:
            System prompt template string
        """
        return self.system_prompt_template
    
    def get_query_prompt(self, query: str, context: str) -> str:
        """Format the query prompt template.
        
        Args:
            query: User query
            context: Retrieved context from documents
            
        Returns:
            Formatted query prompt
        """
        return self.query_prompt_template.format(query=query, context=context)
    
    def get_technical_prompt(self, query: str, context: str) -> str:
        """Format the technical query prompt template.
        
        Args:
            query: User technical query
            context: Retrieved context from documents
            
        Returns:
            Formatted technical prompt
        """
        return self.technical_prompt_template.format(query=query, context=context)
    
    def get_mitre_prompt(self, query: str, context: str) -> str:
        """Format the MITRE ATT&CK query prompt template.
        
        Args:
            query: User query about MITRE ATT&CK
            context: Retrieved context from documents
            
        Returns:
            Formatted MITRE prompt
        """
        return self.mitre_prompt_template.format(query=query, context=context)
    
    def determine_prompt_type(self, query: str) -> str:
        """Determine the appropriate prompt type based on the query content.
        
        Args:
            query: User query
            
        Returns:
            Prompt type: "standard", "technical", or "mitre"
        """
        query_lower = query.lower()
        
        # Check for MITRE ATT&CK indicators
        if any(term in query_lower for term in ["mitre", "att&ck", "technique", "tactics", "t1"]):
            return "mitre"
            
        # Check for technical query indicators
        if any(term in query_lower for term in [
            "config", "configuration", "setting", "parameter", "implementation",
            "parser", "field", "how to", "setup", "code", "rule", "syntax"
        ]):
            return "technical"
            
        # Default to standard query
        return "standard"
    
    def format_prompt(self, query: str, context: str) -> Dict[str, str]:
        """Format the appropriate prompt based on the query type.
        
        Args:
            query: User query
            context: Retrieved context from documents
            
        Returns:
            Dictionary with system_prompt and user_prompt
        """
        prompt_type = self.determine_prompt_type(query)
        
        if prompt_type == "technical":
            user_prompt = self.get_technical_prompt(query, context)
        elif prompt_type == "mitre":
            user_prompt = self.get_mitre_prompt(query, context)
        else:
            user_prompt = self.get_query_prompt(query, context)
            
        return {
            "system_prompt": self.get_system_prompt(),
            "user_prompt": user_prompt
        }