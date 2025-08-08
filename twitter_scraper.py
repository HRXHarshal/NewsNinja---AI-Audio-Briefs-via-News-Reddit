from typing import List, Dict
import os
from datetime import datetime, timedelta
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
import google.generativeai as genai
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from aiolimiter import AsyncLimiter
import asyncio

load_dotenv()

print(f"[{datetime.now()}] 🐦 TwitterScraper: Initializing Twitter scraper...")

class MCPOverloadedError(Exception):
    pass

twitter_limiter = AsyncLimiter(2, 15)

# Configure Gemini for tweet analysis
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash-exp')

server_params = StdioServerParameters(
    command="npx",
    env={
        "API_TOKEN": os.getenv("API_TOKEN"),
        "WEB_UNLOCKER_ZONE": os.getenv("WEB_UNLOCKER_ZONE"),
    },
    args=["@brightdata/mcp"],
)

class TwitterAgent:
    def __init__(self, model, tools):
        self.model = model
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}
    
    async def ainvoke(self, input_data):
        messages = input_data["messages"]
        
        system_message = ""
        user_message = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user":
                user_message = msg["content"]
        
        full_prompt = f"{system_message}\n\n{user_message}"
        
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1500,
                )
            )
            
            topic = user_message.split("'")[1] if "'" in user_message else "the topic"
            print(f"[{datetime.now()}] 🐦 TwitterScraper: AI analysis completed for '{topic}'")
            return {"messages": [{"content": response.text}]}
        except Exception as e:
            print(f"[{datetime.now()}] 🐦 TwitterScraper: AI analysis failed - {str(e)}")
            topic = user_message.split("'")[1] if "'" in user_message else "the topic"
            return {"messages": [{"content": f"Twitter discussions about {topic} are currently unavailable."}]}

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=15, max=60),
    retry=retry_if_exception_type(MCPOverloadedError),
    reraise=True
)
async def process_twitter_topic(agent, topic: str):
    print(f"[{datetime.now()}] 🐦 TwitterScraper: Processing topic '{topic}'")
    
    async with twitter_limiter:
        messages = [
            {
                "role": "system",
                "content": f"""You are a Twitter analysis expert. Use available tools to:
                1. Find trending tweets about the given topic from the last 24-48 hours
                2. Analyze tweet content, engagement metrics, and sentiment
                3. Identify key influencers and viral discussions
                4. Create a summary of Twitter conversations and overall sentiment"""
            },
            {
                "role": "user",
                "content": f"""Analyze Twitter/X posts about '{topic}'. 
                Provide a comprehensive summary including:
                - Top trending tweets and their key messages
                - Engagement levels (likes, retweets, replies)
                - Sentiment analysis (positive/negative/neutral)
                - Key influencers and their perspectives
                - Notable hashtags and trends
                - Quote interesting tweets without mentioning usernames
                - Overall Twitter narrative and discussion points"""
            }
        ]
        
        try:
            response = await agent.ainvoke({"messages": messages})
            return response["messages"][-1]["content"]
        except Exception as e:
            if "Overloaded" in str(e):
                raise MCPOverloadedError("Service overloaded")
            else:
                raise

async def scrape_twitter_topics(topics: List[str]) -> dict[str, dict]:
    print(f"[{datetime.now()}] 🐦 TwitterScraper: Starting Twitter scraping for {len(topics)} topics")
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                print(f"[{datetime.now()}] 🐦 TwitterScraper: Initializing MCP session...")
                await session.initialize()
                tools = await load_mcp_tools(session)
                agent = TwitterAgent(model, tools)
                
                twitter_results = {}
                for idx, topic in enumerate(topics, 1):
                    print(f"[{datetime.now()}] 🐦 TwitterScraper: Processing topic {idx}/{len(topics)}: '{topic}'")
                    summary = await process_twitter_topic(agent, topic)
                    twitter_results[topic] = summary
                    print(f"[{datetime.now()}] 🐦 TwitterScraper: Completed '{topic}' - {len(summary)} chars")
                    await asyncio.sleep(3)
                
                print(f"[{datetime.now()}] 🐦 TwitterScraper: Completed processing all {len(topics)} topics")
                return {"twitter_analysis": twitter_results}
                
    except Exception as e:
        print(f"[{datetime.now()}] 🐦 TwitterScraper: Error in scrape_twitter_topics: {str(e)}")
        twitter_results = {}
        for topic in topics:
            twitter_results[topic] = f"Twitter discussions about {topic} are currently unavailable."
        return {"twitter_analysis": twitter_results}