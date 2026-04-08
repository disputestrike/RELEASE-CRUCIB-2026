"""
Learning Analytics
Analyzes patterns in execution target choices
"""

from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class LearningAnalytics:
    """
    Analyzes patterns and generates recommendations
    """
    
    def __init__(self, learning_system):
        self.learning_system = learning_system
    
    def analyze_patterns(self) -> Dict:
        """
        Analyze patterns in choice history
        """
        
        history = self.learning_system.choice_history
        
        if len(history) < 10:
            return {"status": "insufficient_data", "min_required": 10}
        
        # Find which requests map to which targets
        request_patterns = {}
        for record in history:
            request = record["user_request"]
            target = record["user_choice"]
            
            if request not in request_patterns:
                request_patterns[request] = {}
            
            if target not in request_patterns[request]:
                request_patterns[request][target] = 0
            
            request_patterns[request][target] += 1
        
        # Find strong patterns (>80% of time chose same target)
        strong_patterns = {}
        for request, targets in request_patterns.items():
            total = sum(targets.values())
            for target, count in targets.items():
                if (count / total) > 0.8:
                    if request not in strong_patterns:
                        strong_patterns[request] = []
                    strong_patterns[request].append(target)
        
        return {
            "status": "complete",
            "total_observations": len(history),
            "strong_patterns": strong_patterns,
            "learning_stats": self.learning_system.get_learning_stats()
        }
    
    def suggest_confidence_boost(self, target: str, recent_accuracy: float) -> float:
        """
        Suggest a confidence boost based on recent performance
        """
        
        adjustment = self.learning_system.get_confidence_adjustment(target)
        
        # If recent accuracy is high, boost even more
        if recent_accuracy > 0.9:
            adjustment += 5
        
        return adjustment

