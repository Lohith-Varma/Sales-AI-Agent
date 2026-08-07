import logging
from typing import Optional, List, Dict, Any
from app.voice_pipeline.interfaces import LLMProvider

logger = logging.getLogger(__name__)

# Hardcoded knowledge base for affordability Pay-in-3 product
MOCK_KNOWLEDGE_BASE = [
    {
        "keywords": ["pay-in-3", "zero-cost", "emi", "affordability", "product"],
        "answer": "Our Pay-in-3 Zero-cost EMI product allows you to split your purchase into 3 equal monthly installments with 0% interest and 0 processing fees, available for orders above INR 3,000.",
        "source": "product_terms.md",
        "section": "pay-in-3-overview",
        "citation": "product_terms.md:L1-12:pay-in-3-overview"
    },
    {
        "keywords": ["document", "kyc", "aadhaar", "pan", "verify", "verification"],
        "answer": "For instant KYC verification, you will need to share your PAN card and Aadhaar card details. The Aadhaar card must be linked to your active mobile number to complete the e-Sign OTP step.",
        "source": "compliance_kyc.md",
        "section": "kyc-requirements",
        "citation": "compliance_kyc.md:L14-25:kyc-requirements"
    },
    {
        "keywords": ["late", "miss", "fee", "charge", "interest", "penalty"],
        "answer": "If you miss an EMI payment, a late fee of 2% per month will be charged on the outstanding amount. However, there are zero interest fees or processing charges if paid on time.",
        "source": "fee_schedule.md",
        "section": "late-payments",
        "citation": "fee_schedule.md:L8-15:late-payments"
    },
    {
        "keywords": ["apply", "start", "process", "begin", "eligibility"],
        "answer": "I can help start your application right now. I will just need to ask a few quick questions about your monthly income, date of birth, and employment type.",
        "source": "application_guide.md",
        "section": "process-flow",
        "citation": "application_guide.md:L4-18:process-flow"
    }
]

class MockLLMProvider(LLMProvider):
    """Simulates RAG-based response generation by querying a mock knowledge base."""

    async def generate_response(
        self,
        prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        context_citations: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Scans the customer prompt for key terms, matches it with mock KB, and returns cited responses.
        If no match, flags the output for human escalation.
        """
        query = prompt.lower()
        
        # Check for keyword matches
        for entry in MOCK_KNOWLEDGE_BASE:
            for kw in entry["keywords"]:
                if kw in query:
                    logger.info(f"Mock LLM: matched keyword '{kw}', returning grounded response.")
                    return {
                        "text": entry["answer"],
                        "citations": [entry["citation"]],
                        "confidence": 0.95,
                        "escalate": False
                    }
        
        # Fallback escalation if we don't have a grounded answer in our mock FAQ
        logger.info("Mock LLM: No matching FAQ, generating escalation response.")
        return {
            "text": "I understand you have a specific question. Let me connect you directly to our sales agent to assist with credit approval terms.",
            "citations": ["fallback_policy.md:L2-5:escalation-handling"],
            "confidence": 0.60,
            "escalate": True
        }
