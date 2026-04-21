# CrucibAI Python SDK

Official Python client for the [CrucibAI](https://crucibai.com) platform.

## Installation

```bash
pip install crucibai
```

## Quickstart

```python
from crucibai import CrucibAI

client = CrucibAI(api_key="crc_YOUR_KEY_HERE")

# Browse marketplace templates
result = client.marketplace.listings(kind="template")
for listing in result["listings"]:
    print(listing["title"], listing["proof_score"])

# Start a preview-loop run
run = client.runs.create(prompt="Build a todo app", mode="build")
print(run["run_id"], run["status"])

# Fetch latest benchmark scores
benchmarks = client.benchmarks.latest()
print(benchmarks)
```

Get your API key from the [Developer Portal](https://crucibai.com/developer).
