from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
from sqlalchemy.orm import joinedload
from sqlalchemy import desc, and_

from .database import get_db_session
from .models import Campaign, Episode, Character, CharacterSnapshot, LevelProgression, PlayerNote, StoryMilestone

logger = logging.getLogger(__name__)

class CampaignOperations:
    """Campaign-level database operations"""
    
    @staticmethod
    def get_or_create_campaign(guild_id: str, name: str = "Storm King's Thunder") -> Campaign:
        """Get existing campaign or create new one for guild"""
        with get_db_session() as session:
            campaign = session.query(Campaign).filter_by(guild_id=guild_id).first()
            
            if not campaign:
                campaign = Campaign(
                    guild_id=guild_id,
                    name=name,
                    setting_description="The Sword Coast - Giants have begun raiding settlements across the land. The ancient ordning that kept giant society in check has collapsed, throwing giantkind into chaos.",
                    current_scene="The village of Nightstone sits eerily quiet. Giant-sized boulders litter the village square, and not a soul can be seen moving in the streets. The party approaches the mysteriously open gates..."
                )
                session.add(campaign)
                session.flush()  # Get the ID
                logger.info(f"Created new campaign for guild {guild_id}")
            
            return campaign
    
    @staticmethod
    def update_current_scene(guild_id: str, scene: str) -> bool:
        """Update the current scene for a campaign"""
        with get_db_session() as session:
            campaign = session.query(Campaign).filter_by(guild_id=guild_id).first()
            if campaign:
                campaign.current_scene = scene
                return True
            return False

class EpisodeOperations:
    """Episode-level database operations"""
    
    @staticmethod
    def start_new_episode(guild_id: str, episode_name: str = None) -> Tuple[Episode, bool]:
        """Start a new episode, automatically ending the previous one"""
        with get_db_session() as session:
            campaign = CampaignOperations.get_or_create_campaign(guild_id)
            
            # End any active episode first
            active_episode = session.query(Episode).filter_by(
                campaign_id=campaign.id,
                status='active'
            ).first()
            
            ended_previous = False
            if active_episode:
                EpisodeOperations._end_episode_internal(session, active_episode)
                ended_previous = True
            
            # Create new episode
            new_episode_number = campaign.current_episode_number + 1
            episode = Episode(
                campaign_id=campaign.id,
                episode_number=new_episode_number,
                name=episode_name or f"Episode {new_episode_number}",
                starting_scene=campaign.current_scene,
                major_events=[],
                next_session_hooks=[]
            )
            
            session.add(episode)
            
            # Update campaign
            campaign.current_episode_number = new_episode_number
            
            # Create character snapshots for episode start
            characters = session.query(Character).filter_by(campaign_id=campaign.id).all()
            for character in characters:
                CharacterOperations._create_snapshot_internal(
                    session, character, episode, 'episode_start'
                )
            
            logger.info(f"Started episode {new_episode_number} for guild {guild_id}")
            return episode, ended_previous
    
    @staticmethod
    def end_current_episode(guild_id: str, summary: str = None, dm_notes: str = None, 
                          cliffhanger: str = None, next_hooks: List[str] = None) -> Optional[Episode]:
        """End the current active episode"""
        with get_db_session() as session:
            campaign = session.query(Campaign).filter_by(guild_id=guild_id).first()
            if not campaign:
                return None
            
            active_episode = session.query(Episode).filter_by(
                campaign_id=campaign.id,
                status='active'
            ).first()
            
            if not active_episode:
                return None
            
            return EpisodeOperations._end_episode_internal(
                session, active_episode, summary, dm_notes, cliffhanger, next_hooks
            )
    
    @staticmethod
    def _end_episode_internal(session, episode: Episode, summary: str = None, 
                            dm_notes: str = None, cliffhanger: str = None, 
                            next_hooks: List[str] = None) -> Episode:
        """Internal method to end an episode (called within existing session)"""
        episode.end_time = datetime.utcnow()
        episode.duration_hours = (episode.end_time - episode.start_time).total_seconds() / 3600
        episode.status = 'completed'
        
        if summary:
            episode.summary = summary
        if dm_notes:
            episode.dm_notes = dm_notes
        if cliffhanger:
            episode.cliffhanger = cliffhanger
        if next_hooks:
            episode.next_session_hooks = next_hooks
        
        # Update ending scene
        campaign = session.query(Campaign).filter_by(id=episode.campaign_id).first()
        if campaign:
            episode.ending_scene = campaign.current_scene
        
        # Create end-of-episode character snapshots
        characters = session.query(Character).filter_by(campaign_id=episode.campaign_id).all()
        for character in characters:
            CharacterOperations._create_snapshot_internal(
                session, character, episode, 'episode_end'
            )
        
        logger.info(f"Ended episode {episode.episode_number}")
        return episode
    
    @staticmethod
    def get_episode_history(guild_id: str, limit: int = 10) -> List[Episode]:
        """Get recent episode history"""
        with get_db_session() as session:
            campaign = session.query(Campaign).filter_by(guild_id=guild_id).first()
            if not campaign:
                return []
            
            return session.query(Episode).filter_by(campaign_id=campaign.id)\
                .order_by(desc(Episode.episode_number))\
                .limit(limit).all()
    
    @staticmethod
    def get_episode_recap_data(guild_id: str, episode_number: int = None) -> Optional[Dict]:
        """Get data for generating episode recap"""
        with get_db_session() as session:
            campaign = session.query(Campaign).filter_by(guild_id=guild_id).first()
            if not campaign:
                return None
            
            if episode_number is None:
                episode_number = campaign.current_episode_number - 1
            
            episode = session.query(Episode).filter_by(
                campaign_id=campaign.id,
                episode_number=episode_number
            ).options(
                joinedload(Episode.character_snapshots),
                joinedload(Episode.story_milestones),
                joinedload(Episode.player_notes)
            ).first()
            
            if not episode:
                return None
            
            return {
                'episode': episode,
                'character_changes': [s for s in episode.character_snapshots if s.snapshot_type == 'episode_end'],
                'story_milestones': episode.story_milestones,
                'major_events': episode.major_events or [],
                'cliffhanger': episode.cliffhanger,
                'player_notes': [n for n in episode.player_notes if n.is_public]
            }

