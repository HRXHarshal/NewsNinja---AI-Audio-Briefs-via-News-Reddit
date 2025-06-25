import asyncio
import os
from typing import Dict, List
from datetime import datetime # Import datetime for timestamping prints

from aiolimiter import AsyncLimiter
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

from utils import (
    generate_news_urls_to_scrape,
    scrape_with_brightdata,
    clean_html_to_text,
    extract_headlines,
    summarize_with_gemini_news_script,
    summarize_with_ollama
)

load_dotenv()


class NewsScraper:
    _rate_limiter = AsyncLimiter(5, 1)  # 5 requests/second

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def scrape_news(self, topics: List[str]) -> Dict[str, str]:
        """Scrape and analyze news articles"""
        results = {}
        
        for topic in topics:
            async with self._rate_limiter:
                try:
                    print(f"[{datetime.now()}] NewsScraper: Processing topic: {topic}")
                    urls = generate_news_urls_to_scrape([topic])
                    
                    # Debugging for Bright Data scraping
                    print(f"[{datetime.now()}] NewsScraper: Attempting to scrape with Bright Data for URL: {urls[topic]}")
                    try:
                        search_html = scrape_with_brightdata(urls[topic])
                        print(f"[{datetime.now()}] NewsScraper: Bright Data content accessed successfully for topic: {topic}")
                    except Exception as bright_error:
                        print(f"[{datetime.now()}] NewsScraper: Bright Data scraping failed for {topic}: {str(bright_error)}")
                        print(f"[{datetime.now()}] NewsScraper: Using fallback method with direct requests for {topic}...")
                        # Fallback to a simpler approach
                        import requests # Import requests here if not already imported globally
                        search_html = requests.get(urls[topic], headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                        }).text
                        print(f"[{datetime.now()}] NewsScraper: Fallback scraping completed for {topic}.")
                    
                    clean_text = clean_html_to_text(search_html)
                    print(f"[{datetime.now()}] NewsScraper: HTML cleaned for {topic}. Text length: {len(clean_text)}")
                    headlines = extract_headlines(clean_text)
                    print(f"[{datetime.now()}] NewsScraper: Headlines extracted for {topic}. Headlines snippet: {headlines[:100]}...")
                    
                    if not headlines or headlines.strip() == "":
                        print(f"[{datetime.now()}] NewsScraper: No headlines found for {topic}, using topic as headline.")
                        headlines = f"Latest news about {topic}"
                    
                    print(f"[{datetime.now()}] NewsScraper: Summarizing news script for {topic} with Gemini...")
                    summary = summarize_with_gemini_news_script(
                        api_key=os.getenv("GEMINI_API_KEY"), # Changed to use GEMINI_API_KEY
                        headlines=headlines
                    )
                    print(f"[{datetime.now()}] NewsScraper: News script summarized for {topic}. Summary length: {len(summary)}")
                    results[topic] = summary
                except Exception as e:
                    print(f"[{datetime.now()}] NewsScraper: Error processing topic {topic}: {str(e)}")
                    results[topic] = f"We couldn't retrieve the latest news about {topic} at this time."
                await asyncio.sleep(1)  # Avoid overwhelming news sites
    
        print(f"[{datetime.now()}] NewsScraper: All topics processed. Returning news analysis results.")
        return {"news_analysis" : results}