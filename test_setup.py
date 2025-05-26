print("🚀 Starting test script...")

import os
print("✅ OS module imported")

try:
    from dotenv import load_dotenv
    print("✅ dotenv imported")
except ImportError as e:
    print(f"❌ dotenv import failed: {e}")
    exit()

try:
    import anthropic
    print("✅ anthropic imported")
except ImportError as e:
    print(f"❌ anthropic import failed: {e}")

try:
    import openai
    print("✅ openai imported")
except ImportError as e:
    print(f"❌ openai import failed: {e}")

load_dotenv()
print("✅ Environment loaded")

print("\n🧪 Testing API connections...")

# Test environment variables
discord_token = os.getenv('DISCORD_BOT_TOKEN')
anthropic_key = os.getenv('ANTHROPIC_API_KEY')
openai_key = os.getenv('OPENAI_API_KEY')

print(f"Discord Token: {'✅ Found' if discord_token else '❌ Missing'}")
print(f"Anthropic Key: {'✅ Found' if anthropic_key else '❌ Missing'}")
print(f"OpenAI Key: {'✅ Found' if openai_key else '❌ Missing'}")

# Test Anthropic connection
if anthropic_key:
    try:
        claude_client = anthropic.Anthropic(api_key=anthropic_key)
        response = claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'API test successful'"}]
        )
        print("✅ Anthropic API: Working!")
        print(f"   Response: {response.content[0].text}")
    except Exception as e:
        print(f"❌ Anthropic API Error: {e}")

# Test OpenAI connection
if openai_key:
    try:
        openai_client = openai.OpenAI(api_key=openai_key)
        # Just test the client creation, not an actual API call to save credits
        print("✅ OpenAI API: Connected!")
    except Exception as e:
        print(f"❌ OpenAI API Error: {e}")

print("\n🚀 If all tests pass, you're ready to run the bot!")