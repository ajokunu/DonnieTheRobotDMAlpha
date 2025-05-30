# 🎲 Donnie - The AI Dungeon Master Bot

> **"Greetings, brave adventurers! I am Donnie, your AI-powered Dungeon Master ready to guide any D&D adventure!"**

[![Discord](https://img.shields.io/badge/Discord-Bot-7289da?style=for-the-badge&logo=discord)](https://discord.com/)
[![D&D 5e](https://img.shields.io/badge/D%26D-5e%202024-red?style=for-the-badge)](https://dnd.wizards.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)](https://www.python.org/)
[![Claude AI](https://img.shields.io/badge/Powered%20by-Claude%20AI-orange?style=for-the-badge)](https://anthropic.com/)

**Donnie** is a revolutionary Discord bot that serves as your personal AI Dungeon Master for D&D 5e campaigns. Featuring **expressive text-to-speech narration**, **streamlined combat**, **episode management**, **character progression tracking**, and **PDF character sheet parsing** - all powered by Claude AI for intelligent, responsive gameplay across any campaign setting.

## ✨ Key Features

### 🎤 **Voice Narration System**
- **Expressive TTS**: Donnie speaks with the "Fable" voice for dramatic storytelling
- **Optimized Speed**: Adjustable speaking speed (0.25x - 4.0x) for perfect pacing
- **Smart Audio**: Thinking sounds and natural pauses for immersion
- **Quality Modes**: Speed vs Quality audio generation based on situation

### ⚡ **Streamlined Combat**
- **Auto-Detection**: Combat triggers automatically from player actions
- **Continue Buttons**: Anyone can advance the story for faster gameplay
- **Essential Tracking**: Initiative, positions, and round counter
- **Under 700 Characters**: All responses optimized for speed

### 📺 **Episode Management**
- **Full Campaign Tracking**: Start/end episodes with persistent memory
- **AI-Generated Recaps**: Dramatic "Previously on..." style episode summaries
- **Character Snapshots**: Automatic character state saving at episode boundaries
- **Session History**: Complete action/response logs with database storage

### 📈 **Character Progression**
- **Level Tracking**: Full progression history across episodes
- **Experience Management**: Track XP gains and milestone rewards
- **Character Evolution**: See how characters develop over time
- **Party Analytics**: View entire party progression at once

### 📄 **PDF Character Sheet Parser**
- **Upload & Parse**: Drop any D&D character sheet PDF for instant character creation
- **AI-Powered Extraction**: Claude AI intelligently extracts character data
- **Confirmation System**: Review and approve parsed information
- **Manual Fallback**: Traditional character registration still available

### 💾 **Database Integration**
- **SQLite Storage**: Persistent campaign data with episode tracking
- **Character Snapshots**: Historical character states for each episode
- **Story Notes**: Player observations (marked as non-canonical)
- **Guild Settings**: Per-server configuration and preferences

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+**
- **FFmpeg** (for voice functionality)
- **Discord Bot Token**
- **Anthropic Claude API Key**
- **OpenAI API Key** (for TTS)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/donnie-bot.git
cd donnie-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Create .env file with:
DISCORD_BOT_TOKEN=your_discord_bot_token_here
ANTHROPIC_API_KEY=your_claude_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=sqlite:///data/donnie_campaign.db
ENVIRONMENT=development
AUTO_INIT_DB=true
```

4. **Initialize database**
```bash
python -c "from database import init_database; init_database()"
```

5. **Run the bot**
```bash
python main.py
```

## 🎮 Commands Guide

### 🎤 **Voice Commands**
- `/join_voice` - Donnie joins your voice channel for narration
- `/leave_voice` - Donnie leaves the voice channel
- `/mute_donnie` - Disable TTS (stay in channel)
- `/unmute_donnie` - Re-enable TTS narration
- `/donnie_speed <0.5-4.0>` - Adjust speaking speed

### 📺 **Episode Management**
- `/start_episode [name]` - Begin new episode with database tracking
- `/end_episode [summary]` - End current episode and save progress
- `/episode_recap [#] [style]` - Generate AI dramatic recaps
- `/episode_history` - View campaign timeline
- `/episode_status` - Check current episode status

### 📄 **Character Management**
- `/upload_character_sheet` - Upload PDF character sheet (AI-parsed)
- `/character` - Manual character registration
- `/party` - View all registered characters
- `/character_sheet` - View detailed character information
- `/update_character` - Modify character aspects

### 📈 **Character Progression**
- `/level_up <level> [reason]` - Level up with tracking
- `/character_progression [player]` - View progression history
- `/character_snapshot [notes]` - Manual character snapshot
- `/party_progression` - View entire party progression

### 🎮 **Core Gameplay**
- `/action <what_you_do>` - Take actions (AI DM responds with voice!)
- `/roll <dice>` - Roll dice (1d20+3, 3d6, etc.)
- `/status` - Show campaign status
- `/scene` - View current scene details

### ⚔️ **Combat Commands**
- `/combat_status` - View current combat state
- `/end_combat` - End combat encounter (Admin only)
- **Auto Combat**: Triggers automatically from hostile actions!

### 📚 **World Information**
- `/set_scene` - Update current scene (Admin)
- `/campaign` - View current campaign information
- `/help` - Comprehensive command guide

## 🏗️ Architecture

### **Core Components**
```
donnie_bot/
├── main.py                 # Main bot logic and streamlined combat
├── database/               # SQLite database management
│   ├── __init__.py        # Database initialization
│   ├── database.py        # Connection and utility functions
│   ├── models.py          # SQLAlchemy data models
│   └── operations.py      # Database operations (CRUD)
├── episode_manager/        # Episode lifecycle management
│   ├── episode_commands.py# Episode slash commands
│   ├── episode_logic.py   # Business logic validation
│   └── recap_generator.py # AI-powered recap generation
├── character_tracker/      # Character progression system
├── audio_system/          # Enhanced voice features
├── pdf_character_parser.py # PDF parsing with Claude AI
└── requirements.txt       # Python dependencies
```

### **Database Schema**
- **Episodes**: Campaign episode tracking with start/end times
- **Character Snapshots**: Historical character states per episode
- **Character Progression**: Level-up and milestone tracking
- **Story Notes**: Player observations (marked non-canonical)
- **Guild Settings**: Per-server voice and feature preferences

### **AI Integration**
- **Claude Sonnet 4**: Primary AI DM for intelligent responses
- **OpenAI TTS**: High-quality voice synthesis with "Fable" voice
- **PDF Parsing**: Claude AI extracts character data from uploaded sheets
- **Recap Generation**: AI creates dramatic episode summaries

## ⚙️ Configuration

### **Voice Settings**
```python
# Adjust in Discord with slash commands
voice_speed = 1.25  # Default speaking speed
voice_quality = "smart"  # speed/quality/smart modes
tts_enabled = True  # Per-guild TTS toggle
```

### **Database Settings**
```env
DATABASE_URL=sqlite:///data/donnie_campaign.db  # Development
# DATABASE_URL=postgresql://... # Production
ENVIRONMENT=development
AUTO_INIT_DB=true
```

### **Audio Quality Modes**
- **Speed Mode**: Fast `tts-1` for all responses
- **Quality Mode**: High-quality `tts-1-hd` for all responses  
- **Smart Mode**: Auto-selects based on content importance (default)

## 🎭 Campaign Flexibility

Donnie is designed to work with **any D&D 5e campaign setting**, featuring:

- **Adaptive Storytelling**: Claude AI adjusts to your campaign's tone and setting
- **Customizable Scenes**: DMs can set and update scenes for any adventure
- **Universal Character Support**: Works with any D&D 5e character build
- **Flexible Episode Management**: Track progress in homebrew or published campaigns
- **Setting-Agnostic Features**: All systems work regardless of campaign type

### **Default Configuration**
The bot comes pre-configured with a sample fantasy setting, but can be easily adapted for:
- **Official Campaigns**: Curse of Strahd, Tomb of Annihilation, etc.
- **Homebrew Worlds**: Custom settings and storylines
- **One-Shots**: Single session adventures
- **West Marches**: Episodic, player-driven campaigns

## 🔧 Advanced Features

### **PDF Character Sheet Parsing**
1. Upload any D&D character sheet PDF
2. Claude AI extracts all character information
3. Review and confirm parsed data
4. Automatic character registration

### **Episode Recap Generation**
- **Dramatic Style**: "Previously on [Campaign Name]..." TV-style recaps
- **Character Focus**: Highlights character development and growth
- **Story Beats**: Emphasizes plot progression and revelations
- **Quick Summary**: Bullet-point style for fast reference

### **Streamlined Combat System**
- **Keyword Detection**: Automatically detects combat initiation
- **Simple Initiative**: Auto-rolls initiative for all participants
- **Position Tracking**: Essential distance and position management
- **Continue Buttons**: Any player can advance combat for faster gameplay

### **Database Synchronization**
- **Auto-Sync**: Campaign context syncs with database automatically
- **State Recovery**: Bot remembers campaign state across restarts
- **Guild Isolation**: Each Discord server has separate campaign data

## 🛠️ Development

### **Adding New Features**
1. **Commands**: Add to appropriate module (episode_manager, character_tracker, etc.)
2. **Database**: Update models.py and operations.py for new data
3. **Voice**: Integrate with existing TTS system via `add_to_voice_queue`
4. **AI**: Use Claude client for intelligent responses

### **Testing**
```bash
# Run with debug logging
python main.py --debug

# Test database operations
python -c "from database import health_check; print(health_check())"

# Test voice system
# Use /join_voice and /action commands in Discord
```

### **Customization**
```python
# Modify campaign_context in main.py for different settings
campaign_context = {
    "campaign_name": "Your Campaign Name",
    "setting": "Your campaign setting description...",
    "current_scene": "Starting scene description...",
    # ... other settings
}
```

## 🎯 Roadmap

### **Planned Features**
- [ ] **Multi-Campaign Support**: Support multiple campaigns per server
- [ ] **Advanced Combat AI**: More sophisticated combat management
- [ ] **Campaign Templates**: Pre-built settings for popular campaigns
- [ ] **Web Dashboard**: Browser-based campaign management
- [ ] **Spell/Item Database**: Integrated D&D 5e content
- [ ] **Initiative Tracker UI**: Rich embedded interface
- [ ] **Audio Enhancement**: Custom sound effects and ambient audio

### **Performance Optimizations**
- [ ] **Response Caching**: Cache common AI responses
- [ ] **Database Optimization**: Query optimization and indexing
- [ ] **Voice Queue Management**: Smarter TTS queueing
- [ ] **Memory Usage**: Optimize campaign context storage

## 🙏 Acknowledgments

- **Anthropic Claude AI** - Powering intelligent DM responses
- **OpenAI** - Text-to-speech voice synthesis
- **Discord.py** - Discord bot framework
- **Wizards of the Coast** - D&D 5e system and mechanics
- **FFmpeg** - Audio processing capabilities

## 📞 Support

- **Issues**: Report bugs and request features through appropriate channels
- **Documentation**: Check the code comments and docstrings for detailed implementation info
- **Community**: Share experiences and improvements with other users

---

**"Every adventure needs a guide. Let me be yours."** - Donnie the DM

*Ready to embark on your AI-powered D&D adventure? Install Donnie today and experience the future of tabletop gaming!* 🎲✨