class CharacterOperations:
    """Character-level database operations"""
    
    @staticmethod
    def sync_character_from_context(guild_id: str, discord_user_id: str, character_data: Dict) -> Character:
        """Sync character from campaign_context to database"""
        with get_db_session() as session:
            campaign = CampaignOperations.get_or_create_campaign(guild_id)
            
            character = session.query(Character).filter_by(
                campaign_id=campaign.id,
                discord_user_id=discord_user_id
            ).first()
            
            if not character:
                character = Character(
                    campaign_id=campaign.id,
                    discord_user_id=discord_user_id,
                    player_name=character_data['player_name'],
                    name=character_data['name'],
                    race=character_data['race'],
                    character_class=character_data['class'],
                    current_level=character_data['level'],
                    background=character_data.get('background'),
                    stats=character_data.get('stats'),
                    equipment=character_data.get('equipment'),
                    spells=character_data.get('spells'),
                    affiliations=character_data.get('affiliations'),
                    personality=character_data.get('personality')
                )
                session.add(character)
                logger.info(f"Created new character {character_data['name']} for user {discord_user_id}")
            else:
                # Update existing character
                character.player_name = character_data['player_name']
                character.current_level = character_data['level']
                character.background = character_data.get('background')
                character.stats = character_data.get('stats')
                character.equipment = character_data.get('equipment')
                character.spells = character_data.get('spells')
                character.affiliations = character_data.get('affiliations')
                character.personality = character_data.get('personality')
                character.last_updated = datetime.utcnow()
            
            return character
    
    @staticmethod
    def level_up_character(guild_id: str, discord_user_id: str, new_level: int, reason: str = None) -> bool:
        """Record character level progression"""
        with get_db_session() as session:
            campaign = session.query(Campaign).filter_by(guild_id=guild_id).first()
            if not campaign:
                return False
            
            character = session.query(Character).filter_by(
                campaign_id=campaign.id,
                discord_user_id=discord_user_id
            ).first()
            
            if not character or character.current_level >= new_level:
                return False
            
            # Get current episode
            current_episode = session.query(Episode).filter_by(
                campaign_id=campaign.id,
                status='active'
            ).first()
            
            if not current_episode:
                return False
            
            # Record level progression
            progression = LevelProgression(
                character_id=character.id,
                episode_id=current_episode.id,
                old_level=character.current_level,
                new_level=new_level,
                reason=reason or f"Leveled from {character.current_level} to {new_level}"
            )
            session.add(progression)
            
            # Update character
            old_level = character.current_level
            character.current_level = new_level
            character.last_updated = datetime.utcnow()
            
            # Create level-up snapshot
            CharacterOperations._create_snapshot_internal(
                session, character, current_episode, 'level_up',
                notes=f"Leveled up from {old_level} to {new_level}. {reason or ''}"
            )
            
            logger.info(f"Character {character.name} leveled up to {new_level}")
            return True
    
    @staticmethod
    def _create_snapshot_internal(session, character: Character, episode: Episode, 
                                snapshot_type: str, notes: str = None):
        """Create character snapshot (internal method)"""
        snapshot = CharacterSnapshot(
            character_id=character.id,
            episode_id=episode.id,
            snapshot_type=snapshot_type,
            level=character.current_level,
            hp_current=character.current_hp,
            hp_max=character.max_hp,
            equipment_snapshot=character.equipment,
            spells_snapshot=character.spells,
            notes=notes
        )
        session.add(snapshot)
    
    @staticmethod
    def get_character_progression(guild_id: str, discord_user_id: str) -> List[Dict]:
        """Get character progression history"""
        with get_db_session() as session:
            campaign = session.query(Campaign).filter_by(guild_id=guild_id).first()
            if not campaign:
                return []
            
            character = session.query(Character).filter_by(
                campaign_id=campaign.id,
                discord_user_id=discord_user_id
            ).first()
            
            if not character:
                return []
            
            progressions = session.query(LevelProgression).filter_by(character_id=character.id)\
                .order_by(LevelProgression.level_gained).all()
            
            return [{
                'episode_number': p.episode.episode_number,
                'episode_name': p.episode.name,
                'old_level': p.old_level,
                'new_level': p.new_level,
                'reason': p.reason,
                'date': p.level_gained
            } for p in progressions]

