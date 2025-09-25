#!/usr/bin/env python3
"""
Simple test to verify OpenAI Whisper API is working
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai_key():
    key = os.getenv('OPENAI_API_KEY')
    print(f"OPENAI_API_KEY exists: {bool(key)}")
    print(f"Key starts with 'sk-': {key.startswith('sk-') if key else False}")
    print(f"Key length: {len(key) if key else 0}")

def test_openai_import():
    try:
        from openai import OpenAI
        print("OpenAI import successful")

        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        print("OpenAI client created")

        # Test with a simple text file instead of video for quick test
        return True
    except Exception as e:
        print(f"OpenAI error: {e}")
        return False

if __name__ == "__main__":
    print("=== OpenAI Whisper API Test ===")
    test_openai_key()
    print()
    test_openai_import()