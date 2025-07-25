---
Demo
---
![Screenshot 2025-07-01 124914](https://github.com/user-attachments/assets/c656373d-b387-4ccd-9584-cf5c4b5869cf)

![Screenshot 2025-07-01 124952](https://github.com/user-attachments/assets/654f3b9c-de55-4008-bfeb-60928e7e72e5)

https://github.com/user-attachments/assets/7b70c38e-d693-4435-b78e-833917c97180



Full Demo: [Demo Video Link](https://youtu.be/W-kBjDjm0aQ?si=UrvRYEcS_dRC9E8z)

---
NewsNinja---AI-Audio-Briefs-via-News-Reddit
---

Your personal news ninja that silently gathers headlines and Reddit reactions, then delivers audio briefings straight to your ears. *No scroll, just soul.*

---
FEATURES
- 🗞️ Scrape premium news websites (bypassing paywalls)
- 🕵️♂️ Extract live Reddit reactions (even from JS-heavy threads)
- 🔊 AI-powered audio summaries (text-to-speech with ElevenLabs)
- ⚡ Real-time updates (thanks to Bright Data's MCP magic)

---
PREREQUISITES
- Python 3.12
- Bright Data account (https://brightdata.com)
- MURF API (https://murf.ai/api/docs/introduction/overview) OR ElevenLabs account (https://elevenlabs.io)
- Google AI studio API key (https://aistudio.google.com/apikey)
---
QUICK START

1. Clone the Dojo
```
git clone https://github.com/HRXHarshal/NewsNinja---AI-Audio-Briefs-via-News-Reddit.git
cd NewsNinja---AI-Audio-Briefs-via-News-Reddit
```

2. Install Dependencies
```
pipenv install
pipenv shell
```

3. Ninja Secrets (Environment Setup)
Create .env file:
```
cp .env.example .env
- BRIGHTDATA_MCP_KEY : Your API key for Bright Data's Mobile Collector Proxy (MCP) service, used for web scraping.
- WEB_UNLOCKER_ZONE : The specific zone name configured in your Bright Data account for web unlocking.
- BROWSER_AUTH : Authentication token or credentials for browser-based operations, likely related to Bright Data's browser automation or similar services.
- API_TOKEN : This appears to be a duplicate or alternative to BRIGHTDATA_MCP_KEY based on its value. It's likely another Bright Data API token.

- GEMINI_API_KEY : Your API key for Google's Gemini AI models.
- MURF_API_KEY= Your API key from MURF API 
- MURF_WORKSPACE_ID= YOUR workspace name of  MURF API key
- ELEVENLABS_API_KEY : Your API key for ElevenLabs, used for text-to-speech conversion.

Important NOTE : For LLM use either one of Gemini or Anthropic model and TTS conversion use either one of (MURF API or ElevenLabs)
The above code uses Gemini + MURF AI (prefered) . 

Configure your secrets in .env:
```
# Bright Data
```
BRIGHTDATA_MCP_KEY="your_mcp_api_key"
BROWSER_AUTH="your_browser_auth_token"
```

# MURF API 
```
MURF_API_KEY="your_text_to_speech_key"
```


4. Prepare Your Weapons (Bright Data Setup)
- Create MCP zone: https://brightdata.com/cp/zones
- Enable browser authentication
- Copy credentials to .env

---
RUNNING THE NINJA
---


First terminal (Backend):
```
pipenv run python backend.py

```
Second terminal (Frontend):
```
pipenv run streamlit run frontend.py
```

---
PROJECT STRUCTURE
---
```

├── frontend.py          # Streamlit UI
├── backend.py           # API & data processing  
├── utils.py             # UTILS  
├── news_scraper.py      # News Scraper  
├── reddit_scraper.py    # Reddit Scraper  
├── models.py            # Pydantic model
├── Pipfile              # Dependency scroll
|── test-murf.py         # For testing MURF TTS API 
├── .env.example         # Secret map template
└── requirements.txt     # Alternative dependency list
```
---
NOTES
---
- First scrape takes 15-20 seconds (good ninjas are patient)
- Reddit scraping uses real browser emulation via MCP
- Keep .env file secret 

