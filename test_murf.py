#!/usr/bin/env python3
"""
Simple Murf API Test
Quick test to identify the exact issue with your Murf API integration.
"""

import os
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

def test_murf_simple():
    """Simple test to diagnose the specific issue"""

    print("🧪 SIMPLE MURF API TEST")
    print("=" * 40)

    # Load environment variables
    load_dotenv()
    api_key = os.getenv("MURF_API_KEY")

    if not api_key:
        print("❌ MURF_API_KEY not found in .env file")
        return False

    print(f"✅ API Key found: {api_key[:10]}...")

    try:
        from murf import Murf
        print("✅ Murf package imported successfully")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Run: pip install murf")
        return False

    try:
        client = Murf(api_key=api_key)
        print("✅ Murf client initialized")
    except Exception as e:
        print(f"❌ Client initialization failed: {e}")
        return False

    print("\n🎤 Generating speech...")
    try:
        response = client.text_to_speech.generate(
            text="Hello world! This is a test of the Murf AI text to speech system.",
            voice_id="en-US-natalie",
            format="MP3",
            sample_rate=44100.0,
        )

        print("✅ Speech generation successful")

        print("\n🔍 DEBUGGING RESPONSE:")
        print(f"Response type: {type(response)}")
        print(f"Response dir: {[attr for attr in dir(response) if not attr.startswith('_')]}")

        if hasattr(response, '__dict__'):
            print(f"Response dict: {response.__dict__}")

        print("\n💾 Downloading audio...")

        # THE CORRECT WAY: Use 'audio_file' attribute, not 'audio_url'
        audio_url = None

        if hasattr(response, 'audio_file') and response.audio_file:
            audio_url = response.audio_file
            print(f"✅ Found audio_file attribute: {audio_url[:60]}...")
        elif hasattr(response, 'url') and response.url:
            audio_url = response.url
            print(f"✅ Found url attribute: {audio_url[:60]}...")
        else:
            print("❌ ERROR: Cannot find audio URL in response")
            print("🔍 This indicates the response structure is different than expected")
            return False

        # Download the audio
        audio_response = requests.get(audio_url)
        audio_response.raise_for_status()

        # Save to file
        output_dir = Path("audio")
        output_dir.mkdir(exist_ok=True)

        filename = f"simple_test_{datetime.now().strftime('%H%M%S')}.mp3"
        filepath = output_dir / filename

        with open(filepath, "wb") as f:
            f.write(audio_response.content)

        file_size = filepath.stat().st_size
        print(f"✅ Audio saved: {filepath} ({file_size:,} bytes)")

        if file_size > 0:
            print("\n🎉 SUCCESS! Murf API is working correctly")
            print("\n📝 KEY FINDING:")
            print("   The response uses 'audio_file' attribute, not 'audio_url'")
            print("   Update your code to use: response.audio_file")
        else:
            print("❌ Audio file is empty - there may still be an issue")

        return True

    except Exception as e:
        print(f"❌ ERROR: {e}")
        print("\n📝 Common solutions:")
        print("   1. Verify MURF_API_KEY in .env file")
        print("   2. Run: pip install murf")
        print("   3. Check your Murf API account has credits")
        print("   4. Verify your API key is active")
        return False

if __name__ == "__main__":
    success = test_murf_simple()
    if success:
        print("\n💥 PASSED! Check the errors above")
    else:
        print("\n💥 FAILED! Check the errors above")
