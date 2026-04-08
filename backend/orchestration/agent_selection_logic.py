"""Intelligent swarm agent selection for complex CrucibAI builds.

This module narrows the full AGENT_DAG to the agents that matter for a goal,
then expands the set to include all required dependencies so execution stays
honest and complete.
"""
from __future__ import annotations

from typing import Dict, List, Set

from agent_dag import AGENT_DAG, get_execution_phases


BASE_AGENTS = [
    "Planner",
    "Requirements Clarifier",
    "Stack Selector",
    "Frontend Generation",
    "Backend Generation",
    "Database Agent",
    "File Tool Agent",
]


AGENT_KEYWORDS = {
    # 3D / rendering
    "3d": ["3D Engine Selector Agent", "3D Model Agent", "3D Scene Agent", "3D Interaction Agent"],
    "webgl": ["3D Engine Selector Agent", "WebGL Shader Agent", "3D Performance Agent"],
    "three.js": ["3D Engine Selector Agent", "3D Model Agent", "3D Scene Agent", "3D Physics Agent"],
    "babylon": ["3D Engine Selector Agent", "3D Model Agent", "3D Physics Agent"],
    "cesium": ["3D Engine Selector Agent", "3D Scene Agent"],
    "canvas": ["Canvas/SVG Rendering Agent"],
    "svg": ["Canvas/SVG Rendering Agent"],
    "ar": ["3D AR/VR Agent"],
    "vr": ["3D AR/VR Agent"],
    "augmented reality": ["3D AR/VR Agent"],
    "virtual reality": ["3D AR/VR Agent"],

    # ML / AI
    "ml": ["ML Framework Selector Agent", "ML Data Pipeline Agent", "ML Model Definition Agent", "ML Training Agent", "ML Evaluation Agent"],
    "machine learning": ["ML Framework Selector Agent", "ML Data Pipeline Agent", "ML Model Definition Agent", "ML Training Agent", "ML Evaluation Agent"],
    "tensorflow": ["ML Framework Selector Agent", "ML Model Definition Agent", "ML Training Agent", "ML Model Export Agent"],
    "pytorch": ["ML Framework Selector Agent", "ML Model Definition Agent", "ML Training Agent"],
    "sklearn": ["ML Framework Selector Agent", "ML Data Pipeline Agent", "ML Preprocessing Agent"],
    "scikit-learn": ["ML Framework Selector Agent", "ML Data Pipeline Agent", "ML Preprocessing Agent"],
    "xgboost": ["ML Framework Selector Agent", "ML Data Pipeline Agent", "ML Training Agent"],
    "neural network": ["ML Model Definition Agent", "ML Training Agent"],
    "deep learning": ["ML Model Definition Agent", "ML Training Agent", "ML Explainability Agent"],
    "prediction": ["ML Model Definition Agent", "ML Training Agent", "ML Evaluation Agent"],
    "model": ["ML Model Definition Agent", "ML Training Agent", "ML Model Export Agent", "ML Model Monitoring Agent"],
    "feature engineering": ["ML Data Pipeline Agent", "ML Preprocessing Agent"],
    "embedding": ["Embeddings/Vectorization Agent"],
    "vector": ["Embeddings/Vectorization Agent"],
    "recommendation": ["Recommendation Engine Agent", "Embeddings/Vectorization Agent"],
    "sentiment analysis": ["ML Training Agent", "ML Explainability Agent"],
    "nlp": ["ML Model Definition Agent", "Embeddings/Vectorization Agent"],
    "computer vision": ["ML Model Definition Agent", "ML Training Agent"],
    "classification": ["ML Model Definition Agent", "ML Evaluation Agent"],
    "regression": ["ML Model Definition Agent", "ML Evaluation Agent"],
    "clustering": ["ML Data Pipeline Agent", "ML Training Agent"],
    "forecast": ["Time Series Forecasting Agent"],
    "time series": ["Time Series Forecasting Agent"],

    # Blockchain / Web3
    "blockchain": ["Blockchain Selector Agent", "Smart Contract Agent", "Contract Testing Agent"],
    "smart contract": ["Smart Contract Agent", "Contract Testing Agent", "Contract Deployment Agent"],
    "ethereum": ["Blockchain Selector Agent", "Smart Contract Agent", "Web3 Frontend Agent"],
    "solidity": ["Smart Contract Agent", "Contract Testing Agent"],
    "web3": ["Web3 Frontend Agent", "Blockchain Data Agent", "DeFi Integration Agent"],
    "crypto": ["Blockchain Selector Agent", "Smart Contract Agent", "Web3 Frontend Agent"],
    "defi": ["DeFi Integration Agent", "Smart Contract Agent", "Web3 Frontend Agent"],
    "nft": ["Smart Contract Agent", "Web3 Frontend Agent"],
    "token": ["Smart Contract Agent", "Web3 Frontend Agent"],
    "wallet": ["Web3 Frontend Agent", "Blockchain Data Agent"],
    "dapp": ["Web3 Frontend Agent", "Smart Contract Agent", "Contract Deployment Agent"],
    "polygon": ["Blockchain Selector Agent", "Smart Contract Agent"],
    "solana": ["Blockchain Selector Agent", "Smart Contract Agent"],

    # IoT / hardware
    "iot": ["IoT Platform Selector Agent", "Microcontroller Firmware Agent", "IoT Communication Agent", "IoT Cloud Backend Agent"],
    "arduino": ["IoT Platform Selector Agent", "Microcontroller Firmware Agent", "IoT Sensor Agent"],
    "raspberry pi": ["IoT Platform Selector Agent", "Microcontroller Firmware Agent"],
    "sensor": ["IoT Sensor Agent", "IoT Data Pipeline Agent"],
    "device": ["IoT Platform Selector Agent", "Microcontroller Firmware Agent", "IoT Cloud Backend Agent"],
    "mqtt": ["IoT Communication Agent"],
    "ble": ["IoT Communication Agent", "IoT Mobile App Agent"],
    "bluetooth": ["IoT Communication Agent", "IoT Mobile App Agent"],
    "lora": ["IoT Communication Agent"],
    "firmware": ["Microcontroller Firmware Agent", "IoT Security Agent"],
    "edge": ["Edge Computing Agent", "Edge Deployment Agent"],
    "embedded": ["Microcontroller Firmware Agent", "IoT Sensor Agent"],

    # Data / analytics
    "data": ["ML Data Pipeline Agent", "Data Quality Agent", "Data Visualization Agent"],
    "analytics": ["Data Visualization Agent", "Statistical Analysis Agent", "Jupyter Notebook Agent"],
    "jupyter": ["Jupyter Notebook Agent"],
    "notebook": ["Jupyter Notebook Agent"],
    "statistical": ["Statistical Analysis Agent"],
    "visualization": ["Data Visualization Agent", "3D Model Agent", "3D Scene Agent", "3D Interaction Agent"],
    "dashboard": ["Data Visualization Agent", "IoT Dashboard Agent"],
    "report": ["Report Generation Agent", "Data Visualization Agent"],
    "eda": ["Jupyter Notebook Agent", "Statistical Analysis Agent"],
    "warehouse": ["Data Quality Agent", "Report Generation Agent", "Statistical Analysis Agent"],

    # Infrastructure / ops
    "kubernetes": ["Kubernetes Advanced Agent", "DevOps Agent"],
    "k8s": ["Kubernetes Advanced Agent", "DevOps Agent"],
    "serverless": ["Serverless Deployment Agent"],
    "lambda": ["Serverless Deployment Agent"],
    "cloudflare": ["Edge Deployment Agent"],
    "edge function": ["Edge Deployment Agent"],
    "istio": ["Kubernetes Advanced Agent"],
    "service mesh": ["Kubernetes Advanced Agent"],
    "docker": ["DevOps Agent"],
    "container": ["DevOps Agent"],
    "load balance": ["Load Balancer Agent"],
    "database optimization": ["Database Optimization Agent"],
    "kafka": ["Message Queue Advanced Agent"],
    "rabbitmq": ["Message Queue Advanced Agent"],
    "queue": ["Queue Agent", "Message Queue Advanced Agent"],
    "bullmq": ["Queue Agent", "Message Queue Advanced Agent"],
    "celery": ["Queue Agent", "Message Queue Advanced Agent"],
    "cache": ["Caching Agent", "Database Optimization Agent"],
    "redis": ["Caching Agent", "Database Optimization Agent"],
    "security": ["Network Security Agent", "Blockchain Security Agent", "IoT Security Agent", "Security Checker"],
    "firewall": ["Network Security Agent"],
    "vpc": ["Network Security Agent"],
    "disaster recovery": ["Disaster Recovery Agent"],
    "backup": ["Backup Agent", "Disaster Recovery Agent"],
    "deploy": ["Deployment Agent", "Deployment Tool Agent", "DevOps Agent"],
    "production": ["Deployment Agent", "Staging Agent"],
    "devops": ["DevOps Agent"],
    "ci/cd": ["DevOps Agent"],
    "monitoring": ["Monitoring Agent", "Metrics Agent", "Logging Agent"],
    "observability": ["Monitoring Agent", "Metrics Agent", "Logging Agent"],
    "metrics": ["Metrics Agent"],
    "logging": ["Logging Agent"],
    "tracing": ["Monitoring Agent"],
    "apm": ["Monitoring Agent"],

    # Testing
    "test": ["Test Generation", "Test Executor", "E2E Agent", "Load Test Agent"],
    "testing": ["Test Generation", "Test Executor", "E2E Agent", "Smoke Test Agent"],
    "unit test": ["Test Generation"],
    "e2e": ["E2E Agent"],
    "integration test": ["Test Generation", "Contract Testing Agent"],
    "load test": ["Load Test Agent", "Chaos Engineering Agent"],
    "chaos": ["Chaos Engineering Agent"],
    "property-based": ["Property-Based Testing Agent"],
    "mutation": ["Mutation Testing Agent"],
    "contract test": ["Contract Testing Agent"],
    "synthetic": ["Synthetic Monitoring Agent"],
    "smoke test": ["Smoke Test Agent"],

    # Business / enterprise
    "workflow": ["Workflow Engine Agent", "Workflow Agent"],
    "state machine": ["Workflow Engine Agent"],
    "approval": ["Approval Flow Agent"],
    "rules": ["Business Rules Engine Agent"],
    "business logic": ["Business Rules Engine Agent"],
    "scheduling": ["Scheduling Agent"],
    "calendar": ["Scheduling Agent"],
    "search": ["Search Relevance Agent", "Search Agent"],
    "notification": ["Notification Rules Agent", "Notification Agent"],
    "audit": ["Audit & Compliance Engine Agent", "Audit Trail Agent"],
    "compliance": ["Audit & Compliance Engine Agent", "Legal Compliance Agent"],
    "enterprise": ["Multi-tenant Agent", "RBAC Agent", "Approval Flow Agent", "Audit & Compliance Engine Agent"],
    "multi-tenant": ["Multi-tenant Agent", "RBAC Agent"],
    "multitenant": ["Multi-tenant Agent", "RBAC Agent"],
    "tenant isolation": ["Multi-tenant Agent", "RBAC Agent", "Audit Trail Agent"],
    "crm": ["Form Builder Agent", "Table Agent", "Search Agent", "Workflow Agent"],
    "quote": ["Approval Flow Agent", "Business Rules Engine Agent", "Form Builder Agent", "Audit Trail Agent"],
    "quotes": ["Approval Flow Agent", "Business Rules Engine Agent", "Form Builder Agent", "Audit Trail Agent"],
    "project": ["Workflow Agent", "Scheduling Agent", "Table Agent", "Notification Agent"],
    "projects": ["Workflow Agent", "Scheduling Agent", "Table Agent", "Notification Agent"],
    "policy": ["Business Rules Engine Agent", "Approval Flow Agent", "Audit & Compliance Engine Agent"],
    "operator": ["Table Agent", "Workflow Agent", "Notification Agent", "Audit Trail Agent"],
    "operators": ["Table Agent", "Workflow Agent", "Notification Agent", "Audit Trail Agent"],
    "background jobs": ["Queue Agent", "Workflow Engine Agent", "Notification Agent"],
    "worker/job system": ["Queue Agent", "Workflow Engine Agent"],

    # Design / UI
    "design": ["Design Agent", "Layout Agent", "UX Auditor", "Accessibility Agent"],
    "ui": ["Frontend Generation", "Design Agent", "Layout Agent"],
    "ux": ["UX Auditor", "Design Agent"],
    "styling": ["Design Agent", "Frontend Generation"],
    "css": ["Frontend Generation", "Design Agent", "Layout Agent"],
    "brand": ["Brand Agent", "Design Agent"],
    "dark mode": ["Dark Mode Agent", "Frontend Generation"],
    "animation": ["Animation Agent", "3D Animation Agent"],
    "responsive": ["Mobile Responsive Agent", "Frontend Generation"],
    "image": ["Image Generation", "Layout Agent"],
    "images": ["Image Generation", "Layout Agent"],
    "video": ["Video Generation"],

    # Security / auth
    "auth": ["Auth Setup Agent", "Security Checker"],
    "authentication": ["Auth Setup Agent", "Security Checker"],
    "oauth": ["OAuth Provider Agent"],
    "2fa": ["2FA Agent"],
    "password": ["Auth Setup Agent"],
    "encryption": ["Network Security Agent", "IoT Security Agent"],
    "rbac": ["RBAC Agent"],
    "permission": ["RBAC Agent"],

    # Payments / comms
    "payment": ["Payment Setup Agent", "Stripe Subscription Agent"],
    "stripe": ["Payment Setup Agent", "Stripe Subscription Agent"],
    "billing": ["Stripe Subscription Agent", "Invoice Agent"],
    "invoice": ["Invoice Agent"],
    "email": ["Email Agent", "Notification Agent"],
    "sendgrid": ["Email Agent", "Notification Agent"],
    "twilio": ["Notification Agent"],
    "websocket": ["WebSocket Agent"],
    "websockets": ["WebSocket Agent"],
    "realtime": ["WebSocket Agent"],
    "real-time": ["WebSocket Agent"],

    # Mobile
    "mobile": ["Native Config Agent", "Store Prep Agent", "Mobile Responsive Agent", "IoT Mobile App Agent"],
    "ios": ["Native Config Agent", "Store Prep Agent"],
    "android": ["Native Config Agent", "Store Prep Agent"],
    "react native": ["Native Config Agent"],
    "expo": ["Native Config Agent", "Store Prep Agent"],
    "flutter": ["Native Config Agent"],
    "app store": ["Store Prep Agent"],

    # Docs / content
    "documentation": ["Documentation Agent", "API Documentation Agent"],
    "docs": ["Documentation Agent", "API Documentation Agent"],
    "api": ["API Documentation Agent", "API Integration", "API Tool Agent"],
    "content": ["Content Agent", "SEO Agent"],
    "seo": ["SEO Agent", "Content Agent"],
    "marketing": ["Content Agent", "SEO Agent"],
    "copy": ["Content Agent"],
}


