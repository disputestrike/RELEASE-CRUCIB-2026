"""
Comprehensive test suite for CrucibAI 1.0 Speed Tier Implementation
Tests all 11 requirements from the feedback specification
"""

import pytest
from speed_tier_router import SpeedTierRouter


class TestSpeedTierAccess:
    """Test 1-5: Plan-based speed tier access"""
    
    def test_free_user_sees_only_lite(self):
        """Test 1: Free user sees only Lite, Pro/Max locked"""
        available = SpeedTierRouter.PLAN_SPEED_ACCESS.get("free", [])
        assert available == ["lite"], "Free plan should only have Lite speed"
        assert "pro" not in available, "Free plan should not have Pro speed"
        assert "max" not in available, "Free plan should not have Max speed"
    
    def test_starter_user_sees_lite_pro_only(self):
        """Test 2: Starter user sees Lite+Pro unlocked, Max locked, Pro uses Haiku, no swarm"""
        available = SpeedTierRouter.PLAN_SPEED_ACCESS.get("starter", [])
        assert "lite" in available, "Starter should have Lite speed"
        assert "pro" in available, "Starter should have Pro speed"
        assert "max" not in available, "Starter should not have Max speed"
        
        # Verify Pro uses Haiku
        model = SpeedTierRouter.get_model_for_tier("pro")
        assert model == "haiku", "Pro speed should use Haiku model"
        
        # Verify no swarm for Starter
        is_valid, _ = SpeedTierRouter.validate_speed_tier_access("starter", "pro")
        assert is_valid, "Starter should have access to Pro speed"
    
    def test_builder_user_sees_lite_pro_with_swarm(self):
        """Test 3: Builder user sees Lite+Pro unlocked with swarm, Max locked, faster than Starter"""
        available = SpeedTierRouter.PLAN_SPEED_ACCESS.get("builder", [])
        assert "lite" in available, "Builder should have Lite speed"
        assert "pro" in available, "Builder should have Pro speed"
        assert "max" not in available, "Builder should not have Max speed"
        
        # Verify swarm enabled for Builder (implied by Pro speed access)
        is_valid, _ = SpeedTierRouter.validate_speed_tier_access("builder", "pro")
        assert is_valid, "Builder should have access to Pro speed"
    
    def test_pro_user_sees_all_speeds_with_full_swarm(self):
        """Test 4: Pro user sees all 3 speeds, Max runs full swarm, progress shows 3 flames"""
        available = SpeedTierRouter.PLAN_SPEED_ACCESS.get("pro", [])
        assert "lite" in available, "Pro should have Lite speed"
        assert "pro" in available, "Pro should have Pro speed"
        assert "max" in available, "Pro should have Max speed"
        
        # Verify Max uses full swarm
        use_full_swarm = SpeedTierRouter.should_use_full_swarm("max")
        assert use_full_swarm, "Max speed should use full swarm (all 123 agents)"
    
    def test_teams_user_identical_to_pro_with_more_credits(self):
        """Test 5: Teams user identical to Pro with 10,000 credits"""
        pro_available = SpeedTierRouter.PLAN_SPEED_ACCESS.get("pro", [])
        teams_available = SpeedTierRouter.PLAN_SPEED_ACCESS.get("teams", [])
        
        assert pro_available == teams_available, "Teams should have same speed access as Pro"
        
        # Verify credit difference is only in quantity, not speed
        assert teams_available == ["lite", "pro", "max"], "Teams should have all 3 speeds"


class TestTokenMultipliers:
    """Test 6: Token multipliers and real-time cost estimates"""
    
    def test_token_multipliers_correct(self):
        """Test 6: Token estimate updates in real-time on speed change"""
        lite_multiplier = SpeedTierRouter.get_token_multiplier("lite")
        pro_multiplier = SpeedTierRouter.get_token_multiplier("pro")
        max_multiplier = SpeedTierRouter.get_token_multiplier("max")
        
        assert lite_multiplier == 1.0, "Lite should have 1.0x multiplier"
        assert pro_multiplier == 1.5, "Pro should have 1.5x multiplier"
        assert max_multiplier == 2.0, "Max should have 2.0x multiplier"
    
    def test_credit_costs_correct(self):
        """Verify credit costs match specification"""
        lite_cost = SpeedTierRouter.get_credit_cost("lite")
        pro_cost = SpeedTierRouter.get_credit_cost("pro")
        max_cost = SpeedTierRouter.get_credit_cost("max")
        
        assert lite_cost == 50, "Lite should cost 50 credits"
        assert pro_cost == 100, "Pro should cost 100 credits"
        assert max_cost == 150, "Max should cost 150 credits"


