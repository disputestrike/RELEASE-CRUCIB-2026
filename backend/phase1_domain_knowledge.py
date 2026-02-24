"""
PHASE 1: ENHANCED KNOWLEDGE - Domain Expertise Injection System
Implements domain-specific knowledge bases for medical, legal, financial, physics, etc.
Enables CrucibAI to understand domain constraints and best practices deeply.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

logger = logging.getLogger(__name__)


class DomainType(Enum):
    """Supported domain types"""
    MEDICAL = "medical"
    LEGAL = "legal"
    FINANCIAL = "financial"
    PHYSICS = "physics"
    ENGINEERING = "engineering"
    COMPLIANCE = "compliance"
    SECURITY = "security"
    GENERAL = "general"


@dataclass
class DomainRule:
    """Represents a domain-specific rule or constraint"""
    rule_id: str
    domain: str
    category: str
    rule_text: str
    severity: str  # "critical", "high", "medium", "low"
    applicable_contexts: List[str]
    exceptions: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "domain": self.domain,
            "category": self.category,
            "rule_text": self.rule_text,
            "severity": self.severity,
            "applicable_contexts": self.applicable_contexts,
            "exceptions": self.exceptions,
            "references": self.references,
            "created_at": self.created_at
        }


@dataclass
class DomainOntology:
    """Domain-specific ontology defining concepts and relationships"""
    domain: str
    concepts: Dict[str, Dict[str, Any]]
    relationships: Dict[str, List[str]]
    hierarchies: Dict[str, List[str]]
    constraints: List[DomainRule]
    version: str = "1.0"
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "concepts": self.concepts,
            "relationships": self.relationships,
            "hierarchies": self.hierarchies,
            "constraints": [c.to_dict() for c in self.constraints],
            "version": self.version,
            "last_updated": self.last_updated
        }


class DomainKnowledgeBase:
    """
    Manages domain-specific knowledge bases for CrucibAI.
    Enables deep understanding of domain constraints and best practices.
    """
    
    def __init__(self, db):
        self.db = db
        self.domains: Dict[str, DomainOntology] = {}
        self.rules_cache: Dict[str, List[DomainRule]] = {}
        self.expert_systems: Dict[str, Any] = {}
    
    async def initialize_domains(self):
        """Initialize all domain knowledge bases"""
        logger.info("Initializing domain knowledge bases...")
        
        await self._init_medical_domain()
        await self._init_legal_domain()
        await self._init_financial_domain()
        await self._init_physics_domain()
        await self._init_engineering_domain()
        await self._init_compliance_domain()
        await self._init_security_domain()
        
        logger.info("Domain knowledge bases initialized successfully")
    
    async def _init_medical_domain(self):
        """Initialize medical domain knowledge"""
        concepts = {
            "patient": {
                "definition": "Individual receiving medical care",
                "properties": ["age", "medical_history", "allergies", "current_medications"],
                "related_concepts": ["disease", "treatment", "diagnosis"]
            },
            "diagnosis": {
                "definition": "Identification of disease or condition",
                "properties": ["icd_code", "severity", "confidence", "date"],
                "related_concepts": ["disease", "symptoms", "treatment"]
            },
            "treatment": {
                "definition": "Medical intervention to address disease",
                "properties": ["drug_name", "dosage", "frequency", "duration", "side_effects"],
                "related_concepts": ["medication", "therapy", "procedure"]
            },
            "medication": {
                "definition": "Pharmaceutical substance for treatment",
                "properties": ["generic_name", "brand_name", "fda_approval", "contraindications"],
                "related_concepts": ["drug_interaction", "dosage", "side_effect"]
            },
            "procedure": {
                "definition": "Medical intervention (surgical or non-surgical)",
                "properties": ["procedure_code", "risk_level", "recovery_time", "success_rate"],
                "related_concepts": ["surgery", "anesthesia", "complication"]
            }
        }
        
        rules = [
            DomainRule(
                rule_id="med_001",
                domain="medical",
                category="patient_privacy",
                rule_text="All patient data must comply with HIPAA regulations",
                severity="critical",
                applicable_contexts=["patient_records", "data_storage", "data_transmission"],
                references=["HIPAA_Title_II", "45_CFR_164"]
            ),
            DomainRule(
                rule_id="med_002",
                domain="medical",
                category="drug_safety",
                rule_text="Check for drug interactions before prescribing medications",
                severity="critical",
                applicable_contexts=["prescription", "medication_management"],
                references=["FDA_Guidelines", "PharmGKB"]
            ),
            DomainRule(
                rule_id="med_003",
                domain="medical",
                category="informed_consent",
                rule_text="Obtain informed consent before any procedure",
                severity="critical",
                applicable_contexts=["procedure", "surgery", "treatment"],
                references=["Medical_Ethics", "Common_Law"]
            ),
            DomainRule(
                rule_id="med_004",
                domain="medical",
                category="dosage",
                rule_text="Verify dosage against patient age, weight, and kidney/liver function",
                severity="high",
                applicable_contexts=["medication", "prescription"],
                references=["FDA_Dosage_Guidelines"]
            )
        ]
        
        ontology = DomainOntology(
            domain="medical",
            concepts=concepts,
            relationships={
                "patient": ["disease", "treatment", "diagnosis"],
                "diagnosis": ["disease", "symptoms", "treatment"],
                "treatment": ["medication", "procedure", "therapy"],
                "medication": ["drug_interaction", "side_effect", "dosage"]
            },
            hierarchies={
                "medical_intervention": ["medication", "procedure", "therapy"],
                "disease": ["acute", "chronic", "genetic"],
                "severity": ["critical", "high", "medium", "low"]
            },
            constraints=rules
        )
        
        self.domains["medical"] = ontology
        self.rules_cache["medical"] = rules
        logger.info("Medical domain initialized with 4 core rules")
    
    async def _init_legal_domain(self):
        """Initialize legal domain knowledge"""
        concepts = {
            "contract": {
                "definition": "Legally binding agreement between parties",
                "properties": ["parties", "terms", "conditions", "effective_date", "expiration_date"],
                "related_concepts": ["agreement", "liability", "indemnification"]
            },
            "compliance": {
                "definition": "Adherence to laws and regulations",
                "properties": ["jurisdiction", "regulations", "audit_trail"],
                "related_concepts": ["regulation", "legal_requirement", "enforcement"]
            },
            "liability": {
                "definition": "Legal responsibility for damages or harm",
                "properties": ["type", "limit", "insurance_coverage"],
                "related_concepts": ["indemnification", "negligence", "damages"]
            }
        }
        
        rules = [
            DomainRule(
                rule_id="legal_001",
                domain="legal",
                category="contract_validity",
                rule_text="All contracts must have clear terms, consideration, and mutual agreement",
                severity="critical",
                applicable_contexts=["contract_generation", "agreement"],
                references=["Contract_Law", "UCC"]
            ),
            DomainRule(
                rule_id="legal_002",
                domain="legal",
                category="liability_limitation",
                rule_text="Liability clauses must comply with local jurisdiction laws",
                severity="high",
                applicable_contexts=["contract", "terms_of_service"],
                references=["Tort_Law", "Product_Liability"]
            )
        ]
        
        ontology = DomainOntology(
            domain="legal",
            concepts=concepts,
            relationships={
                "contract": ["agreement", "liability", "compliance"],
                "compliance": ["regulation", "enforcement", "audit"]
            },
            hierarchies={
                "legal_document": ["contract", "agreement", "policy"],
                "jurisdiction": ["federal", "state", "local", "international"]
            },
            constraints=rules
        )
        
        self.domains["legal"] = ontology
        self.rules_cache["legal"] = rules
        logger.info("Legal domain initialized with 2 core rules")
    
    async def _init_financial_domain(self):
        """Initialize financial domain knowledge"""
        concepts = {
            "transaction": {
                "definition": "Exchange of financial value",
                "properties": ["amount", "currency", "date", "parties", "type"],
                "related_concepts": ["payment", "settlement", "reconciliation"]
            },
            "risk": {
                "definition": "Potential for financial loss",
                "properties": ["type", "probability", "impact", "mitigation"],
                "related_concepts": ["hedge", "insurance", "diversification"]
            },
            "compliance": {
                "definition": "Adherence to financial regulations",
                "properties": ["regulation", "reporting_requirement", "audit_trail"],
                "related_concepts": ["aml", "kyc", "sanctions"]
            }
        }
        
        rules = [
            DomainRule(
                rule_id="fin_001",
                domain="financial",
                category="aml_kyc",
                rule_text="Implement AML/KYC procedures for all customer transactions",
                severity="critical",
                applicable_contexts=["customer_onboarding", "transaction_monitoring"],
                references=["FinCEN", "FATF_Guidelines"]
            ),
            DomainRule(
                rule_id="fin_002",
                domain="financial",
                category="data_security",
                rule_text="Encrypt all financial data in transit and at rest",
                severity="critical",
                applicable_contexts=["data_storage", "transmission"],
                references=["PCI_DSS", "ISO_27001"]
            )
        ]
        
        ontology = DomainOntology(
            domain="financial",
            concepts=concepts,
            relationships={
                "transaction": ["payment", "settlement", "reconciliation"],
                "risk": ["hedge", "insurance", "diversification"]
            },
            hierarchies={
                "financial_instrument": ["equity", "debt", "derivative"],
                "risk_type": ["market_risk", "credit_risk", "operational_risk"]
            },
            constraints=rules
        )
        
        self.domains["financial"] = ontology
        self.rules_cache["financial"] = rules
        logger.info("Financial domain initialized with 2 core rules")
    
    async def _init_physics_domain(self):
        """Initialize physics domain knowledge"""
        concepts = {
            "force": {
                "definition": "Interaction that causes acceleration",
                "properties": ["magnitude", "direction", "type"],
                "related_concepts": ["acceleration", "momentum", "energy"]
            },
            "energy": {
                "definition": "Capacity to do work",
                "properties": ["type", "magnitude", "conservation"],
                "related_concepts": ["force", "work", "power"]
            },
            "field": {
                "definition": "Physical quantity assigned to every point in space",
                "properties": ["type", "magnitude", "gradient"],
                "related_concepts": ["force", "potential", "wave"]
            }
        }
        
        rules = [
            DomainRule(
                rule_id="phys_001",
                domain="physics",
                category="conservation_laws",
                rule_text="Energy and momentum must be conserved in all calculations",
                severity="critical",
                applicable_contexts=["simulation", "calculation"],
                references=["Newton_Laws", "Conservation_Laws"]
            ),
            DomainRule(
                rule_id="phys_002",
                domain="physics",
                category="unit_consistency",
                rule_text="All units must be consistent (SI or CGS)",
                severity="high",
                applicable_contexts=["calculation", "simulation"],
                references=["SI_Units", "NIST"]
            )
        ]
        
        ontology = DomainOntology(
            domain="physics",
            concepts=concepts,
            relationships={
                "force": ["acceleration", "momentum", "energy"],
                "energy": ["force", "work", "power"]
            },
            hierarchies={
                "force_type": ["gravitational", "electromagnetic", "nuclear"],
                "energy_type": ["kinetic", "potential", "thermal"]
            },
            constraints=rules
        )
        
        self.domains["physics"] = ontology
        self.rules_cache["physics"] = rules
        logger.info("Physics domain initialized with 2 core rules")
    
    async def _init_engineering_domain(self):
        """Initialize engineering domain knowledge"""
        concepts = {
            "system": {
                "definition": "Integrated set of components with defined purpose",
                "properties": ["components", "interfaces", "performance_metrics"],
                "related_concepts": ["subsystem", "component", "interface"]
            },
            "reliability": {
                "definition": "Probability of system functioning without failure",
                "properties": ["mtbf", "availability", "redundancy"],
                "related_concepts": ["failure_mode", "fault_tolerance"]
            }
        }
        
        rules = [
            DomainRule(
                rule_id="eng_001",
                domain="engineering",
                category="safety_factor",
                rule_text="Apply appropriate safety factors to all designs",
                severity="critical",
                applicable_contexts=["design", "calculation"],
                references=["ASME", "ISO_13849"]
            ),
            DomainRule(
                rule_id="eng_002",
                domain="engineering",
                category="testing",
                rule_text="Comprehensive testing required before deployment",
                severity="high",
                applicable_contexts=["deployment", "validation"],
                references=["IEEE_1012", "Testing_Standards"]
            )
        ]
        
        ontology = DomainOntology(
            domain="engineering",
            concepts=concepts,
            relationships={
                "system": ["subsystem", "component", "interface"]
            },
            hierarchies={
                "system_type": ["mechanical", "electrical", "software", "hybrid"]
            },
            constraints=rules
        )
        
        self.domains["engineering"] = ontology
        self.rules_cache["engineering"] = rules
        logger.info("Engineering domain initialized with 2 core rules")
    
    async def _init_compliance_domain(self):
        """Initialize compliance domain knowledge"""
        concepts = {
            "regulation": {
                "definition": "Legal requirement or rule",
                "properties": ["jurisdiction", "effective_date", "scope"],
                "related_concepts": ["compliance", "enforcement", "penalty"]
            }
        }
        
        rules = [
            DomainRule(
                rule_id="comp_001",
                domain="compliance",
                category="audit_trail",
                rule_text="Maintain complete audit trail of all system actions",
                severity="critical",
                applicable_contexts=["logging", "monitoring"],
                references=["SOX", "GDPR"]
            )
        ]
        
        ontology = DomainOntology(
            domain="compliance",
            concepts=concepts,
            relationships={},
            hierarchies={},
            constraints=rules
        )
        
        self.domains["compliance"] = ontology
        self.rules_cache["compliance"] = rules
        logger.info("Compliance domain initialized with 1 core rule")
    
    async def _init_security_domain(self):
        """Initialize security domain knowledge"""
        concepts = {
            "threat": {
                "definition": "Potential harm to system",
                "properties": ["type", "likelihood", "impact"],
                "related_concepts": ["vulnerability", "attack", "mitigation"]
            },
            "vulnerability": {
                "definition": "Weakness that can be exploited",
                "properties": ["cve_id", "severity", "patch_status"],
                "related_concepts": ["threat", "exploit", "mitigation"]
            }
        }
        
        rules = [
            DomainRule(
                rule_id="sec_001",
                domain="security",
                category="authentication",
                rule_text="Implement multi-factor authentication for all critical systems",
                severity="critical",
                applicable_contexts=["access_control", "authentication"],
                references=["NIST_800-63", "OWASP"]
            ),
            DomainRule(
                rule_id="sec_002",
                domain="security",
                category="encryption",
                rule_text="Use strong encryption (AES-256 or better) for sensitive data",
                severity="critical",
                applicable_contexts=["data_protection", "transmission"],
                references=["NIST_800-175B", "FIPS_140-2"]
            )
        ]
        
        ontology = DomainOntology(
            domain="security",
            concepts=concepts,
            relationships={
                "threat": ["vulnerability", "attack", "mitigation"],
                "vulnerability": ["threat", "exploit", "patch"]
            },
            hierarchies={
                "threat_type": ["external", "internal", "supply_chain"],
                "attack_type": ["malware", "phishing", "ddos", "injection"]
            },
            constraints=rules
        )
        
        self.domains["security"] = ontology
        self.rules_cache["security"] = rules
        logger.info("Security domain initialized with 2 core rules")
    
    def get_domain_rules(self, domain: str) -> List[DomainRule]:
        """Get all rules for a specific domain"""
        return self.rules_cache.get(domain, [])
    
    def get_domain_ontology(self, domain: str) -> Optional[DomainOntology]:
        """Get ontology for a specific domain"""
        return self.domains.get(domain)
    
    def validate_against_domain(self, domain: str, requirement: str) -> Dict[str, Any]:
        """
        Validate a requirement against domain rules.
        Returns violations and recommendations.
        """
        rules = self.get_domain_rules(domain)
        violations = []
        recommendations = []
        
        for rule in rules:
            if rule.severity == "critical":
                # Check if requirement violates this rule
                if not self._check_rule_compliance(requirement, rule):
                    violations.append({
                        "rule_id": rule.rule_id,
                        "rule_text": rule.rule_text,
                        "severity": rule.severity,
                        "references": rule.references
                    })
        
        return {
            "domain": domain,
            "requirement": requirement,
            "violations": violations,
            "recommendations": recommendations,
            "compliant": len(violations) == 0
        }
    
    def _check_rule_compliance(self, requirement: str, rule: DomainRule) -> bool:
        """Check if requirement complies with rule (simplified)"""
        # In production, this would use NLP/semantic analysis
        rule_keywords = rule.rule_text.lower().split()
        requirement_lower = requirement.lower()
        
        # Simple keyword matching
        return any(keyword in requirement_lower for keyword in rule_keywords)
    
    async def save_domain_knowledge(self):
        """Save domain knowledge to database"""
        for domain_name, ontology in self.domains.items():
            await self.db.insert_one(
                "domain_ontologies",
                {
                    "domain": domain_name,
                    "ontology": ontology.to_dict(),
                    "created_at": datetime.utcnow().isoformat()
                }
            )
        logger.info(f"Saved {len(self.domains)} domain ontologies to database")
    
    async def load_domain_knowledge(self):
        """Load domain knowledge from database"""
        ontologies = await self.db.find("domain_ontologies", {})
        for doc in ontologies:
            domain = doc.get("domain")
            ontology_data = doc.get("ontology")
            # Reconstruct ontology objects from stored data
            logger.info(f"Loaded domain knowledge for {domain}")


# Integration with Agent System
class DomainAwareAgent:
    """
    Base class for agents that are aware of domain constraints.
    """
    
    def __init__(self, agent_name: str, domain: str, knowledge_base: DomainKnowledgeBase):
        self.agent_name = agent_name
        self.domain = domain
        self.knowledge_base = knowledge_base
        self.domain_rules = knowledge_base.get_domain_rules(domain)
    
    async def validate_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """Validate output against domain rules"""
        validation_result = self.knowledge_base.validate_against_domain(
            self.domain,
            json.dumps(output)
        )
        
        if not validation_result["compliant"]:
            logger.warning(f"Domain violations detected: {validation_result['violations']}")
        
        return validation_result
    
    async def get_domain_context(self) -> Dict[str, Any]:
        """Get domain context for this agent"""
        ontology = self.knowledge_base.get_domain_ontology(self.domain)
        return {
            "domain": self.domain,
            "concepts": ontology.concepts if ontology else {},
            "rules": [r.to_dict() for r in self.domain_rules],
            "constraints": len(self.domain_rules)
        }


if __name__ == "__main__":
    print("Phase 1: Domain Knowledge Base System")
    print("Supports: Medical, Legal, Financial, Physics, Engineering, Compliance, Security")
