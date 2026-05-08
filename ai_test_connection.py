"""
ai_test_connection.py — A simple script to verify the OpenRouter API connection
and test the advanced 'Reasoning' capabilities of the LLM.
"""

import config
from openai import OpenAI

def test_openrouter():
    print("=" * 50)
    print("🧠 Testing OpenRouter AI Reasoning Capabilities...")
    print("=" * 50)

    if not config.OPENROUTER_API_KEY:
        print("❌ ERROR: OPENROUTER_API_KEY is not set.")
        return

    print(f"Using Model: {config.LLM_MODEL}")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=config.OPENROUTER_API_KEY,
    )

    try:
        print("Asking the famous 'Strawberry' logic question...")

        # Send the request
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": "How many r's are in the word 'strawberry'? Think step-by-step."
                }
            ],
            temperature=1,
            # extra_body passes OpenRouter-specific params through the OpenAI SDK
            extra_body={
                # "include_reasoning: True" is the OLD deprecated approach.
                # The correct modern parameter is "reasoning" with an effort level.
                "reasoning": {
                    "effort": "high"  # "low", "medium", or "high"
                }
            }
        )
        
        # Convert the OpenAI object to a raw Python dictionary
        # to expose hidden OpenRouter-specific fields like 'reasoning'
        raw_response = response.model_dump()
        message_data = raw_response['choices'][0]['message']

        print("\n✅ SUCCESS! Here is what happened:")
        print("-" * 50)

        # 1. Print the Reasoning (Inner Monologue)
        # OpenRouter puts this in a 'reasoning' field if the model supports it
        reasoning = message_data.get('reasoning')
        if reasoning:
            print("🧠 AI'S INTERNAL THOUGHT PROCESS:")
            print(reasoning.strip())
            print("-" * 50)
        else:
            print("🧠 No native reasoning tokens found (model may not support it).")
            print("-" * 50)

        # 2. Print the Final Answer
        print("🗣️ AI'S FINAL ANSWER:")
        print(message_data.get('content').strip())
        print("-" * 50)

        # 3. Print Token Usage
        usage = raw_response.get('usage', {})
        print(f"📊 Token Usage: {usage.get('total_tokens')} total tokens used.")

    except Exception as e:
        print(f"\n❌ FAILED to connect to OpenRouter: {e}")

if __name__ == "__main__":
    test_openrouter()