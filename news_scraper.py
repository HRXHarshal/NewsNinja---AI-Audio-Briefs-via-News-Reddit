# Import asyncio for asynchronous operations
import asyncio
# Import os for environment variable access
import os
# Import Dict and List for type hinting
from typing import Dict, List
# Import datetime for logging timestamps
from datetime import datetime

# Import AsyncLimiter for rate limiting API calls
from aiolimiter import AsyncLimiter
# Import retry decorators for handling failures
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
# Import load_dotenv for environment variable loading
from dotenv import load_dotenv

# Import utility functions for news scraping
from utils import (
    generate_news_urls_to_scrape,    # Creates Google News search URLs
    scrape_with_brightdata,          # Scrapes using BrightData proxy
    clean_html_to_text,              # Removes HTML tags and cleans text
    extract_headlines,               # Extracts news headlines from text
    summarize_with_gemini_news_script, # Summarizes headlines using Gemini AI
)

# Load environment variables from .env file
load_dotenv()

# Define NewsScraper class for handling news scraping operations
class NewsScraper:
    # Create rate limiter to prevent API abuse (5 requests per second)
    _rate_limiter = AsyncLimiter(5, 1)

    # Apply retry decorator with exponential backoff
    @retry(
        stop=stop_after_attempt(3),                    # Maximum 3 retry attempts
        wait=wait_exponential(multiplier=1, min=2, max=10)  # Exponential wait between retries
    )
    async def scrape_news(self, topics: List[str]) -> Dict[str, str]:
        """
        Main method to scrape and analyze news articles.
        
        Args:
            topics: List of topics to search for news
            
        Returns:
            Dictionary with topic as key and news summary as value
        """
        # Log scraping initiation with topic count
        print(f"[{datetime.now()}] 📰 NewsScraper: Starting news scraping for {len(topics)} topics")
        # Initialize empty dictionary for results
        results = {}
        
        # Iterate through topics with index for progress tracking
        for idx, topic in enumerate(topics, 1):
            # Record start time for this topic
            topic_start = datetime.now()
            # Log current topic being processed
            print(f"[{datetime.now()}] 📰 NewsScraper: Processing topic {idx}/{len(topics)}: '{topic}'")
            
            # Use rate limiter to prevent API abuse
            async with self._rate_limiter:
                try:
                    # Log URL generation for current topic
                    print(f"[{datetime.now()}] 📰 NewsScraper: Generating search URLs for '{topic}'")
                    # Generate Google News search URLs for topic
                    urls = generate_news_urls_to_scrape([topic])
                    # Log number of URLs generated
                    print(f"[{datetime.now()}] 📰 NewsScraper: Generated {len(urls)} URLs for '{topic}'")
                    
                    # Initialize variable for HTML content
                    search_html = None
                    try:
                        # Attempt to scrape using BrightData proxy
                        print(f"[{datetime.now()}] 📰 NewsScraper: Attempting BrightData scrape for '{topic}'")
                        print(f"[{datetime.now()}] 📰 NewsScraper: URL: {urls[topic]}")
                        # Scrape Google News page
                        search_html = scrape_with_brightdata(urls[topic])
                        # Log successful scraping
                        print(f"[{datetime.now()}] ✅ BrightData: Successfully scraped '{topic}'")
                    except Exception as bright_error:
                        # Handle BrightData scraping failures
                        print(f"[{datetime.now()}] ❌ BrightData: Failed for '{topic}' - {str(bright_error)}")
                        print(f"[{datetime.now()}] 🔄 NewsScraper: Using fallback method with direct requests for '{topic}'...")
                        # Import requests for direct HTTP requests
                        import requests
                        # Make direct HTTP request as fallback
                        search_html = requests.get(urls[topic], headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        }).text
                        # Log successful fallback scraping
                        print(f"[{datetime.now()}] ✅ NewsScraper: Fallback scraping completed for '{topic}'.")
                    
                    # Record start time for HTML cleaning
                    clean_start = datetime.now()
                    # Clean HTML content to extract readable text
                    clean_text = clean_html_to_text(search_html)
                    # Calculate cleaning duration
                    clean_duration = (datetime.now() - clean_start).total_seconds()
                    # Log cleaning results
                    print(f"[{datetime.now()}] 📄 NewsScraper: HTML cleaned for '{topic}'. Text length: {len(clean_text)} chars in {clean_duration:.3f}s")
                    
                    # Record start time for headline extraction
                    headlines_start = datetime.now()
                    # Extract news headlines from cleaned text
                    headlines = extract_headlines(clean_text)
                    # Calculate extraction duration
                    headlines_duration = (datetime.now() - headlines_start).total_seconds()
                    # Log extraction results
                    print(f"[{datetime.now()}] 📰 NewsScraper: Headlines extracted for '{topic}'. Headlines snippet: {headlines[:150]}...")
                    print(f"[{datetime.now()}] 📰 NewsScraper: Extraction took {headlines_duration:.3f}s")
                    
                    # Handle case where no headlines were found
                    if not headlines or headlines.strip() == "":
                        print(f"[{datetime.now()}] ⚠️ NewsScraper: No headlines found for '{topic}', using fallback")
                        # Create fallback headline
                        headlines = f"Latest news about {topic}"
                    
                    # Log AI summarization initiation
                    print(f"[{datetime.now()}] 🤖 NewsScraper: Summarizing news script for '{topic}' with Gemini...")
                    # Record start time for summarization
                    summarize_start = datetime.now()
                    # Use Gemini AI to summarize headlines into news script
                    summary = summarize_with_gemini_news_script(
                        api_key=os.getenv("GEMINI_API_KEY"),
                        headlines=headlines
                    )
                    # Calculate summarization duration
                    summarize_duration = (datetime.now() - summarize_start).total_seconds()
                    # Log summarization completion
                    print(f"[{datetime.now()}] 🤖 Gemini (News Script): News script summarized.")
                    print(f"[{datetime.now()}] ✅ NewsScraper: News script summarized for '{topic}'. Summary length: {len(summary)} chars in {summarize_duration:.3f}s")
                    # Store summary in results dictionary
                    results[topic] = summary
                    
                except Exception as e:
                    # Handle any errors during topic processing
                    print(f"[{datetime.now()}] ❌ NewsScraper: Failed to process '{topic}' - {str(e)}")
                    # Provide fallback message for failed topic
                    results[topic] = f"We couldn't retrieve the latest news about {topic} at this time."
                
                # Calculate and log total time for this topic
                topic_duration = (datetime.now() - topic_start).total_seconds()
                print(f"[{datetime.now()}] 📰 NewsScraper: Topic '{topic}' completed in {topic_duration:.3f}s")
                # Add delay between topics to be respectful to APIs
                await asyncio.sleep(1)
        
        # Log completion of all topics
        total_duration = (datetime.now() - datetime.now()).total_seconds()
        print(f"[{datetime.now()}] 📰 NewsScraper: All topics processed. Returning news analysis results. Processed {len(topics)} topics")
        # Return results in expected format
        return {"news_analysis": results}