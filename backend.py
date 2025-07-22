import os
import traceback
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import base64

from models import NewsRequest
from utils import generate_broadcast_news, text_to_audio_murf
from news_scraper import NewsScraper
from reddit_scraper import scrape_reddit_topics

app = FastAPI()
load_dotenv()

@app.post("/generate-news-audio")
async def generate_news_audio(request: NewsRequest):
    try:
        print(f"[{datetime.now()}] Received request for /generate-news-audio with topics: {request.topics}, source_type: {request.source_type}")
        results = {}
        
        if request.source_type in ["news", "both"]:
            print(f"[{datetime.now()}] Starting news scraping for topics: {request.topics}")
            news_scraper = NewsScraper()
            results["news"] = await news_scraper.scrape_news(request.topics)
            print(f"[{datetime.now()}] News scraping completed. Results: {results.get('news', 'No news data')}")
        
        if request.source_type in ["reddit", "both"]:
            try:
                print(f"[{datetime.now()}] Starting Reddit scraping for topics: {request.topics}")
                results["reddit"] = await scrape_reddit_topics(request.topics)
                print(f"[{datetime.now()}] Reddit scraping completed. Results: {results.get('reddit', 'No Reddit data')}")
            except Exception as e:
                print(f"[{datetime.now()}] Reddit scraping failed: {str(e)}")
                results["reddit"] = {"reddit_analysis": {topic: f"Could not analyze Reddit discussions about {topic}" 
                                      for topic in request.topics}}

        news_data = results.get("news", {})
        reddit_data = results.get("reddit", {})
        
        print(f"[{datetime.now()}] News data for broadcast: {news_data}")
        print(f"[{datetime.now()}] Reddit data for broadcast: {reddit_data}")

        print(f"[{datetime.now()}] Generating broadcast news summary...")
        news_summary = generate_broadcast_news(
            api_key=os.getenv("GEMINI_API_KEY"),
            news_data=news_data,
            reddit_data=reddit_data,
            topics=request.topics
        )
        print(f"[{datetime.now()}] Broadcast news summary generated. Length: {len(news_summary)} characters")
        print(f"[{datetime.now()}] Summary snippet (first 500 chars):\n{news_summary[:500]}...")

        print(f"[{datetime.now()}] Converting news summary to audio using Murf AI...")
        audio_path = text_to_audio_murf(
            text=news_summary,
            output_dir="audio"
        )
        print(f"[{datetime.now()}] Audio generation completed. Audio path: {audio_path}")

        if audio_path and Path(audio_path).exists():
            print(f"[{datetime.now()}] Reading audio file from {audio_path}...")
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
            
            # Encode audio to base64 to send in JSON response
            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
            
            print(f"[{datetime.now()}] Audio file read and encoded. Returning JSON response.")
            return JSONResponse(
                content={
                    "summary_text": news_summary,
                    "audio_content": audio_base64
                }
            )
        else:
            print(f"[{datetime.now()}] Audio file not found or path is invalid: {audio_path}")
            raise HTTPException(status_code=500, detail="Failed to generate audio file.")
    
    except Exception as e:
        print(f"[{datetime.now()}] Unhandled exception in /generate-news-audio: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend:app",
        host="0.0.0.0",
        port=1234,
        reload=True
    )