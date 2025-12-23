
import requests
import json
from config import settings
from logger import setup_logger
from typing import Optional, Dict, Any, List

logger = setup_logger(__name__)

class AISummarizer:
    def __init__(self):
        self.enabled = bool(settings.gemini_api_key)
        self.api_key = settings.gemini_api_key
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.ai_model}:generateContent?key={self.api_key}"

    def summarize(self, text: str) -> dict:
        """
        Summarize article content and assign tags using Gemini REST API.
        Returns a dict with 'summary' and 'tags'.
        """
        if not self.enabled:
            return {"summary": None, "tags": []}

        if not text or len(text.strip()) < 100:
            logger.warning("Text too short to summarize.")
            return {"summary": None, "tags": []}

        try:
            # Clean text slightly (remove excessive whitespace)
            clean_text = " ".join(text.split())
            # Limit text length to avoid token limits
            input_text = clean_text[:20000] 
            
            tags_list_str = ", ".join(settings.standard_tags)
            prompt = settings.summarization_prompt.format(tags_list=tags_list_str) + "\n\nNỘI DUNG BÀI VIẾT:\n" + input_text
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "response_mime_type": "application/json"
                }
            }
            
            logger.info("Sending request to Gemini API (REST) for JSON summarization...")
            response = requests.post(self.api_url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Gemini API returned error: {response.status_code} - {response.text}")
                return {"summary": None, "tags": []}
                
            result_json = response.json()
            
            # Extract text from response
            try:
                raw_text = result_json["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                logger.error(f"Unexpected response structure from Gemini: {result_json}")
                return {"summary": None, "tags": []}
            
            # Parse JSON content
            if not raw_text:
                logger.error("Gemini returned empty text.")
                return {"summary": None, "tags": []}
                
            try:
                # Clean up if markdown blocks still exist (though response_mime_type should handle it)
                clean_raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                
                data = json.loads(clean_raw_text)
                summary = data.get("summary")
                tags = data.get("tags", [])
                
                # Ensure tags are valid
                valid_tags = [t for t in tags if t in settings.standard_tags]
                
                logger.info("Successfully generated AI summary and tags.")
                return {"summary": summary, "tags": valid_tags}
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from Gemini: {raw_text[:200]}")
                return {"summary": raw_text, "tags": []}
                
        except Exception as e:
            logger.error(f"AI summarization/tagging failed: {e}")
            return {"summary": None, "tags": []}

# Global instance
ai_summarizer = AISummarizer()
