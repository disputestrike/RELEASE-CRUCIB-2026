import json
from pathlib import Path
from urllib import error, request


BASE = "https://crucibai-production.up.railway.app"
OUTPUT_DIR = Path("proof/agent_swarm_191_upgrade")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def call(method: str, path: str, payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(raw)
        except Exception:
            return exc.code, raw


def unwrap_plan(payload):
    if isinstance(payload, dict) and isinstance(payload.get("plan"), dict):
        return payload["plan"]
    return payload if isinstance(payload, dict) else {}


def run():
    report = {}
    status, payload = call("GET", "/api/debug/agent-info")
    report["test1_debug_endpoint"] = {"status": status, "payload": payload}

    cases = {
        "test2_3d": "Build a 3D product visualizer with Three.js and interactive rotation",
        "test3_blockchain": "Build Ethereum smart contract DeFi dApp with Web3 wallet",
        "test4_ml": "Build ML recommendation engine with TensorFlow and embeddings",
        "test5_iot": "Build IoT temperature sensor system with Arduino and MQTT cloud",
        "test6_todo": "Build a simple todo app with React",
        "test7_helios": "Build Helios Aegis enterprise platform with 3D visualizer, ML engine, smart contracts, IoT, and Kubernetes",
        "test8_negation": "Build smart contract system - NOT an AR app",
    }
    for key, goal in cases.items():
        status, payload = call("POST", "/api/build", {"goal": goal})
        plan = unwrap_plan(payload)
        selected = plan.get("selected_agents", []) if isinstance(plan.get("selected_agents"), list) else []
        report[key] = {
            "status": status,
            "selected_agent_count": plan.get("selected_agent_count"),
            "orchestration_mode": plan.get("orchestration_mode"),
            "phase_count": plan.get("phase_count"),
            "selected_agents": selected,
        }

    status, payload = call("GET", "/api/debug/agent-info")
    report["test9_last_build"] = {"status": status, "last_build": payload.get("last_build") if isinstance(payload, dict) else payload}

    status, payload = call("GET", "/api/debug/agent-selection-logs")
    report["test10_log_equivalent"] = {"status": status, "payload": payload}

    (OUTPUT_DIR / "production_routing_checklist.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    run()
