"""
Competitor Intelligence Analysis using Google Gemini API
Replace your existing scripts/antigravity.py with this file
"""

import os
import json
from datetime import datetime
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Use Gemini 1.5 Flash (fast and free tier friendly) or Pro for better quality
MODEL_NAME = "gemini-2.0-flash" # Change to "gemini-1.5-pro" for better results

ANALYSIS_PROMPT = """You are a competitive intelligence analyst for Abuzz, a 3D wayfinding solutions company. 

Analyze the following news article about {competitor_name} ({competitor_website}).

## Information to Extract
1. **Event Type** (select one):
   - New Project/Installation
   - Investment/Funding Round
   - Award/Recognition
   - Product Launch
   - Partnership/Acquisition
   - Leadership Change
   - Market Expansion
   - Technical Innovation

2. **Key Details**:
   - Date of announcement (YYYY-MM-DD format, use today's date if not specified)
   - Location/Region affected
   - Financial figures (if mentioned)
   - Client/Partner names
   - Technology/product names

3. **Strategic Significance** (1-5 scale):
   - 1 = Minimal impact on Abuzz
   - 3 = Moderate competitive threat
   - 5 = Major threat requiring immediate attention
   - Consider: Does this affect malls, hospitals, airports, shopping centers? Does it involve 3D navigation?

## Article to Analyze:
{article_text}

## Output Format
Return ONLY a valid JSON object (no markdown, no explanation):
{{
  "competitor": "{competitor_name}",
  "event_type": "string",
  "date": "YYYY-MM-DD",
  "title": "short descriptive title",
  "summary": "2-3 sentence executive summary",
  "threat_level": 1-5,
  "details": {{
    "location": "string or null",
    "financial_value": "string or null",
    "partners": ["array of strings"],
    "products": ["array of strings"]
  }},
  "source_url": "{source_url}",
  "extracted_at": "{timestamp}"
}}
"""


def generate(
    competitor_name: str,
    competitor_website: str,
    article_text: str,
    source_url: str = ""
) -> Optional[dict]:
    """
    Analyze a news article about a competitor using Gemini.
    
    Args:
        competitor_name: Name of the competitor company
        competitor_website: Competitor's website URL
        article_text: The news article content to analyze
        source_url: URL where the article was found
    
    Returns:
        Dictionary with structured intelligence data, or None if analysis fails
    """
    
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️  GEMINI_API_KEY not found in environment variables")
        print("   Get your free API key at: https://aistudio.google.com/app/apikey")
        return _mock_response(competitor_name, source_url)
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = ANALYSIS_PROMPT.format(
            competitor_name=competitor_name,
            competitor_website=competitor_website,
            article_text=article_text[:8000],  # Truncate very long articles
            source_url=source_url,
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,  # Lower temperature for more consistent JSON
                max_output_tokens=1024,
            )
        )
        
        # Extract JSON from response
        response_text = response.text.strip()
        
        # Handle markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
        
        result = json.loads(response_text)
        
        # Validate required fields
        required_fields = ["competitor", "event_type", "title", "summary", "threat_level"]
        for field in required_fields:
            if field not in result:
                print(f"⚠️  Missing required field: {field}")
                return None
        
        print(f"✅ Analyzed: {result['title']} (Threat Level: {result['threat_level']})")
        return result
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON response: {e}")
        print(f"   Raw response: {response.text[:200]}...")
        return None
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return None


def _mock_response(competitor_name: str, source_url: str) -> dict:
    """Return a mock response for testing without API key"""
    print("   Using mock response for testing...")
    return {
        "competitor": competitor_name,
        "event_type": "Product Launch",
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "title": f"[MOCK] {competitor_name} News Update",
        "summary": "This is a mock response. Add your GEMINI_API_KEY to .env for real analysis.",
        "threat_level": 2,
        "details": {
            "location": "Unknown",
            "financial_value": None,
            "partners": [],
            "products": []
        },
        "source_url": source_url,
        "extracted_at": datetime.utcnow().isoformat() + "Z"
    }


# Quick test
if __name__ == "__main__":
    test_article = """
    Mappedin, the leading indoor mapping platform, today announced a partnership 
    with Westfield Shopping Centers to deploy their wayfinding solution across 
    15 malls in North America. The deal, valued at $2.3 million, will include 
    interactive kiosks and mobile app integration. The rollout begins Q2 2026.
    """
    
    result = generate(
        competitor_name="Mappedin",
        competitor_website="https://mappedin.com",
        article_text=test_article,
        source_url="https://example.com/news/mappedin-westfield"
    )
    
    if result:
        print("\n" + json.dumps(result, indent=2))