def _dependency_closure(initial: Set[str]) -> Set[str]:
    selected = set(initial)
    queue = list(initial)
    while queue:
        name = queue.pop()
        for dep in AGENT_DAG.get(name, {}).get("depends_on", []):
            if dep in AGENT_DAG and dep not in selected:
                selected.add(dep)
                queue.append(dep)
    return selected


def select_agents_for_goal(goal: str, stack_contract: Dict | None = None) -> List[str]:
    selected: Set[str] = set(BASE_AGENTS)
    goal_lower = (goal or "").lower()
    contract = stack_contract or {}

    for keyword, agents in AGENT_KEYWORDS.items():
        if keyword in goal_lower:
            selected.update(a for a in agents if a in AGENT_DAG)

    if contract.get("mobile"):
        selected.update(a for a in ("Native Config Agent", "Store Prep Agent", "Mobile Responsive Agent") if a in AGENT_DAG)

    if contract.get("requires_full_system_builder"):
        selected.update(a for a in ("File Tool Agent", "Code Review Agent", "Security Checker", "UX Auditor", "Performance Analyzer", "Deployment Agent", "Memory Agent") if a in AGENT_DAG)

    if contract.get("queues"):
        selected.update(a for a in ("Queue Agent", "Message Queue Advanced Agent") if a in AGENT_DAG)
    if contract.get("caches"):
        selected.update(a for a in ("Caching Agent", "Database Optimization Agent") if a in AGENT_DAG)
    if contract.get("payments"):
        selected.update(a for a in ("Payment Setup Agent", "Stripe Subscription Agent") if a in AGENT_DAG)
    if contract.get("realtime"):
        selected.update(a for a in ("WebSocket Agent",) if a in AGENT_DAG)
    if contract.get("vector_databases"):
        selected.update(a for a in ("Embeddings/Vectorization Agent", "Recommendation Engine Agent") if a in AGENT_DAG)

    if any(word in goal_lower for word in ("design", "landing", "website", "ui", "ux")):
        selected.update(a for a in ("Design Agent", "Layout Agent", "Brand Agent", "UX Auditor", "Dark Mode Agent", "Animation Agent") if a in AGENT_DAG)

    if any(word in goal_lower for word in ("content", "seo", "marketing", "landing", "blog")):
        selected.update(a for a in ("Content Agent", "SEO Agent", "Image Generation") if a in AGENT_DAG)

    if any(word in goal_lower for word in ("enterprise", "compliance", "hipaa", "soc2", "gdpr")):
        selected.update(a for a in ("Legal Compliance Agent", "Audit Trail Agent", "Audit & Compliance Engine Agent", "Multi-tenant Agent", "RBAC Agent") if a in AGENT_DAG)

    if any(word in goal_lower for word in ("scale", "kubernetes", "microservice", "distributed", "high-availability")):
        selected.update(a for a in ("Kubernetes Advanced Agent", "Load Balancer Agent", "Message Queue Advanced Agent", "Database Optimization Agent", "Disaster Recovery Agent", "Monitoring Agent") if a in AGENT_DAG)

    if any(word in goal_lower for word in ("data", "analytics", "bigdata", "warehouse")):
        selected.update(a for a in ("Data Quality Agent", "Data Visualization Agent", "Report Generation Agent", "Statistical Analysis Agent") if a in AGENT_DAG)

    selected.update(a for a in ("Code Review Agent", "Security Checker", "UX Auditor", "Performance Analyzer", "Deployment Agent", "Memory Agent") if a in AGENT_DAG)
    selected = _dependency_closure(selected)
    return sorted(selected)


def build_full_phases_from_dag(selected_agents: List[str], agent_dag: Dict) -> List[List[str]]:
    filtered_dag = {name: config for name, config in agent_dag.items() if name in set(selected_agents)}
    return get_execution_phases(filtered_dag)
