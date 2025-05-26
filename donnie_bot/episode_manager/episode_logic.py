"""
Episode business logic for Storm King's Thunder
This module handles episode-specific business logic and validation
"""

class EpisodeLogic:
    """Handles episode business logic and validation"""
    
    def __init__(self):
        pass
    
    def validate_episode_transition(self, current_episode: int, new_episode: int) -> bool:
        """Validate that episode transition is valid"""
        return new_episode == current_episode + 1
    
    def calculate_episode_difficulty(self, party_level_avg: float, episode_number: int) -> str:
        """Calculate appropriate difficulty for episode based on party level"""
        base_difficulty = min(episode_number, 10)  # Cap at 10
        level_modifier = party_level_avg / 5  # Roughly scale with party level
        
        total_difficulty = base_difficulty + level_modifier
        
        if total_difficulty <= 3:
            return "Easy"
        elif total_difficulty <= 6:
            return "Medium"
        elif total_difficulty <= 9:
            return "Hard"
        else:
            return "Deadly"
    
    def generate_episode_hooks(self, campaign_progress: dict) -> list:
        """Generate story hooks for the next episode"""
        hooks = []
        
        # Add some default Storm King's Thunder hooks
        hooks.append("The giant raids intensify across the Sword Coast")
        hooks.append("Mysterious messages arrive from ancient allies")
        hooks.append("The ordning's collapse creates new opportunities")
        
        return hooks
    
    def validate_episode_summary(self, summary: str) -> tuple[bool, str]:
        """Validate episode summary for completeness"""
        if not summary or len(summary.strip()) < 10:
            return False, "Episode summary should be at least 10 characters"
        
        if len(summary) > 1000:
            return False, "Episode summary should be less than 1000 characters"
        
        return True, "Valid summary"