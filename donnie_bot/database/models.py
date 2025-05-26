from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Campaign(Base):
    __tablename__ = 'campaigns'
    
    id = Column(Integer, primary_key=True)
    guild_id = Column(String(20), unique=True, nullable=False)  # Discord guild ID
    name = Column(String(100), nullable=False)
    created_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default='active')  # active, paused, completed
    current_episode_number = Column(Integer, default=0)
    setting_description = Column(Text)
    current_scene = Column(Text)
    
    # Relationships
    episodes = relationship("Episode", back_populates="campaign", cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="campaign", cascade="all, delete-orphan")

class Episode(Base):
    __tablename__ = 'episodes'
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    episode_number = Column(Integer, nullable=False)
    name = Column(String(200))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    duration_hours = Column(Float, nullable=True)
    status = Column(String(20), default='active')  # active, completed
    
    # Episode content
    summary = Column(Text)
    dm_notes = Column(Text)
    major_events = Column(JSON)  # List of event strings
    cliffhanger = Column(Text)
    next_session_hooks = Column(JSON)  # List of hook strings
    
    # Scene tracking
    starting_scene = Column(Text)
    ending_scene = Column(Text)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="episodes")
    character_snapshots = relationship("CharacterSnapshot", back_populates="episode", cascade="all, delete-orphan")
    player_notes = relationship("PlayerNote", back_populates="episode", cascade="all, delete-orphan")
    story_milestones = relationship("StoryMilestone", back_populates="episode", cascade="all, delete-orphan")

class Character(Base):
    __tablename__ = 'characters'
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    discord_user_id = Column(String(20), nullable=False)
    player_name = Column(String(100), nullable=False)
    
    # Character details
    name = Column(String(100), nullable=False)
    race = Column(String(50), nullable=False)
    character_class = Column(String(50), nullable=False)
    current_level = Column(Integer, default=1)
    background = Column(String(100))
    
    # Character state
    current_hp = Column(Integer)
    max_hp = Column(Integer)
    stats = Column(JSON)  # Ability scores
    equipment = Column(Text)
    spells = Column(Text)
    affiliations = Column(Text)
    personality = Column(Text)
    
    # Tracking
    created_date = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="characters")
    snapshots = relationship("CharacterSnapshot", back_populates="character", cascade="all, delete-orphan")
    level_progressions = relationship("LevelProgression", back_populates="character", cascade="all, delete-orphan")

class CharacterSnapshot(Base):
    __tablename__ = 'character_snapshots'
    
    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    episode_id = Column(Integer, ForeignKey('episodes.id'), nullable=False)
    snapshot_time = Column(DateTime, default=datetime.utcnow)
    snapshot_type = Column(String(50))  # episode_start, episode_end, level_up, manual
    
    # Character state at snapshot time
    level = Column(Integer, nullable=False)
    hp_current = Column(Integer)
    hp_max = Column(Integer)
    equipment_snapshot = Column(Text)
    spells_snapshot = Column(Text)
    notes = Column(Text)  # What happened to the character this episode
    
    # Relationships
    character = relationship("Character", back_populates="snapshots")
    episode = relationship("Episode", back_populates="character_snapshots")

class LevelProgression(Base):
    __tablename__ = 'level_progressions'
    
    id = Column(Integer, primary_key=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    episode_id = Column(Integer, ForeignKey('episodes.id'), nullable=False)
    level_gained = Column(DateTime, default=datetime.utcnow)
    
    old_level = Column(Integer, nullable=False)
    new_level = Column(Integer, nullable=False)
    reason = Column(String(200))  # "Milestone reached", "Defeated giants", etc.
    
    # Relationships
    character = relationship("Character", back_populates="level_progressions")

class PlayerNote(Base):
    __tablename__ = 'player_notes'
    
    id = Column(Integer, primary_key=True)
    episode_id = Column(Integer, ForeignKey('episodes.id'), nullable=False)
    discord_user_id = Column(String(20), nullable=False)
    player_name = Column(String(100), nullable=False)
    created_time = Column(DateTime, default=datetime.utcnow)
    
    note_type = Column(String(50))  # character_thought, player_observation, theory, question
    content = Column(Text, nullable=False)
    is_public = Column(Boolean, default=True)  # Can other players see this note?
    
    # IMPORTANT: Mark as subjective for AI
    is_canonical = Column(Boolean, default=False)  # Only DM notes are canonical
    
    # Relationships
    episode = relationship("Episode", back_populates="player_notes")

class StoryMilestone(Base):
    __tablename__ = 'story_milestones'
    
    id = Column(Integer, primary_key=True)
    episode_id = Column(Integer, ForeignKey('episodes.id'), nullable=False)
    created_time = Column(DateTime, default=datetime.utcnow)
    
    milestone_type = Column(String(50))  # major_plot, character_arc, location_discovered, npc_met
    title = Column(String(200), nullable=False)
    description = Column(Text)
    significance = Column(String(20), default='medium')  # low, medium, high, critical
    
    # Relationships
    episode = relationship("Episode", back_populates="story_milestones")

# Indexes for performance
from sqlalchemy import Index
Index('idx_campaign_guild', Campaign.guild_id)
Index('idx_episode_campaign', Episode.campaign_id, Episode.episode_number)
Index('idx_character_discord_user', Character.discord_user_id)
Index('idx_snapshot_episode', CharacterSnapshot.episode_id)
Index('idx_player_note_episode', PlayerNote.episode_id)