import anthropic
import os
import asyncio
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class RecapGenerator:
    """Generate dramatic episode recaps using Claude AI"""
    
    def __init__(self):
        self.claude_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
    
    async def generate_dramatic_recap(self, recap_data: Dict) -> str:
        """Generate a dramatic, TV-show style recap"""
        episode = recap_data['episode']
        character_changes = recap_data['character_changes']
        story_milestones = recap_data['story_milestones']
        major_events = recap_data['major_events']
        cliffhanger = recap_data['cliffhanger']
        player_notes = recap_data['player_notes']
        
        prompt = f"""You are creating a dramatic "Previously on Storm King's Thunder" style recap for a D&D campaign episode. Make it sound like a professional TV show recap with dramatic flair and tension.

EPISODE: {episode.name} (Episode {episode.episode_number})
DURATION: {episode.duration_hours:.1f} hours
EPISODE SUMMARY: {episode.summary or 'No summary provided'}

CHARACTER CHANGES:
{self._format_character_changes(character_changes)}

MAJOR STORY EVENTS:
{self._format_story_events(major_events, story_milestones)}

CLIFFHANGER: {cliffhanger or 'None'}

PLAYER PERSPECTIVES (NOT CANONICAL - player thoughts only):
{self._format_player_notes(player_notes)}

Create a dramatic recap that:
1. Sounds like a TV narrator (think "Previously on Game of Thrones" style)
2. Highlights the most exciting/important moments
3. Builds tension toward the cliffhanger
4. Is 150-300 words long
5. Uses present tense and vivid language
6. References character names and their key moments
7. Does NOT include player speculation as fact - only canonical story events

Begin with "Previously on Storm King's Thunder..." and make it sound epic and engaging!"""

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=400,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate dramatic recap: {e}")
            return self._generate_fallback_recap(episode, major_events, cliffhanger)
    
    async def generate_character_focused_recap(self, recap_data: Dict) -> str:
        """Generate a character-focused recap"""
        episode = recap_data['episode']
        character_changes = recap_data['character_changes']
        
        prompt = f"""Create a character-focused recap for D&D Episode {episode.episode_number}: {episode.name}

Focus on what happened to each character, their growth, decisions, and key moments.

CHARACTER DEVELOPMENTS:
{self._format_character_changes(character_changes)}

EPISODE SUMMARY: {episode.summary or 'No summary provided'}

Create a 100-200 word recap that focuses on:
1. What each character accomplished
2. How they changed or grew
3. Key character decisions and moments
4. Character relationships and interactions

Use a narrative style that emphasizes the personal journeys of the heroes."""

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=300,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate character-focused recap: {e}")
            return self._generate_fallback_character_recap(character_changes)
    
    async def generate_story_beats_recap(self, recap_data: Dict) -> str:
        """Generate a story beats focused recap"""
        episode = recap_data['episode']
        story_milestones = recap_data['story_milestones']
        major_events = recap_data['major_events']
        
        prompt = f"""Create a story beats recap for D&D Episode {episode.episode_number}: {episode.name}

Focus on the major plot developments and story progression.

STORY MILESTONES:
{self._format_story_milestones(story_milestones)}

MAJOR EVENTS:
{', '.join(major_events) if major_events else 'No major events recorded'}

EPISODE SUMMARY: {episode.summary or 'No summary provided'}

Create a 100-200 word recap that focuses on:
1. Major plot developments
2. Story revelations and discoveries
3. Plot threads that were advanced
4. New mysteries or questions raised
5. How the overarching story progressed

Use a narrative style that emphasizes plot progression and story beats."""

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.claude_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=300,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }]
                )
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate story beats recap: {e}")
            return self._generate_fallback_story_recap(major_events, story_milestones)
    
    def generate_quick_recap(self, recap_data: Dict) -> str:
        """Generate a quick, bullet-point style recap"""
        episode = recap_data['episode']
        major_events = recap_data['major_events']
        character_changes = recap_data['character_changes']
        cliffhanger = recap_data['cliffhanger']
        
        recap_parts = []
        
        if episode.summary:
            recap_parts.append(f"📋 **Summary:** {episode.summary}")
        
        if major_events:
            events_text = ' • '.join(major_events[:3])  # Limit to top 3 events
            recap_parts.append(f"⚡ **Key Events:** {events_text}")
        
        if character_changes:
            char_changes = []
            for change in character_changes[:3]:  # Limit to 3 characters
                if change.notes:
                    char_changes.append(f"{change.character.name}: {change.notes}")
            if char_changes:
                recap_parts.append(f"🎭 **Characters:** {' • '.join(char_changes)}")
        
        if cliffhanger:
            recap_parts.append(f"🎬 **Cliffhanger:** {cliffhanger}")
        
        return '\n\n'.join(recap_parts) if recap_parts else "No recap data available."
    
    def _format_character_changes(self, character_changes: List) -> str:
        """Format character changes for prompt"""
        if not character_changes:
            return "No significant character changes recorded"
        
        formatted = []
        for change in character_changes:
            char_name = change.character.name
            level = change.level
            notes = change.notes or "No specific notes"
            formatted.append(f"- {char_name} (Level {level}): {notes}")
        
        return '\n'.join(formatted)
    
    def _format_story_events(self, major_events: List, story_milestones: List) -> str:
        """Format story events and milestones"""
        formatted = []
        
        if major_events:
            formatted.extend([f"- {event}" for event in major_events])
        
        if story_milestones:
            for milestone in story_milestones:
                significance = milestone.significance.upper() if milestone.significance != 'medium' else ""
                formatted.append(f"- {significance} {milestone.title}: {milestone.description or ''}")
        
        return '\n'.join(formatted) if formatted else "No major events recorded"
    
    def _format_story_milestones(self, story_milestones: List) -> str:
        """Format story milestones specifically"""
        if not story_milestones:
            return "No story milestones recorded"
        
        formatted = []
        for milestone in story_milestones:
            significance = f"[{milestone.significance.upper()}]" if milestone.significance != 'medium' else ""
            formatted.append(f"- {significance} {milestone.title}: {milestone.description or ''}")
        
        return '\n'.join(formatted)
    
    def _format_player_notes(self, player_notes: List) -> str:
        """Format player notes (marked as non-canonical)"""
        if not player_notes:
            return "No player notes recorded"
        
        formatted = []
        for note in player_notes[:5]:  # Limit to 5 most recent
            note_type = note.note_type.replace('_', ' ').title()
            formatted.append(f"- {note.player_name} ({note_type}): {note.content}")
        
        return '\n'.join(formatted)
    
    def _generate_fallback_recap(self, episode, major_events: List, cliffhanger: str) -> str:
        """Generate a simple fallback recap if AI fails"""
        recap = f"Previously on Storm King's Thunder, in Episode {episode.episode_number}"
        
        if episode.name:
            recap += f" '{episode.name}'"
        
        if episode.summary:
            recap += f": {episode.summary}"
        elif major_events:
            recap += f", our heroes {', '.join(major_events[:2])}"
        else:
            recap += ", our heroes continued their journey through the giant crisis"
        
        if cliffhanger:
            recap += f" But {cliffhanger.lower()}"
        
        recap += " The adventure continues..."
        
        return recap
    
    def _generate_fallback_character_recap(self, character_changes: List) -> str:
        """Generate fallback character recap"""
        if not character_changes:
            return "The party members continued their adventures, growing stronger and wiser through their trials."
        
        recap = "Our heroes progressed on their journey: "
        char_summaries = []
        
        for change in character_changes[:3]:
            if change.notes:
                char_summaries.append(f"{change.character.name} {change.notes.lower()}")
            else:
                char_summaries.append(f"{change.character.name} reached level {change.level}")
        
        recap += ', '.join(char_summaries) + "."
        return recap
    
    def _generate_fallback_story_recap(self, major_events: List, story_milestones: List) -> str:
        """Generate fallback story recap"""
        if not major_events and not story_milestones:
            return "The overarching story of the giant crisis continued to unfold as our heroes delved deeper into the mystery."
        
        recap_parts = []
        
        if major_events:
            recap_parts.append(f"Key developments included: {', '.join(major_events[:3])}")
        
        if story_milestones:
            milestone_titles = [m.title for m in story_milestones[:2]]
            recap_parts.append(f"Important milestones: {', '.join(milestone_titles)}")
        
        return '. '.join(recap_parts) + "."