class PlayerNoteOperations:
    """Player note operations"""
    
    @staticmethod
    def add_player_note(guild_id: str, discord_user_id: str, player_name: str, 
                       content: str, note_type: str = 'player_observation', 
                       is_public: bool = True) -> bool:
        """Add a player note to current episode"""
        with get_db_session() as session:
            campaign = session.query(Campaign).filter_by(guild_id=guild_id).first()
            if not campaign:
                return False
            
            current_episode = session.query(Episode).filter_by(
                campaign_id=campaign.id,
                status='active'
            ).first()
            
            if not current_episode:
                return False
            
            note = PlayerNote(
                episode_id=current_episode.id,
                discord_user_id=discord_user_id,
                player_name=player_name,
                note_type=note_type,
                content=content,
                is_public=is_public,
                is_canonical=False  # Player notes are never canonical
            )
            session.add(note)
            
            logger.info(f"Added player note from {player_name}")
            return True
    
    @staticmethod
    def get_episode_player_notes(guild_id: str, episode_number: int = None, 
                               public_only: bool = True) -> List[PlayerNote]:
        """Get player notes for an episode"""
        with get_db_session() as session:
            campaign = session.query(Campaign).filter_by(guild_id=guild_id).first()
            if not campaign:
                return []
            
            if episode_number is None:
                episode_number = campaign.current_episode_number
            
            episode = session.query(Episode).filter_by(
                campaign_id=campaign.id,
                episode_number=episode_number
            ).first()
            
            if not episode:
                return []
            
            query = session.query(PlayerNote).filter_by(episode_id=episode.id)
            if public_only:
                query = query.filter_by(is_public=True)
            
            return query.order_by(PlayerNote.created_time).all()