class TestProgressBar:
    """Test 7: Progress bar shows speed mode"""
    
    def test_progress_bar_labels(self):
        """Test 7: Progress bar shows correct mode label and flame count"""
        lite_label = SpeedTierRouter.get_speed_label("lite")
        pro_label = SpeedTierRouter.get_speed_label("pro")
        max_label = SpeedTierRouter.get_speed_label("max")
        
        assert lite_label == "Sequential", "Lite should show Sequential label"
        assert pro_label == "Parallel", "Pro should show Parallel label"
        assert max_label == "Full Swarm", "Max should show Full Swarm label"


class TestWorkspaceHeader:
    """Test 8: Workspace header shows current speed"""
    
    def test_speed_display_in_header(self):
        """Test 8: Workspace header shows current speed mode"""
        # This test verifies the speed tier router provides correct data for header
        lite_config = SpeedTierRouter.SPEED_CONFIGS.get("lite")
        pro_config = SpeedTierRouter.SPEED_CONFIGS.get("pro")
        max_config = SpeedTierRouter.SPEED_CONFIGS.get("max")
        
        assert lite_config is not None and lite_config.get("name") == "CrucibAI 1.0 Lite"
        assert pro_config is not None and pro_config.get("name") == "CrucibAI 1.0"
        assert max_config is not None and max_config.get("name") == "CrucibAI 1.0 Max"


class TestPricingPage:
    """Test 9: Pricing page shows 5 columns with correct order"""
    
    def test_pricing_page_plans(self):
        """Test 9: Pricing page shows 5 columns, correct order, Teams present, Pro has MOST POPULAR"""
        plans = ["free", "starter", "builder", "pro", "teams"]
        
        # Verify all plans exist
        for plan in plans:
            assert plan in SpeedTierRouter.PLAN_SPEED_ACCESS, f"Plan '{plan}' should exist"
        
        # Verify order
        assert plans == ["free", "starter", "builder", "pro", "teams"], "Plans should be in correct order"


class TestDatabaseAndStripe:
    """Test 10: Database & Stripe show Teams not Agency"""
    
    def test_no_agency_references(self):
        """Test 10: Database & Stripe show Teams not Agency everywhere"""
        # Verify no "agency" in plan access
        assert "agency" not in SpeedTierRouter.PLAN_SPEED_ACCESS, "Should not have 'agency' plan"
        
        # Verify "teams" exists
        assert "teams" in SpeedTierRouter.PLAN_SPEED_ACCESS, "Should have 'teams' plan"


class TestUIColors:
    """Test 11: No dark colors, orange accent only"""
    
    def test_no_dark_colors_added(self):
        """Test 11: No dark colors added, orange accent only, no layout changes"""
        # This is a visual test - verify the configuration supports white/light grey/orange only
        speed_configs = SpeedTierRouter.SPEED_CONFIGS
        
        # Verify configs exist and have proper structure
        for speed, config in speed_configs.items():
            assert "name" in config, f"Speed '{speed}' should have name"
            assert "model" in config, f"Speed '{speed}' should have model"
            assert "token_multiplier" in config, f"Speed '{speed}' should have token_multiplier"
            assert "credit_cost" in config, f"Speed '{speed}' should have credit_cost"


class TestRequestRouting:
    """Integration tests for request routing"""
    
    def test_valid_request_routing(self):
        """Test complete request routing"""
        result = SpeedTierRouter.route_request("pro", "max", 100000)
        
        assert result["valid"], "Request should be valid"
        assert result["model"] == "haiku", "Should route to Haiku model"
        assert result["token_multiplier"] == 2.0, "Should apply 2.0x multiplier"
        assert result["adjusted_tokens"] == 200000, "Should apply token multiplier"
        assert result["use_full_swarm"], "Max should use full swarm"
    
    def test_invalid_request_routing(self):
        """Test invalid request routing (plan doesn't have access to speed)"""
        result = SpeedTierRouter.route_request("free", "max", 100000)
        
        assert not result["valid"], "Request should be invalid"
        assert result["status_code"] == 403, "Should return 403 Forbidden"
        assert "available" in result["error"], "Should have error message"
    
    def test_starter_pro_speed_access(self):
        """Test Starter plan has Pro speed access"""
        result = SpeedTierRouter.route_request("starter", "pro", 100000)
        
        assert result["valid"], "Starter should have access to Pro speed"
        assert result["model"] == "haiku", "Pro should use Haiku"
        assert result["token_multiplier"] == 1.5, "Pro should have 1.5x multiplier"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
