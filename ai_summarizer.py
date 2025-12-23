
import google.generativeai as genai
from config import settings
from logger import setup_logger
from typing import Optional

logger = setup_logger(__name__)

class AISummarizer:
    def __init__(self):
        self.enabled = bool(settings.gemini_api_key)
        if self.enabled:
            genai.configure(api_key=settings.gemini_api_key)
            self.model = genai.GenerativeModel(settings.ai_model)
        else:
            logger.warning("Gemini API key not configured. AI summarization disabled.")

    def summarize(self, text: str) -> dict:
        """
        Summarize article content and assign tags using Gemini API.
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
            
            logger.info("Sending request to Gemini for JSON summarization and tagging...")
            response = self.model.generate_content(prompt)
            
            if response and response.text:
                raw_text = response.text.strip()
                # Clean up markdown code blocks if present
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()
                
                try:
                    import json
                    data = json.loads(raw_text)
                    summary = data.get("summary")
                    tags = data.get("tags", [])
                    
                    # Ensure tags are valid
                    valid_tags = [t for t in tags if t in settings.standard_tags]
                    
                    logger.info("Successfully generated AI summary and tags.")
                    return {"summary": summary, "tags": valid_tags}
                except (json.JSONDecodeError, AttributeError):
                    logger.error(f"Failed to parse JSON from Gemini: {raw_text[:200]}")
                    return {"summary": raw_text, "tags": []}
            else:
                logger.error("Gemini returned empty response.")
                return {"summary": None, "tags": []}
                
        except Exception as e:
            logger.error(f"AI summarization/tagging failed: {e}")
            return {"summary": None, "tags": []}

# Global instance
ai_summarizer = AISummarizer()
