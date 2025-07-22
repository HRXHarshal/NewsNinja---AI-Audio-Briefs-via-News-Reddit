from urllib.parse import quote_plus
from dotenv import load_dotenv
import requests
import os
import time
from murf import Murf
from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup
import ollama
import google.generativeai as genai
from datetime import datetime
from pathlib import Path
from gtts import gTTS

load_dotenv()

class MCPOverloadedError(Exception):
    """Custom exception for MCP service overloads"""
    pass

def generate_valid_news_url(keyword: str) -> str:
    """
    Generate a Google News search URL for a keyword with optional sorting by latest
    Args:
        keyword: Search term to use in the news search
    Returns:
        str: Constructed Google News search URL
    """
    q = quote_plus(keyword)
    return f"https://news.google.com/search?q={q}&tbs=sbd:1"

def generate_news_urls_to_scrape(list_of_keywords):
    valid_urls_dict = {}
    for keyword in list_of_keywords:
        valid_urls_dict[keyword] = generate_valid_news_url(keyword)
    return valid_urls_dict

def scrape_with_brightdata(url: str) -> str:
    """Scrape a URL using BrightData"""
    headers = {
        "Authorization": f"Bearer {os.getenv('BRIGHTDATA_MCP_KEY')}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "zone": os.getenv('WEB_UNLOCKER_ZONE'),
        "url": url,
        "format": "raw"
    }
    
    try:
        print(f"[{datetime.now()}] BrightData: Sending request to BrightData API for URL: {url}")
        response = requests.post("https://api.brightdata.com/request", json=payload, headers=headers)
        response.raise_for_status()
        print(f"[{datetime.now()}] BrightData: BrightData content accessed successfully for URL: {url}")
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now()}] BrightData: Error scraping with BrightData for URL {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"BrightData error: {str(e)}")

def clean_html_to_text(html_content: str) -> str:
    """Clean HTML content to plain text"""
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text(separator="\n")
    return text.strip()

def extract_headlines(cleaned_text: str) -> str:
    """
    Extract and concatenate headlines from cleaned news text content.
    Args:
        cleaned_text: Raw text from news page after HTML cleaning
    Returns:
        str: Combined headlines separated by newlines
    """
    headlines = []
    current_block = []
    
    # Split text into lines and remove empty lines
    lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]
    
    # Process lines to find headline blocks
    for line in lines:
        if line == "More":
            if current_block:
                # First line of block is headline
                headlines.append(current_block[0])
                current_block = []
        else:
            current_block.append(line)
    
    # Add any remaining block at end of text
    if current_block:
        headlines.append(current_block[0])
    
    return "\n".join(headlines)

def summarize_with_ollama(headlines) -> str:
    """Summarize content using Ollama"""
    prompt = f"""You are my personal news editor. Summarize these headlines into a TV news script for me, focus on important headlines and remember that this text will be converted to audio:

So no extra stuff other than text which the podcaster/newscaster should read, no special symbols or extra information in between and of course no preamble please.

{headlines}

News Script:"""
    
    try:
        print(f"[{datetime.now()}] Ollama: Summarizing with Ollama...")
        client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
        
        # Generate response using the Ollama client
        response = client.generate(
            model="llama3.2",
            prompt=prompt,
            options={
                "temperature": 0.4,
                "max_tokens": 800
            },
            stream=False
        )
        
        print(f"[{datetime.now()}] Ollama: Summary generated.")
        return response['response']
    
    except Exception as e:
        print(f"[{datetime.now()}] Ollama: Error summarizing with Ollama: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")

def generate_broadcast_news(api_key, news_data, reddit_data, topics):
    """Generate broadcast news using Google Gemini 2.5 Flash"""
    system_prompt = """
You are broadcast_news_writer, a professional virtual news reporter. Generate natural, TTS-ready news reports using available sources:

For each topic, STRUCTURE BASED ON AVAILABLE DATA:
1. If news exists: "According to official reports..." + summary
2. If Reddit exists: "Online discussions on Reddit reveal..." + summary  
3. If both exist: Present news first, then Reddit reactions
4. If neither exists: Skip the topic (shouldn't happen)

Formatting rules:
- ALWAYS start directly with the content, NO INTRODUCTIONS
- Keep audio length 60-120 seconds per topic
- Use natural speech transitions like "Meanwhile, online discussions..."
- Incorporate 1-2 short quotes from Reddit when available
- Maintain neutral tone but highlight key sentiments
- End with "To wrap up this segment..." summary

Write in full paragraphs optimized for speech synthesis. Avoid markdown.
"""
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        topic_blocks = []
        for topic in topics:
            news_content = news_data["news_analysis"].get(topic) if news_data else ''
            reddit_content = reddit_data["reddit_analysis"].get(topic) if reddit_data else ''
            
            context = []
            if news_content:
                context.append(f"OFFICIAL NEWS CONTENT:\n{news_content}")
            if reddit_content:
                context.append(f"REDDIT DISCUSSION CONTENT:\n{reddit_content}")
            
            if context:
                topic_blocks.append(
                    f"TOPIC: {topic}\n\n" + 
                    "\n\n".join(context)
                )
        
        user_prompt = (
            "Create broadcast segments for these topics using available sources:\n\n" +
            "\n\n--- NEW TOPIC ---\n\n".join(topic_blocks)
        )
        
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        print(f"[{datetime.now()}] Gemini (Broadcast News): Invoking Gemini for broadcast news generation...")
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=4000,
            )
        )
        
        print(f"[{datetime.now()}] Gemini (Broadcast News): Broadcast news generated.")
        return response.text
        
    except Exception as e:
        print(f"[{datetime.now()}] Gemini (Broadcast News): Error generating broadcast news: {str(e)}")
        raise e

