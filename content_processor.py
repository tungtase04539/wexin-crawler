"""
Content processing and cleaning utilities
"""
import re
from typing import Optional, List, Dict, Any
from datetime import datetime
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from config import settings
from logger import setup_logger

logger = setup_logger(__name__)


class ContentProcessor:
    """Process and clean article content"""
    
    def __init__(self):
        self.enable_cleaning = settings.enable_content_cleaning
    
    def process_article(self, entry: Dict[str, Any], fetch_full_content: bool = True) -> Dict[str, Any]:
        """
        Process a feed entry into article data
        
        Args:
            entry: Feed entry dictionary
            fetch_full_content: Whether to fetch full content from URL
        
        Returns:
            Processed article data
        """
        # Extract basic fields
        title = self._clean_text(entry.get("title", ""))
        
        # Handle author being dict, string or list (JSON Feed format)
        author = entry.get("author", "")
        authors = entry.get("authors", [])
        
        if authors and isinstance(authors, list):
            # Extract names from authors list
            author_names = []
            for a in authors:
                if isinstance(a, dict):
                    author_names.append(a.get("name", "Unknown"))
                elif isinstance(a, str):
                    author_names.append(a)
            if author_names:
                author = ", ".join(author_names)
        
        if isinstance(author, dict):
            author = author.get("name", "Unknown")
        elif not isinstance(author, str):
            author = str(author) if author else ""
        
        if not author or author.lower() == "unknown":
            # Try to get from feed_item level directly
            author = entry.get("author_name", author)
        
        # Handle URL - JSON feed uses 'url', RSS uses 'link'
        url = entry.get("url", "") or entry.get("link", "")
        guid = entry.get("id", url)
        
        # Extract and process content
        # Try to fetch full content from URL if available
        content_text = ""
        content_html = ""
        images_list = []
        videos_list = []
        
        if url and fetch_full_content:
            logger.info(f"Fetching full content for: {title[:50]}...")
            
            try:
                from content_fetcher import content_fetcher
                fetched = content_fetcher.fetch_article_content(url)
                
                if fetched:
                    content_text = fetched.get('content_text', '')
                    content_html = fetched.get('content_html', '')
                    images_list = fetched.get('images', [])
                    videos_list = fetched.get('videos', [])
                    logger.info(f"✓ Fetched {len(content_text)} chars, {len(images_list)} images, {len(videos_list)} videos")
            except Exception as e:
                logger.error(f"Failed to fetch content from {url}: {e}")
        
        # Fallback to feed content if fetching failed
        if not content_text:
            raw_content = (
                entry.get("content_html", "") or 
                entry.get("content_text", "") or
                entry.get("content", "") or 
                entry.get("description", "") or
                entry.get("summary", "")
            )
            content_html = raw_content
            content_text = self._html_to_text(raw_content)
        
        # Generate summary & Tags (AI)
        summary_text = entry.get("summary", "")
        summary = summary_text if summary_text else self._generate_summary(content_text, "")
        tags = []
        
        # Try AI generation if configured
        if settings.openai_api_key and content_text:
             logger.info("Generating AI content...")
             ai_result = self._generate_ai_content(content_text)
             if ai_result:
                 if ai_result.get('summary'):
                     summary = ai_result.get('summary')
                 if ai_result.get('tags'):
                     tags = ai_result.get('tags')

        # Extract images from HTML if not already fetched
        if not images_list:
            images_data = self._extract_images(content_html)
            cover_image = images_data["cover"]
            images_list = images_data["all"]
        else:
            # Use fallback image from entry if available (JSON Feed standard 'image')
            cover_image = entry.get("image", None)
            if not cover_image:
                cover_image = images_list[0]['url'] if images_list else None
        
        # Parse published date
        date_str = (
            entry.get("date_published", "") or
            entry.get("published", "") or 
            entry.get("updated", "") or
            entry.get("date_modified", "")
        )
        published_at = self._parse_date(date_str)
        
        # Calculate word count and reading time
        word_count = self._count_words(content_text)
        reading_time = max(1, word_count // 200)  # Assume 200 words/minute
        
        return {
            "title": title,
            "author": author,
            "url": url,
            "guid": guid,
            "content": content_text,
            "content_html": content_html,
            "summary": summary,
            "tags": {"items": tags} if tags else None,
            "cover_image": cover_image,
            "images": {"urls": [img['url'] for img in images_list]} if images_list else None,
            "videos": {"urls": [vid['url'] for vid in videos_list]} if videos_list else None,
            "published_at": published_at,
            "word_count": word_count,
            "reading_time_minutes": reading_time
        }
    
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _html_to_text(self, html: str) -> str:
        """
        Convert HTML to plain text
        
        Args:
            html: HTML content
        
        Returns:
            Plain text content
        """
        if not html:
            return ""
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style', 'iframe', 'noscript']):
                element.decompose()
            
            # Get text
            text = soup.get_text(separator='\n')
            
            # Clean up whitespace
            lines = [line.strip() for line in text.splitlines()]
            lines = [line for line in lines if line]
            text = '\n'.join(lines)
            
            return text
        
        except Exception as e:
            logger.warning(f"Failed to parse HTML: {e}")
            return html
    
    def _extract_images(self, html: str) -> Dict[str, Any]:
        """
        Extract images from HTML content
        
        Args:
            html: HTML content
        
        Returns:
            Dictionary with cover image and all images
        """
        if not html:
            return {"cover": None, "all": []}
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            img_tags = soup.find_all('img')
            
            images = []
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src and src.startswith('http'):
                    images.append(src)
            
            # First image as cover
            cover = images[0] if images else None
            
            return {"cover": cover, "all": images}
        
        except Exception as e:
            logger.warning(f"Failed to extract images: {e}")
            return {"cover": None, "all": []}
    
        return ""

    def _generate_ai_content(self, text: str) -> Dict[str, Any]:
        """
        Generate summary and tags using AI
        
        Args:
           text: Article text
           
        Returns:
           Dict with 'summary' and 'tags'
        """
        if not settings.openai_api_key:
            return {}

        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url
            )
            
            prompt = f"""
            Analyze the following article content and provide:
            1. A concise structured summary (max 300 words).
            2. A list of 5 relevant tags (keywords).
            
            Content:
            {text[:4000]}
            
            Format response as JSON:
            {{
                "summary": "...",
                "tags": ["tag1", "tag2", ...]
            }}
            """
            
            response = client.chat.completions.create(
                model=settings.ai_model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that analyzes articles."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"AI Generation failed: {e}")
            return {}

    def _generate_summary(self, text: str, existing_summary: str = "") -> str:
        """
        Generate article summary (AI aware)
        """
        # If AI is enabled and we have text, try AI first (or maybe we do it in process_article to verify tags too)
        # For now, keep simple fallback
        if existing_summary:
            return self._clean_text(existing_summary)
        
        # Take first 200 characters as summary
        if text:
            summary = text[:200]
            last_period = summary.rfind('。')
            if last_period > 100:
                summary = summary[:last_period + 1]
            elif len(text) > 200:
                summary += '...'
            return summary
        
        return ""
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime
        
        Args:
            date_str: Date string
        
        Returns:
            Datetime object or None
        """
        if not date_str:
            return None
        
        try:
            # Try to parse with dateutil
            dt = date_parser.parse(date_str)
            return dt
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None
    
    def _count_words(self, text: str) -> int:
        """
        Count words in text (supports Chinese)
        
        Args:
            text: Text to count
        
        Returns:
            Word count
        """
        if not text:
            return 0
        
        # For Chinese text, count characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        # For English/other languages, count words
        words = re.findall(r'\b\w+\b', text)
        english_words = len([w for w in words if not re.match(r'[\u4e00-\u9fff]', w)])
        
        # Combine (Chinese characters count as words)
        return chinese_chars + english_words
    
    def clean_html(self, html: str) -> str:
        """
        Clean HTML content
        
        Args:
            html: HTML content
        
        Returns:
            Cleaned HTML
        """
        if not html or not self.enable_cleaning:
            return html
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'iframe', 'noscript']):
                element.decompose()
            
            # Remove unwanted attributes
            for tag in soup.find_all(True):
                # Keep only essential attributes
                allowed_attrs = ['src', 'href', 'alt', 'title']
                attrs = dict(tag.attrs)
                for attr in attrs:
                    if attr not in allowed_attrs:
                        del tag[attr]
            
            return str(soup)
        
        except Exception as e:
            logger.warning(f"Failed to clean HTML: {e}")
            return html


# Global processor instance
content_processor = ContentProcessor()
