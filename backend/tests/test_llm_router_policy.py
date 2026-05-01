from backend.llm_router import LLMRouter, TaskComplexity


def _labels(chain):
    return [x[0] for x in chain]


def test_simple_tasks_are_cerebras_first():
    router = LLMRouter()
    chain = router.get_model_chain(
        task_complexity=TaskComplexity.SIMPLE,
        user_tier="free",
        speed_selector="lite",
        available_credits=100,
    )
    if chain:
        assert _labels(chain)[0] == "cerebras"


def test_complex_tasks_keep_cerebras_primary():
    router = LLMRouter()
    chain = router.get_model_chain(
        task_complexity=TaskComplexity.COMPLEX,
        user_tier="pro",
        speed_selector="pro",
        available_credits=100,
    )
    labels = _labels(chain)
    if "haiku" in labels and "cerebras" in labels:
        assert labels.index("cerebras") < labels.index("haiku")


def test_critical_tasks_use_haiku_then_cerebras():
    router = LLMRouter()
    chain = router.get_model_chain(
        task_complexity=TaskComplexity.CRITICAL,
        user_tier="pro",
        speed_selector="pro",
        available_credits=100,
    )
    labels = _labels(chain)
    if "haiku" in labels and "cerebras" in labels:
        assert labels.index("haiku") < labels.index("cerebras")


def test_sonnet_not_in_default_chains():
    router = LLMRouter()
    chain = router.get_model_chain(
        task_complexity=TaskComplexity.CRITICAL,
        user_tier="pro",
        speed_selector="max",
        available_credits=100,
    )
    assert "sonnet" not in _labels(chain)
