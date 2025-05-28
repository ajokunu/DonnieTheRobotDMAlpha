# setup_audio_assets.py
"""
Script to set up the audio assets directory structure and create placeholder sound files
Run this once to set up your audio system: python setup_audio_assets.py
"""

import os
from pathlib import Path

def create_audio_directory_structure():
    """Create the directory structure for audio assets"""
    base_path = Path("audio_assets")
    
    directories = [
        "dice_rolls",
        "papers", 
        "dm_reactions",
        "ambient"
    ]
    
    for directory in directories:
        dir_path = base_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")
    
    return base_path

def create_placeholder_sound_files(base_path: Path):
    """Create placeholder sound files (you'll need to replace these with real audio)"""
    
    sound_files = {
        "dice_rolls": [
            "d20_roll_1.mp3", "d20_roll_2.mp3", "d20_roll_3.mp3",
            "multi_dice_1.mp3", "multi_dice_2.mp3"
        ],
        "papers": [
            "page_turn_1.mp3", "page_turn_2.mp3", 
            "paper_rustle_1.mp3", "paper_rustle_2.mp3",
            "book_flip_1.mp3"
        ],
        "dm_reactions": [
            "throat_clear_1.mp3", "throat_clear_2.mp3",
            "sharp_breath_1.mp3", "sharp_breath_2.mp3", 
            "thinking_hum_1.mp3", "thinking_hum_2.mp3",
            "tongue_click_1.mp3"
        ],
        "ambient": [
            "chair_creak_1.mp3", "chair_creak_2.mp3",
            "quiet_movement_1.mp3", "room_tone_1.mp3"
        ]
    }
    
    print("\n📁 Creating placeholder files...")
    for category, files in sound_files.items():
        category_path = base_path / category
        for filename in files:
            file_path = category_path / filename
            if not file_path.exists():
                # Create empty placeholder file
                file_path.touch()
                print(f"📄 Created placeholder: {file_path}")

def show_next_steps():
    """Show instructions for what to do next"""
    print("\n" + "="*60)
    print("🎵 AUDIO SETUP COMPLETE!")
    print("="*60)
    
    print("\n📁 Directory structure created:")
    print("audio_assets/")
    print("├── dice_rolls/     (dice rolling sounds)")
    print("├── papers/         (page turning, rustling)")
    print("├── dm_reactions/   (thinking sounds, throat clearing)")
    print("└── ambient/        (chair creaks, room sounds)")
    
    print("\n⚠️  IMPORTANT: Replace placeholder files with real audio!")
    print("\n🎵 AUDIO REQUIREMENTS:")
    print("• File format: MP3 (recommended)")
    print("• Length: 0.5-4 seconds each")
    print("• Quality: Clear, not too loud")
    print("• Realistic: Actual sounds, not spoken descriptions")
    
    print("\n🎤 WHERE TO GET AUDIO:")
    print("\n1. 📱 RECORD YOURSELF (EASIEST):")
    print("   • Use phone voice recorder")
    print("   • Roll actual dice on table")
    print("   • Flip through book pages")
    print("   • Natural 'hmm', throat clearing")
    print("   • Chair creaking, quiet movement")
    
    print("\n2. 🌐 FREE SOUND LIBRARIES:")
    print("   • freesound.org (search: dice roll, page turn)")
    print("   • YouTube Audio Library")
    print("   • zapsplat.com (free tier)")
    
    print("\n3. 🤖 AI GENERATION:")
    print("   • elevenlabs.io sound effects")
    print("   • Use AI voice generators for thinking sounds")
    
    print("\n🚀 TESTING:")
    print("1. Start your bot: python main.py")
    print("2. Look for: '✅ Enhanced voice system initialized'")
    print("3. Use: /join_voice then /action <something>")
    print("4. Listen for sound effects before Donnie speaks!")
    
    print("\n💡 TIP: Start with just 2-3 files in each category")
    print("   You can add more variations later!")

def main():
    print("🎵 Setting up Enhanced Donnie Audio System...")
    print("This will create directories and placeholder files for sound effects.")
    
    # Create directories
    base_path = create_audio_directory_structure()
    
    # Create placeholder files
    create_placeholder_sound_files(base_path)
    
    # Show next steps
    show_next_steps()
    
    print(f"\n✅ Setup complete! Audio assets directory created at: {base_path.absolute()}")
    print("🎵 Don't forget to add real audio files to replace the placeholders!")

if __name__ == "__main__":
    main()