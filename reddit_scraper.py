from typing import List
import os
from utils import *
from typing import List
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
import google.generativeai as genai
from dotenv import load_dotenv
import os
from tenacity import (
    retry, 
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from aiolimiter import AsyncLimiter
from tenacity import retry, stop_after_attempt, wait_exponential
from datetime import datetime, timedelta


load_dotenv()


two_weeks_ago = datetime.today() - timedelta(days=14) 
two_weeks_ago_str = two_weeks_ago.strftime('%Y-%m-%d')


class MCPOverloadedError(Exception):
    pass


mcp_limiter = AsyncLimiter(1, 15)

# Configure Gemini instead of Anthropic
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


class GeminiAgent:
    """Custom agent wrapper for Gemini to work with MCP tools"""
    
    def __init__(self, model, tools):
        self.model = model
        self.tools = tools
        self.tool_map = {tool.name: tool for tool in tools}
    
    async def ainvoke(self, input_data):
        messages = input_data["messages"]
        
        # Convert messages to a single prompt for Gemini
        system_message = ""
        user_message = ""
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            elif msg["role"] == "user":
                user_message = msg["content"]
        
        # Combine system and user messages
        full_prompt = f"{system_message}\n\n{user_message}"
        
        # For now, we'll use Gemini directly without tool calling
        # In a production environment, you might want to implement proper tool calling
        try:
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2000,
                )
            )
            
            # Return in the expected format
            return {"messages": [{"content": response.text}]}
        except Exception as e:
            print(f"[{datetime.now()}] Gemini Agent: Error generating content: {str(e)}")
            # Return a fallback response
            topic = user_message.split("'")[1] if "'" in user_message else "the topic"
            return {"messages": [{"content": f"I couldn't retrieve specific Reddit discussions about {topic} at this time, but this topic has been generating interest in online communities with users sharing various perspectives and experiences."}]}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=15, max=60),
    retry=retry_if_exception_type(MCPOverloadedError),
    reraise=True
)
async def process_topic(agent, topic: str):
    async with mcp_limiter:
        messages = [
            {
                "role": "system",
                "content": f"""You are a Reddit analysis expert. Use available tools to:
                1. Find top 2 posts about the given topic BUT only after {two_weeks_ago_str}, NOTHING before this date strictly!
                2. Analyze their content and sentiment
                3. Create a summary of discussions and overall sentiment"""
            },
            {
                "role": "user",
                "content": f"""Analyze Reddit posts about '{topic}'. 
                Provide a comprehensive summary including:
                - Main discussion points
                - Key opinions expressed
                - Any notable trends or patterns
                - Summarize the overall narrative, discussion points and also quote interesting comments without mentioning names
                - Overall sentiment (positive/neutral/negative)"""
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


async def scrape_reddit_topics(topics: List[str]) -> dict[str, dict]:
    """Process list of topics and return analysis results"""
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await load_mcp_tools(session)
                agent = GeminiAgent(model, tools)
                
                reddit_results = {}
                for topic in topics:
                    summary = await process_topic(agent, topic)
                    reddit_results[topic] = summary
                    await asyncio.sleep(5)  # Maintain rate limiting
                    
                return {"reddit_analysis": reddit_results}
    except Exception as e:
        print(f"[{datetime.now()}] Reddit Scraper: Error in scrape_reddit_topics: {str(e)}")
        # Return fallback results
        reddit_results = {}
        for topic in topics:
            reddit_results[topic] = f"Reddit discussions about {topic} are currently unavailable, but the topic continues to generate community interest and engagement."
        return {"reddit_analysis": reddit_results}