def summarize_with_gemini_news_script(api_key: str, headlines: str) -> str:
    """
    Summarize multiple news headlines into a TTS-friendly broadcast news script using Google Gemini 2.5 Flash.
    """
    system_prompt = """
You are my personal news editor and scriptwriter for a news podcast. Your job is to turn raw headlines into a clean, professional, and TTS-friendly news script.

The final output will be read aloud by a news anchor or text-to-speech engine. So:
- Do not include any special characters, emojis, formatting symbols, or markdown.
- Do not add any preamble or framing like "Here's your summary" or "Let me explain".
- Write in full, clear, spoken-language paragraphs.
- Keep the tone formal, professional, and broadcast-style — just like a real TV news script.
- Focus on the most important headlines and turn them into short, informative news segments that sound natural when spoken.
- Start right away with the actual script, using transitions between topics if needed.

Remember: Your only output should be a clean script that is ready to be read out loud.
"""
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        full_prompt = f"{system_prompt}\n\n{headlines}"
        
        print(f"[{datetime.now()}] Gemini (News Script): Invoking Gemini for news script summarization...")
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=1000,
            )
        )
        
        print(f"[{datetime.now()}] Gemini (News Script): News script summarized.")
        return response.text
        
    except Exception as e:
        print(f"[{datetime.now()}] Gemini (News Script): Error summarizing news script: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gemini error: {str(e)}")

def text_to_audio_murf(
    text: str,
    voice_id: str = "en-US-natalie",
    format_type: str = "MP3",
    sample_rate: float = 44100.0,
    output_dir: str = "audio",
    api_key: str = None,
    channel_type: str = "STEREO",
    pitch: int = 0,
    rate: float = 1.0,
    style: str = None
) -> str:
    """
    Converts text to speech using Murf API and saves it to audio/ directory.
    
    Args:
        text: The text to be converted to speech
        voice_id: Murf voice ID (e.g., "en-US-natalie", "en-US-cooper")
        format_type: Audio format (MP3, WAV, FLAC, ALAW, ULAW)
        sample_rate: Audio sample rate (8000, 24000, 44100, 48000)
        output_dir: Directory to save the audio file
        api_key: Murf API key (will use MURF_API_KEY env var if not provided)
        channel_type: STEREO or MONO
        pitch: Voice pitch adjustment (-50 to 50)
        rate: Speech rate multiplier (0.5 to 2.0)
        style: Voice style for generation
        
    Returns:
        str: Path to the saved audio file.
    """
    try:
        api_key = api_key or os.getenv("MURF_API_KEY")
        if not api_key:
            print(f"[{datetime.now()}] Murf: MURF_API_KEY is missing.")
            raise ValueError("Murf API key is required.")

        print(f"[{datetime.now()}] Murf: Initializing Murf client...")
        client = Murf(api_key=api_key)

        print(f"[{datetime.now()}] Murf: Converting text to speech...")
        
        # Prepare generation parameters
        generation_params = {
            "text": text,
            "voice_id": voice_id,
            "format": format_type,
            "sample_rate": sample_rate,
            "channel_type": channel_type,
            "pitch": pitch,
            "rate": rate
        }
        
        # Add style if provided
        if style:
            generation_params["style"] = style
        
        # Generate speech using Murf API
        response = client.text_to_speech.generate(**generation_params)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        filepath = os.path.join(output_dir, filename)

        print(f"[{datetime.now()}] Murf: Downloading audio file to: {filepath}")

        # Based on your successful debugging output, the response has 'audio_file' attribute
        if hasattr(response, 'audio_file') and response.audio_file:
            print(f"[{datetime.now()}] Murf: Downloading from audio_file URL...")
            audio_response = requests.get(response.audio_file)
            audio_response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(audio_response.content)
                
            print(f"[{datetime.now()}] Murf: Audio file saved successfully.")
            return filepath
        else:
            # Fallback: try other possible response structures
            if hasattr(response, 'audio_url') and response.audio_url:
                print(f"[{datetime.now()}] Murf: Downloading from audio_url...")
                audio_response = requests.get(response.audio_url)
                audio_response.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(audio_response.content)
                return filepath
            elif hasattr(response, 'url') and response.url:
                print(f"[{datetime.now()}] Murf: Downloading from url...")
                audio_response = requests.get(response.url)
                audio_response.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(audio_response.content)
                return filepath
            else:
                print(f"[{datetime.now()}] Murf: ERROR - Could not find audio URL in response")
                print(f"[{datetime.now()}] DEBUG: Available response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")
                raise Exception("Murf API did not provide an audio URL or file.")

    except Exception as e:
        print(f"[{datetime.now()}] Murf: Error converting text to audio: {str(e)}")
        raise e

def tts_to_audio(text: str, language: str = 'en') -> str:
    """
    Convert text to speech using gTTS (Google Text-to-Speech) and save to file.
    """
    try:
        print(f"[{datetime.now()}] gTTS: Converting text to speech with gTTS...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create audio directory if it doesn't exist
        audio_dir = Path("audio")
        audio_dir.mkdir(exist_ok=True)
        
        filename = audio_dir / f"tts_{timestamp}.mp3"
        
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(str(filename))
        
        print(f"[{datetime.now()}] gTTS: Audio file saved successfully to {filename}.")
        return str(filename)
        
    except Exception as e:
        print(f"[{datetime.now()}] gTTS: Error converting text to audio with gTTS: {str(e)}")
        return None

# Create audio directory
AUDIO_DIR = Path("audio")
AUDIO_DIR.mkdir(exist_ok=True)