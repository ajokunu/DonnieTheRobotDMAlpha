# 🎲 Donnie the DM - AI Dungeon Master Bot

A Discord bot that serves as an intelligent Dungeon Master for tabletop RPG campaigns, built with Clean Architecture principles for maintainability and scalability.

## ✨ Features

- **AI-Powered Storytelling**: Dynamic narrative generation using Claude AI
- **Character Management**: Persistent character creation and progression
- **Episode Tracking**: Campaign session management with memory persistence
- **Voice Integration**: Text-to-speech narration for immersive gameplay
- **Combat System**: Automated combat mechanics and dice rolling
- **Multi-Guild Support**: Independent campaigns across Discord servers

## 🏗️ Architecture

This project follows **Clean Architecture** principles to ensure maintainability, testability, and flexibility:

```
src/
├── domain/              # Core business logic (framework-independent)
│   ├── entities/        # Data models (Character, Episode, Guild, Memory)
│   ├── services/        # Business logic services
│   └── interfaces/      # Abstract contracts
├── infrastructure/      # External dependencies
│   ├── database/        # SQLite implementation
│   ├── ai/             # Claude AI integration
│   └── voice/          # Discord voice implementation
├── application/         # Use cases and orchestration
│   ├── use_cases/      # Application workflows
│   └── dto/            # Data transfer objects
├── presentation/        # Discord interface layer
│   ├── commands/       # Slash commands
│   └── events/         # Discord event handlers
└── main.py             # Dependency injection setup
```

### Key Benefits

✅ **No Circular Imports** - Clear dependency direction  
✅ **Highly Testable** - Business logic isolated from frameworks  
✅ **Maintainable** - Single responsibility per component  
✅ **Flexible** - Easy to swap AI providers or databases  
✅ **Debuggable** - Clear error boundaries between layers  
✅ **Scalable** - Add features without breaking existing code  

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Discord Bot Token
- Anthropic Claude API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/donnie-the-dm.git
   cd donnie-the-dm
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your tokens
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

### Environment Variables

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
CLAUDE_API_KEY=your_anthropic_api_key
DATABASE_PATH=./data/donnie.db
LOG_LEVEL=INFO
```

## 🎮 Usage

### Slash Commands

#### Character Management
- `/character create` - Create a new character
- `/character show` - Display character sheet
- `/character update` - Modify character attributes

#### Episode Management
- `/episode start` - Begin a new campaign session
- `/episode status` - View current episode state
- `/episode end` - Conclude current session

#### DM Tools
- `/dm narrate <text>` - Add custom narration
- `/dm roll <dice>` - Roll dice (e.g., "2d6+3")
- `/dm combat start` - Initialize combat encounter

#### Gameplay
- `/action <description>` - Perform character action
- `/say <message>` - Speak in character
- `/inspect <target>` - Examine objects or NPCs

### Example Interaction

```
Player: /action I carefully examine the ancient door for traps
Donnie: 🎲 Rolling Investigation (1d20+3): 16

As you run your fingers along the door's weathered surface, you notice 
subtle pressure plates hidden in the ornate carvings. Your keen eye 
spots thin wires leading to small holes in the frame - definitely 
trapped! The mechanism appears to be a poison dart trap.

What would you like to do next?
```

## 🔧 Development

### Project Structure

#### Domain Layer (`src/domain/`)
Contains pure business logic with no external dependencies:

```python
# Example: Character entity
@dataclass
class Character:
    id: str
    name: str
    class_type: str
    level: int
    attributes: Dict[str, int]
    
    def calculate_modifier(self, attribute: str) -> int:
        return (self.attributes[attribute] - 10) // 2
```

#### Application Layer (`src/application/`)
Orchestrates use cases and workflows:

```python
class HandleActionUseCase:
    def __init__(self, 
                 character_service: CharacterService,
                 episode_service: EpisodeService,
                 ai_service: AIServiceInterface):
        self.character_service = character_service
        self.episode_service = episode_service
        self.ai_service = ai_service
    
    async def execute(self, command: ActionCommand) -> ActionResponse:
        # Clean orchestration logic
        pass
```

#### Infrastructure Layer (`src/infrastructure/`)
Implements external service interfaces:

```python
class ClaudeAIService(AIServiceInterface):
    async def generate_response(self, context: GameContext) -> AIResponse:
        # Claude API implementation
        pass
```

### Dependency Injection

The main.py file wires all dependencies together:

```python
def create_bot() -> DiscordBot:
    # Infrastructure
    db_repo = SQLiteRepository(settings.DATABASE_PATH)
    ai_service = ClaudeAIService(settings.CLAUDE_API_KEY)
    voice_service = DiscordVoiceService()
    
    # Domain services
    character_service = CharacterService(db_repo)
    episode_service = EpisodeService(db_repo, ai_service)
    
    # Use cases
    handle_action = HandleActionUseCase(character_service, episode_service, ai_service)
    
    # Presentation
    return DiscordBot(handle_action, ...)
```

### Testing

Run the test suite:
```bash
# Unit tests (domain layer)
pytest tests/unit/

# Integration tests
pytest tests/integration/

# All tests
pytest
```

Example unit test:
```python
def test_character_modifier_calculation():
    character = Character(attributes={"strength": 16})
    assert character.calculate_modifier("strength") == 3
```

### Adding New Features

1. **Define entity/value object** in `domain/entities/`
2. **Create service interface** in `domain/interfaces/`
3. **Implement service** in `domain/services/`
4. **Add infrastructure** in `infrastructure/`
5. **Create use case** in `application/use_cases/`
6. **Add Discord command** in `presentation/commands/`
7. **Wire dependencies** in `main.py`

## 📚 API Reference

### Core Interfaces

#### AIServiceInterface
```python
class AIServiceInterface(ABC):
    @abstractmethod
    async def generate_response(self, context: GameContext) -> AIResponse:
        pass
    
    @abstractmethod
    async def generate_character(self, prompt: str) -> Character:
        pass
```

#### RepositoryInterface
```python
class RepositoryInterface(ABC):
    @abstractmethod
    async def save_character(self, character: Character) -> None:
        pass
    
    @abstractmethod
    async def get_character(self, character_id: str) -> Optional[Character]:
        pass
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the clean architecture patterns
4. Add tests for new functionality
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public methods
- Keep domain logic pure (no external dependencies)
- Use dependency injection

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Anthropic Claude](https://www.anthropic.com/) for AI capabilities
- [Discord.py](https://discordpy.readthedocs.io/) for Discord integration
- Clean Architecture principles by Robert C. Martin

## 📞 Support

- Create an [Issue](https://github.com/yourusername/donnie-the-dm/issues) for bug reports
- Join our [Discord Server](https://discord.gg/your-server) for community support
- Check the [Wiki](https://github.com/yourusername/donnie-the-dm/wiki) for detailed guides

---

*Built with ❤️ for the tabletop RPG community*