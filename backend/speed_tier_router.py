"""
Speed Tier Router - Handles model selection, token multipliers, and credit deduction based on speed tier
"""


class SpeedTierRouter:
    """Routes requests to appropriate model and applies token multipliers based on speed tier and plan"""

    SPEED_CONFIGS = {
        "lite": {
            "name": "CrucibAI 1.0 Lite",
            "model": "cerebras",
            "parallelism": 1,
            "token_multiplier": 1.0,
            "credit_cost": 50,
            "timeout": 300,
            "label": "Sequential",
        },
        "pro": {
            "name": "CrucibAI 1.0",
            "model": "haiku",
            "parallelism": 2.5,
            "token_multiplier": 1.5,
            "credit_cost": 100,
            "timeout": 180,
            "label": "Parallel",
        },
        "max": {
            "name": "CrucibAI 1.0 Max",
            "model": "haiku",
            "parallelism": 4.0,
            "token_multiplier": 2.0,
            "credit_cost": 150,
            "timeout": 120,
            "label": "Full Swarm",
            "all_agents": True,
        },
    }

    PLAN_SPEED_ACCESS = {
        "free": ["lite"],
        "builder": ["lite", "pro"],
        "pro": ["lite", "pro", "max"],
        "scale": ["lite", "pro", "max"],
        "teams": ["lite", "pro", "max"],
    }

    @staticmethod
    def validate_speed_tier_access(plan: str, speed_tier: str) -> tuple[bool, str]:
        """
        Validate if a user's plan allows access to the requested speed tier

        Returns: (is_valid, error_message)
        """
        allowed_speeds = SpeedTierRouter.PLAN_SPEED_ACCESS.get(plan, ["lite"])

        if speed_tier not in allowed_speeds:
            if speed_tier == "pro":
                return (
                    False,
                    "Pro and Max speeds are available on paid plans only. Upgrade to Builder or higher.",
                )
            elif speed_tier == "max":
                return (
                    False,
                    "Max speed is available on Pro and Teams plans only. Upgrade to Pro or higher.",
                )
            else:
                return (
                    False,
                    f"Speed tier '{speed_tier}' is not available on your plan.",
                )

        return True, ""

    @staticmethod
    def get_model_for_tier(speed_tier: str) -> str:
        """Get the LLM model for a given speed tier"""
        config = SpeedTierRouter.SPEED_CONFIGS.get(speed_tier, {})
        return config.get("model", "cerebras")

    @staticmethod
    def get_token_multiplier(speed_tier: str, plan: str = None) -> float:
        """
        Get token multiplier for a speed tier

        Lite: 1.0x (baseline)
        Pro: 1.5x (parallel agents)
        Max: 2.0x (full swarm)
        """
        config = SpeedTierRouter.SPEED_CONFIGS.get(speed_tier, {})
        return config.get("token_multiplier", 1.0)

    @staticmethod
    def get_credit_cost(speed_tier: str) -> int:
        """Get credit cost for a build at this speed tier"""
        config = SpeedTierRouter.SPEED_CONFIGS.get(speed_tier, {})
        return config.get("credit_cost", 50)

    @staticmethod
    def get_parallelism_level(speed_tier: str) -> float:
        """Get parallelism level (number of agents that can run in parallel)"""
        config = SpeedTierRouter.SPEED_CONFIGS.get(speed_tier, {})
        return config.get("parallelism", 1)

    @staticmethod
    def should_use_full_swarm(speed_tier: str) -> bool:
        """Check if this speed tier should use all 374 Agents (max only)"""
        config = SpeedTierRouter.SPEED_CONFIGS.get(speed_tier, {})
        return config.get("all_agents", False)

    @staticmethod
    def get_timeout(speed_tier: str) -> int:
        """Get timeout in seconds for this speed tier"""
        config = SpeedTierRouter.SPEED_CONFIGS.get(speed_tier, {})
        return config.get("timeout", 300)

    @staticmethod
    def get_speed_label(speed_tier: str) -> str:
        """Get human-readable label for speed tier"""
        config = SpeedTierRouter.SPEED_CONFIGS.get(speed_tier, {})
        return config.get("label", speed_tier.capitalize())

    @staticmethod
    def apply_token_multiplier(base_tokens: int, speed_tier: str) -> int:
        """Apply token multiplier to base token count"""
        multiplier = SpeedTierRouter.get_token_multiplier(speed_tier)
        return int(base_tokens * multiplier)

    @staticmethod
    def get_build_time_estimate(speed_tier: str) -> str:
        """Get estimated build time for this speed tier"""
        estimates = {"lite": "30-40s", "pro": "12-16s", "max": "8-10s"}
        return estimates.get(speed_tier, "30-40s")

    @staticmethod
    def route_request(plan: str, speed_tier: str, base_tokens: int) -> dict:
        """
        Route a build request to the appropriate model and configuration

        Returns: {
            "valid": bool,
            "error": str (if not valid),
            "model": str,
            "speed_tier": str,
            "token_multiplier": float,
            "adjusted_tokens": int,
            "credit_cost": int,
            "parallelism": float,
            "timeout": int,
            "use_full_swarm": bool,
            "build_time_estimate": str,
            "label": str
        }
        """
        # Validate access
        is_valid, error_msg = SpeedTierRouter.validate_speed_tier_access(
            plan, speed_tier
        )
        if not is_valid:
            return {"valid": False, "error": error_msg, "status_code": 403}

        # Route to appropriate model and configuration
        model = SpeedTierRouter.get_model_for_tier(speed_tier)
        token_multiplier = SpeedTierRouter.get_token_multiplier(speed_tier, plan)
        adjusted_tokens = SpeedTierRouter.apply_token_multiplier(
            base_tokens, speed_tier
        )
        credit_cost = SpeedTierRouter.get_credit_cost(speed_tier)
        parallelism = SpeedTierRouter.get_parallelism_level(speed_tier)
        timeout = SpeedTierRouter.get_timeout(speed_tier)
        use_full_swarm = SpeedTierRouter.should_use_full_swarm(speed_tier)
        build_time_estimate = SpeedTierRouter.get_build_time_estimate(speed_tier)
        label = SpeedTierRouter.get_speed_label(speed_tier)

        return {
            "valid": True,
            "model": model,
            "speed_tier": speed_tier,
            "token_multiplier": token_multiplier,
            "adjusted_tokens": adjusted_tokens,
            "credit_cost": credit_cost,
            "parallelism": parallelism,
            "timeout": timeout,
            "use_full_swarm": use_full_swarm,
            "build_time_estimate": build_time_estimate,
            "label": label,
        }
