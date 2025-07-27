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

app = FastAPI()
load_dotenv()

@app.post("/generate-news-audio")
async def generate_news_audio(req: NewsRequest):
    try:
        print(f"[{datetime.now()}] /generate-news-audio → {req.dict()}")
        results = {}

        if req.source_type in {"news", "both"}:
            news_scraper = NewsScraper()
            results["news"] = await news_scraper.scrape_news(req.topics)

        if req.source_type in {"reddit", "both"}:
            try:
                results["reddit"] = await scrape_reddit_topics(req.topics)
            except Exception as e:
                print("Reddit scrape failed:", e)
                results["reddit"] = {"reddit_analysis": {t: "Reddit unavailable" for t in req.topics}}

        summary_en = generate_broadcast_news(
            api_key=os.getenv("GEMINI_API_KEY"),
            news_data=results.get("news"),
            reddit_data=results.get("reddit"),
            topics=req.topics,
        )

        # Translate if needed
        final_summary = translate_for_language(os.getenv("GEMINI_API_KEY"), summary_en, req.language)

        voice_id = get_voice_for_language(req.language)
        audio_path = text_to_audio_murf(
            text=final_summary,
            voice_id=voice_id,
            language=req.language,
            output_dir="audio",
        )

        if not (audio_path and Path(audio_path).exists()):
            raise RuntimeError("Audio generation failed")

        audio_b64 = base64.b64encode(Path(audio_path).read_bytes()).decode()
        return JSONResponse({"summary_text": final_summary, "audio_content": audio_b64})

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=1234, reload=True)
