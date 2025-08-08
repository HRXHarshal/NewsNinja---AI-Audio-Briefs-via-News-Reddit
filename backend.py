import os, base64, traceback
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from models import NewsRequest
from utils import (
    generate_broadcast_news,
    text_to_audio_murf,
    get_voice_for_language,
    translate_for_language,
)
from news_scraper import NewsScraper
from reddit_scraper import scrape_reddit_topics
from twitter_scraper import scrape_twitter_topics

app = FastAPI()
load_dotenv()

print(f"[{datetime.now()}] 🚀 NewsNinja Backend Starting...")
print(f"[{datetime.now()}] 📡 Environment: {os.getenv('ENVIRONMENT', 'development')}")
print(f"[{datetime.now()}] 🔑 API Keys Configured: Gemini={'✅' if os.getenv('GEMINI_API_KEY') else '❌'}, Murf={'✅' if os.getenv('MURF_API_KEY') else '❌'}")

@app.post("/generate-news-audio")
async def generate_news_audio(req: NewsRequest):
    try:
        print(f"[{datetime.now()}] 📥 RECEIVED REQUEST:")
        print(f"[{datetime.now()}]    Topics: {req.topics}")
        print(f"[{datetime.now()}]    Source Type: {req.source_type}")
        print(f"[{datetime.now()}]    Language: {req.language}")
        
        results = {}
        total_start_time = datetime.now()

        # News Scraping
        if req.source_type in {"news", "both", "all"}:
            print(f"[{datetime.now()}] 📰 STARTING NEWS SCRAPING...")
            news_start = datetime.now()
            news_scraper = NewsScraper()
            results["news"] = await news_scraper.scrape_news(req.topics)
            news_duration = (datetime.now() - news_start).total_seconds()
            print(f"[{datetime.now()}] 📰 NEWS SCRAPING COMPLETED in {news_duration:.2f}s")
            print(f"[{datetime.now()}]    News topics processed: {len(results['news']['news_analysis'])}")

        # Reddit Scraping
        if req.source_type in {"reddit", "both", "all"}:
            print(f"[{datetime.now()}] 🔴 STARTING REDDIT SCRAPING...")
            reddit_start = datetime.now()
            try:
                results["reddit"] = await scrape_reddit_topics(req.topics)
                reddit_duration = (datetime.now() - reddit_start).total_seconds()
                print(f"[{datetime.now()}] 🔴 REDDIT SCRAPING COMPLETED in {reddit_duration:.2f}s")
                print(f"[{datetime.now()}]    Reddit topics processed: {len(results['reddit']['reddit_analysis'])}")
            except Exception as e:
                print(f"[{datetime.now()}] 🔴 REDDIT SCRAPING FAILED: {str(e)}")
                results["reddit"] = {"reddit_analysis": {t: "Reddit unavailable" for t in req.topics}}

        # Twitter Scraping
        if req.source_type in {"twitter", "all"}:
            print(f"[{datetime.now()}] 🐦 STARTING TWITTER SCRAPING...")
            twitter_start = datetime.now()
            try:
                results["twitter"] = await scrape_twitter_topics(req.topics)
                twitter_duration = (datetime.now() - twitter_start).total_seconds()
                print(f"[{datetime.now()}] 🐦 TWITTER SCRAPING COMPLETED in {twitter_duration:.2f}s")
                print(f"[{datetime.now()}]    Twitter topics processed: {len(results['twitter']['twitter_analysis'])}")
            except Exception as e:
                print(f"[{datetime.now()}] 🐦 TWITTER SCRAPING FAILED: {str(e)}")
                results["twitter"] = {"twitter_analysis": {t: "Twitter unavailable" for t in req.topics}}

        # Summary Generation
        print(f"[{datetime.now()}] ✨ GENERATING BROADCAST SUMMARY...")
        summary_start = datetime.now()
        summary_en = generate_broadcast_news(
            api_key=os.getenv("GEMINI_API_KEY"),
            news_data=results.get("news"),
            reddit_data=results.get("reddit"),
            twitter_data=results.get("twitter"),
            topics=req.topics,
        )
        summary_duration = (datetime.now() - summary_start).total_seconds()
        print(f"[{datetime.now()}] ✨ SUMMARY GENERATED in {summary_duration:.2f}s")
        print(f"[{datetime.now()}]    Summary length: {len(summary_en)} characters")

        # Translation
        if req.language != "en-US":
            print(f"[{datetime.now()}] 🌐 TRANSLATING TO {req.language}...")
            translate_start = datetime.now()
            final_summary = translate_for_language(os.getenv("GEMINI_API_KEY"), summary_en, req.language)
            translate_duration = (datetime.now() - translate_start).total_seconds()
            print(f"[{datetime.now()}] 🌐 TRANSLATION COMPLETED in {translate_duration:.2f}s")
        else:
            final_summary = summary_en
            print(f"[{datetime.now()}] 🌐 NO TRANSLATION NEEDED (English)")

        # Audio Generation
        print(f"[{datetime.now()}] 🔊 GENERATING AUDIO...")
        audio_start = datetime.now()
        voice_id = get_voice_for_language(req.language)
        audio_path = text_to_audio_murf(
            text=final_summary,
            voice_id=voice_id,
            language=req.language,
            output_dir="audio",
        )
        audio_duration = (datetime.now() - audio_start).total_seconds()
        print(f"[{datetime.now()}] 🔊 AUDIO GENERATED in {audio_duration:.2f}s")
        print(f"[{datetime.now()}]    Audio file: {audio_path}")

        if not (audio_path and Path(audio_path).exists()):
            raise RuntimeError("Audio generation failed")

        # Encoding
        print(f"[{datetime.now()}] 📊 ENCODING AUDIO FOR RESPONSE...")
        audio_b64 = base64.b64encode(Path(audio_path).read_bytes()).decode()
        audio_size_mb = len(audio_b64) * 0.75 / 1024 / 1024  # Approximate size
        print(f"[{datetime.now()}] 📊 AUDIO ENCODED: {audio_size_mb:.2f} MB")

        total_duration = (datetime.now() - total_start_time).total_seconds()
        print(f"[{datetime.now()}] ✅ REQUEST COMPLETED in {total_duration:.2f}s")

        return JSONResponse({
            "summary_text": final_summary,
            "audio_content": audio_b64,
            "metadata": {
                "topics": req.topics,
                "sources": req.source_type,
                "language": req.language,
                "processing_time": total_duration
            }
        })

    except Exception as e:
        print(f"[{datetime.now()}] ❌ ERROR: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=1234, reload=True)
