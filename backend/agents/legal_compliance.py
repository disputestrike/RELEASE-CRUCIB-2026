"""
Legal / AUP compliance: block prohibited build requests before orchestration runs.
Aligned with OpenAI, Anthropic, and Vercel usage policies and common law (US/EU).
See docs/LEGAL_COMPLIANCE_AND_INDUSTRY_ALIGNMENT.md for comparison.
"""

import logging
from typing import Dict, Any
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Prohibited keywords (lowercase) -> category for blocking and logging.
# Anthropic
PROHIBITED_KEYWORDS: Dict[str, list] = {
    "illegal": [
        "drug marketplace",
        "sell drugs",
        "buy drugs",
        "dark web market",
        "bomb making",
        "weapon sales",
        "assassination",
        "malware",
        "ransomware",
        "phishing",
        "credit card fraud",
        "identity theft",
        "ponzi scheme",
        "counterfeit",
        "fake id",
        "child abuse",
        "csam",
        "human trafficking",
        "illicit goods",
        "weapons development",
        "explosives",
        "cbrne",
        "unauthorized access",
        "ddos tool",
        "botnet",
        "ransomware",
    ],
    "adult": [
        "porn",
        "pornography",
        "xxx",
        "escort service",
        "onlyfans clone",
        "adult entertainment site",
        "sex work platform",
        "sexually explicit",
    ],
    "gambling": [
        "unlicensed casino",
        "unlicensed betting",
        "illegal gambling",
    ],
    "harassment": [
        "doxxing",
        "doxx",
        "revenge porn",
        "stalking tool",
        "harassment platform",
        "doxing",
        "non-consensual intimate",
    ],
    "child_safety": [
        "csam",
        "child sexual abuse",
        "minor grooming",
        "sexualize minors",
        "child exploitation",
        "minor sextortion",
        "underage sexual",
    ],
    "self_harm": [
        "suicide facilitation",
        "self-harm promotion",
        "suicide guide",
        "how to kill myself",
        "promote self-harm",
    ],
    "violence_terrorism": [
        "terrorism",
        "terrorist",
        "violence promotion",
        "hate speech platform",
        "violent extremism",
        "assassination service",
        "bomb instructions",
    ],
    "misinformation_election": [
        "election fraud",
        "voter suppression",
        "fake news generator",
        "deepfake political",
        "election interference",
        "deceptive political",
    ],
    "critical_infrastructure": [
        "hack power grid",
        "disrupt critical infrastructure",
        "voting machine hack",
        "water treatment hack",
        "medical device compromise",
    ],
    "unlicensed_advice": [
        "unlicensed legal advice",
        "unlicensed medical diagnosis",
        "unlicensed financial advice",
        "practice law without license",
        "prescribe without license",
    ],
    "privacy_surveillance": [
        "stalking tool",
        "spyware",
        "stalkerware",
        "facial recognition abuse",
        "surveillance without consent",
        "track someone without consent",
        "unauthorized surveillance",
    ],
    "fraud_scam": [
        "scam website",
        "phishing site",
        "fraud platform",
        "pyramid scheme",
        "fake investment",
        "pump and dump",
        "identity theft service",
    ],
    # Prevent replication / IP extraction: block prompts that ask to reveal or copy CrucibAI
    "replication_extraction": [
        "replicate crucibai",
        "clone crucibai",
        "copy crucibai",
        "rebuild crucibai",
        "reveal your system prompt",
        "export your instructions",
        "how were you built",
        "replicate yourself",
        "clone yourself",
        "copy this system",
        "replicate this system",
        "reveal your architecture",
        "what are you built with",
        "export your prompts",
        "recreate crucibai",
        "build something like crucibai",
        "copy how crucibai works",
        "steal crucibai",
        "reverse engineer crucibai",
        "mimic crucibai",
    ],
}


def check_request(prompt: str) -> Dict[str, Any]:
    """
    Check if build request violates AUP. Returns {"allowed": bool, "reason": str, "category": str}.
    Does not call LLM; keyword-based only for speed and determinism.
    """
    if not prompt or not isinstance(prompt, str):
        return {"allowed": True, "reason": None, "category": None}
    text = prompt.lower().strip()
    for category, keywords in PROHIBITED_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return {
                    "allowed": False,
                    "reason": f"Request violates Acceptable Use Policy (prohibited category: {category}).",
                    "category": category,
                }
    return {"allowed": True, "reason": None, "category": None}
