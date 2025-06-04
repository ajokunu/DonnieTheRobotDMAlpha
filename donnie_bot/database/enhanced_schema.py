# donnie_bot/database/enhanced_schema.py
"""
Enhanced Database Schema for Persistent Memory System
Adds tables for conversation memories, NPC tracking, world state, and plot management
"""

import sqlite3
from datetime import datetime
import json
from typing import Optional, Dict, Any

def upgrade_database_schema():
    """Upgrade database with enhanced memory tables"""
    from .database import get_db_connection
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        print("🔄 Upgrading database schema for enhanced memory...")
        
        # Create conversation_memories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_memories (
                memory_id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                episode_id INTEGER,
                user_id TEXT NOT NULL,
                character_name TEXT NOT NULL,
                player_input TEXT NOT NULL,
                dm_response TEXT NOT NULL,
                summary TEXT NOT NULL,
                entities TEXT,  -- JSON array of extracted entities
                importance_score REAL NOT NULL DEFAULT 0.5,
                emotional_context TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                scene_context TEXT,
                combat_context TEXT,
                FOREIGN KEY (episode_id) REFERENCES episodes (id)
            )
        ''')
        
        # Create indexes for conversation_memories
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_campaign_id ON conversation_memories(campaign_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_importance ON conversation_memories(importance_score)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversation_memories(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conv_character ON conversation_memories(character_name)')
        
        # Create npc_memories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS npc_memories (
                npc_id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                personality_summary TEXT,
                first_encountered_episode INTEGER,
                last_seen_episode INTEGER,
                relationship_with_party TEXT,
                current_location TEXT,
                faction_affiliation TEXT,
                knowledge_base TEXT,  -- JSON object of what the NPC knows
                secrets TEXT,  -- JSON array of secrets the NPC has
                goals TEXT,  -- JSON array of NPC goals
                mannerisms TEXT,
                voice_description TEXT,
                importance_level TEXT DEFAULT 'minor',  -- minor, notable, important, major
                status TEXT DEFAULT 'alive',  -- alive, dead, missing, unknown
                notes TEXT,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(campaign_id, name)
            )
        ''')
        
        # Create indexes for npc_memories
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_npc_campaign_id ON npc_memories(campaign_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_npc_importance ON npc_memories(importance_level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_npc_name ON npc_memories(name)')
        
        # Create world_state table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS world_state (
                state_id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                location_name TEXT NOT NULL,
                current_state TEXT,
                previous_state TEXT,
                changed_by_episode INTEGER,
                faction_control TEXT,
                threat_level TEXT DEFAULT 'normal',  -- safe, normal, dangerous, critical
                notable_features TEXT,  -- JSON array
                active_events TEXT,  -- JSON array of ongoing events
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(campaign_id, location_name)
            )
        ''')
        
        # Create plot_threads table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plot_threads (
                thread_id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                thread_name TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'active',  -- active, completed, abandoned, on_hold
                introduced_episode INTEGER,
                resolved_episode INTEGER,
                related_npcs TEXT,  -- JSON array of NPC names
                related_locations TEXT,  -- JSON array of location names
                player_actions TEXT,  -- JSON array of relevant player actions
                dm_notes TEXT,
                importance_level TEXT DEFAULT 'minor',  -- minor, major, central
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create memory_consolidation table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_consolidation (
                consolidation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                episode_id INTEGER NOT NULL,
                episode_summary TEXT,
                key_events TEXT,  -- JSON array of important events
                character_developments TEXT,  -- JSON array of character growth
                npc_interactions TEXT,  -- JSON array of significant NPC interactions
                world_changes TEXT,  -- JSON array of world state changes
                new_plot_threads TEXT,  -- JSON array of new plot threads
                resolved_plot_threads TEXT,  -- JSON array of resolved threads
                player_choices TEXT,  -- JSON array of significant choices
                emotional_moments TEXT,  -- JSON array of high-impact scenes
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (episode_id) REFERENCES episodes (id),
                UNIQUE(campaign_id, episode_id)
            )
        ''')
        
        # Create campaign_constants table for Storm King's Thunder specific data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaign_constants (
                constant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_name TEXT NOT NULL,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                details TEXT,  -- JSON object with detailed information
                importance TEXT DEFAULT 'normal',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(setting_name, category, name)
            )
        ''')
        
        # Insert Storm King's Thunder constants
        insert_storm_kings_thunder_constants(cursor)
        
        conn.commit()
        print("✅ Enhanced memory schema upgrade completed successfully")
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'conversation_memories', 'npc_memories', 'world_state', 
            'plot_threads', 'memory_consolidation', 'campaign_constants'
        ]
        
        for table in required_tables:
            if table in tables:
                print(f"✅ Table {table}: created")
            else:
                print(f"❌ Table {table}: missing")
                raise Exception(f"Failed to create table {table}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema upgrade failed: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

def insert_storm_kings_thunder_constants(cursor):
    """Insert Storm King's Thunder campaign constants"""
    
    # Giants and the Ordning
    giants_data = [
        ("Storm Giant", "Highest in the ordning, masters of sea and storm", {
            "ordning_rank": 1,
            "typical_locations": ["Storm Giant Court", "Eye of the All-Father", "Maelstrom"],
            "key_npcs": ["King Hekaton", "Princess Serissa", "Princess Mirran", "Princess Nym"],
            "abilities": ["Storm magic", "Lightning", "Weather control"],
            "motivations": ["Restore the ordning", "Find King Hekaton", "Unite giant-kind"]
        }),
        ("Cloud Giant", "Noble giants who live in the clouds", {
            "ordning_rank": 2,
            "typical_locations": ["Cloud Giant Castles", "Lyn Armaal", "Nightstone vicinity"],
            "key_npcs": ["Zephyros", "Count Thullen", "Countess Sansuri"],
            "abilities": ["Flight", "Cloud walking", "Weather magic"],
            "motivations": ["Wealth", "Nobility", "Ancient artifacts"]
        }),
        ("Fire Giant", "Masters of smithing and war", {
            "ordning_rank": 3,
            "typical_locations": ["Ironslag", "Volcanic regions"],
            "key_npcs": ["Duke Zalto", "Duchess Brimskarda"],
            "abilities": ["Fire immunity", "Master smithing", "Combat prowess"],
            "motivations": ["Forge the Vonindod", "Conquest", "Ancient weapons"]
        }),
        ("Frost Giant", "Brutal raiders from the frozen north", {
            "ordning_rank": 4,
            "typical_locations": ["Svardborg", "Icewind Dale", "Frozen regions"],
            "key_npcs": ["Jarl Storvald", "Harshnag"],
            "abilities": ["Cold immunity", "Ice magic", "Berserker rage"],
            "motivations": ["Raid and pillage", "Ancient relics", "Tribal dominance"]
        }),
        ("Stone Giant", "Reclusive artists and dreamers", {
            "ordning_rank": 5,
            "typical_locations": ["Underground caverns", "Stone Giant caves", "Remote mountains"],
            "key_npcs": ["Kayalithica", "Thane Kayalithica"],
            "abilities": ["Stone shaping", "Rock throwing", "Underground navigation"],
            "motivations": ["Artistic expression", "Dreams and visions", "Solitude"]
        }),
        ("Hill Giant", "Lowest in the ordning, crude and simple", {
            "ordning_rank": 6,
            "typical_locations": ["Hills", "Crude settlements", "Raiding camps"],
            "key_npcs": ["Chief Guh", "Various tribal chiefs"],
            "abilities": ["Brute strength", "Pack tactics", "Crude weapons"],
            "motivations": ["Food", "Simple pleasures", "Following stronger giants"]
        })
    ]
    
    for giant_name, description, details in giants_data:
        cursor.execute('''
            INSERT OR IGNORE INTO campaign_constants 
            (setting_name, category, name, description, details, importance)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("Storm King's Thunder", "Giants", giant_name, description, json.dumps(details), "major"))
    
    # Important Locations
    locations_data = [
        ("Nightstone", "Small village attacked by cloud giants", {
            "region": "Sword Coast",
            "population": "~40 (before attack)",
            "notable_features": ["Bridge", "Tower", "Inn"],
            "current_threat": "Orc occupation",
            "significance": "Starting location for many campaigns"
        }),
        ("Waterdeep", "The City of Splendors", {
            "region": "Sword Coast",
            "population": "~1,000,000",
            "government": "Masked Lords",
            "notable_features": ["Castle Waterdeep", "Harbor", "Market"],
            "significance": "Major trade hub and political center"
        }),
        ("Triboar", "Important crossroads town", {
            "region": "Sword Coast",
            "population": "~1,200",
            "notable_features": ["Crossroads", "Trading post"],
            "threats": ["Fire giant raids"],
            "significance": "Key location for giant attacks"
        }),
        ("Eye of the All-Father", "Ancient oracle of Annam", {
            "region": "High Forest",
            "type": "Ancient temple",
            "guardians": ["Oracle", "Ancient magic"],
            "significance": "Central to the campaign's resolution",
            "secrets": ["Annam's true will", "Giant history"]
        })
    ]
    
    for loc_name, description, details in locations_data:
        cursor.execute('''
            INSERT OR IGNORE INTO campaign_constants 
            (setting_name, category, name, description, details, importance)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("Storm King's Thunder", "Locations", loc_name, description, json.dumps(details), "important"))
    
    # Key NPCs
    npcs_data = [
        ("King Hekaton", "Missing Storm Giant King", {
            "race": "Storm Giant",
            "role": "King of Storm Giants",
            "status": "Missing/Captured",
            "importance": "Central to plot",
            "location": "Unknown (Kraken's Lair)",
            "personality": "Wise, just, powerful"
        }),
        ("Zephyros", "Ancient Cloud Giant Wizard", {
            "race": "Cloud Giant",
            "role": "Ally/Transport",
            "status": "Alive",
            "importance": "Major ally",
            "location": "Flying Tower",
            "personality": "Eccentric, helpful, ancient"
        }),
        ("Harshnag", "Frost Giant Ally", {
            "race": "Frost Giant",
            "role": "Guide/Ally",
            "status": "Alive",
            "importance": "Major ally",
            "personality": "Noble, honorable, helpful"
        })
    ]
    
    for npc_name, description, details in npcs_data:
        cursor.execute('''
            INSERT OR IGNORE INTO campaign_constants 
            (setting_name, category, name, description, details, importance)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("Storm King's Thunder", "NPCs", npc_name, description, json.dumps(details), "major"))
    
    # Plot Elements
    plot_data = [
        ("The Shattered Ordning", "The giant hierarchy has collapsed", {
            "cause": "King Hekaton's disappearance",
            "effect": "Giants raid indiscriminately",
            "resolution": "Restore King Hekaton or establish new order",
            "importance": "Central plot"
        }),
        ("The Vonindod", "Ancient giant construct", {
            "creator": "Ancient Fire Giants",
            "purpose": "Weapon against dragons",
            "current_status": "Being rebuilt by Duke Zalto",
            "threat_level": "Critical if completed"
        }),
        ("Kraken Society", "Secret organization", {
            "leader": "Slarkrethel (Kraken)",
            "goal": "Control through manipulation",
            "methods": ["Cultists", "Political infiltration"],
            "threat_to_party": "Hidden antagonist"
        })
    ]
    
    for plot_name, description, details in plot_data:
        cursor.execute('''
            INSERT OR IGNORE INTO campaign_constants 
            (setting_name, category, name, description, details, importance)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ("Storm King's Thunder", "Plot Elements", plot_name, description, json.dumps(details), "major"))

if __name__ == "__main__":
    # Test schema upgrade
    try:
        upgrade_database_schema()
        print("🎉 Schema upgrade test successful!")
    except Exception as e:
        print(f"❌ Schema upgrade test failed: {e}")
        import traceback
        traceback.print_exc()