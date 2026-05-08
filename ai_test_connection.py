"""
ai_test_connection.py — A simple script to verify the OpenRouter API connection
before integrating it into the main application logic.
"""

import config
from openai import OpenAI

def test_openrouter():
    print("=" * 50)
    print("🤖 Testing OpenRouter AI Connection...")
    print("=" * 50)

    if not config.OPENROUTER_API_KEY:
        print("❌ ERROR: OPENROUTER_API_KEY is not set in your .env file.")
        print("Please add your key to continue testing.")
        return

    print(f"Using Model: {config.LLM_MODEL}")
    
    # Initialize the OpenAI client pointing to OpenRouter
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=config.OPENROUTER_API_KEY,
    )

    try:
        print("Sending a ping to the LLM...")
        
        # Send a simple test message
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {
                    "role": "user", 
                    "content": "Hello! In one short sentence, confirm that you are ready to act as a PostgreSQL DBA for NAPA's maritime database."
                }
            ],
            max_tokens=60
        )
        
        print("\n✅ SUCCESS! Received response from AI:")
        print("-" * 50)
        print(response.choices[0].message.content)
        print("-" * 50)
        
    except Exception as e:
        print(f"\n❌ FAILED to connect to OpenRouter: {e}")

if __name__ == "__main__":
    test_openrouter()