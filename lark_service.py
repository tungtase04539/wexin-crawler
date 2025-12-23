"""
LarkSuite (Feishu) Integration Service
Handles syncing articles, tags and scores to Lark Bitable.
"""
import requests
import json
import time
from datetime import datetime
from typing import Optional, List, Dict, Any

from config import settings
from logger import setup_logger
from models import Article

logger = setup_logger(__name__)

class LarkService:
    """Service to interact with Lark/Feishu Open API (Bitable)"""
    
    def __init__(self):
        self.app_id = settings.lark_app_id
        self.app_secret = settings.lark_app_secret
        self.base_token = settings.lark_base_token
        self.table_id = settings.lark_table_id
        
        self._tenant_access_token = None
        self._token_expiry = 0
        
    def _get_tenant_access_token(self) -> Optional[str]:
        """Get or refresh tenant_access_token"""
        if self._tenant_access_token and time.time() < self._token_expiry:
            return self._tenant_access_token
            
        if not self.app_id or not self.app_secret:
            logger.error("Lark App ID or Secret missing")
            return None
            
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        try:
            response = requests.post(url, json=payload)
            data = response.json()
            
            if data.get("code") == 0:
                self._tenant_access_token = data.get("tenant_access_token")
                # Expiry is usually 2 hours, save with 5min buffer
                self._token_expiry = time.time() + data.get("expire", 7200) - 300
                return self._tenant_access_token
            else:
                logger.error(f"Failed to get Lark token: {data.get('msg')}")
                return None
        except Exception as e:
            logger.error(f"Lark auth error: {e}")
            return None

    def upsert_article(self, article: Article) -> bool:
        """
        Create or update an article record in Lark Bitable.
        Uses the article URL as a unique identifier.
        """
        token = self._get_tenant_access_token()
        if not token or not self.base_token or not self.table_id:
            return False
            
        # 1. Search for existing record by URL
        # We assume there is a field "Link Gốc" or similar that stores the URL
        record_id = self._find_record_by_url(article.url, token)
        
        # 2. Prepare fields
        fields = self._map_article_to_fields(article)
        
        if record_id:
            return self._update_record(record_id, fields, token)
        else:
            return self._create_record(fields, token)

    def _map_article_to_fields(self, article: Article) -> Dict[str, Any]:
        """Map Article model to Lark Bitable fields"""
        # Note: These names MUST match the columns in your Lark Bitable exactly
        fields = {
            "Tiêu đề": article.title,
            "Link Gốc": article.url,
            "Tác giả": article.author or "Unknown",
            "Tài khoản": article.account.name if article.account else "Unknown",
            "Tóm tắt AI": article.ai_summary or article.summary or "",
            "Số chữ": article.word_count or 0,
            
            # Metrics
            "Lượt đọc": article.read_count or 0,
            "Lượt thích": article.like_count or 0,
            "Lượt chia sẻ": article.share_count or 0,
            
            # Scores (Calculated in Article.calculate_scores())
            "Tương tác (ER)": round(article.engagement_rate or 0, 2),
            "Lan truyền (VI)": round(article.virality_index or 0, 2),
            "Giá trị (CVI)": round(article.content_value_index or 0, 2),
            "Điểm Nhiệt": round(article.heat_score or 0, 2),
        }
        
        # Tags (Multi-select)
        if article.tags:
            # article.tags is already a list or json-string from DB
            tags_list = article.tags if isinstance(article.tags, list) else []
            if tags_list:
                fields["Phân loại"] = tags_list
                
        return fields

    def _find_record_by_url(self, url: str, token: str) -> Optional[str]:
        """Find a record ID by its URL field"""
        api_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.base_token}/tables/{self.table_id}/records/search"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Search filter
        payload = {
            "field_name": "Link Gốc",
            "value": [url],
            "operator": "contains" 
        }
        
        try:
            # Note: The 'search' endpoint might vary by version, sometimes it's simpler to filter
            # using the 'list' endpoint with a filter parameter
            list_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.base_token}/tables/{self.table_id}/records"
            # Filter syntax: CurrentValue.[Link Gốc] = "url"
            params = {
                "filter": f'CurrentValue.[Link Gốc] == "{url}"'
            }
            
            response = requests.get(list_url, headers=headers, params=params)
            data = response.json()
            
            if data.get("code") == 0:
                items = data.get("data", {}).get("items", [])
                if items:
                    return items[0].get("record_id")
            return None
        except Exception as e:
            logger.error(f"Lark record search error: {e}")
            return None

    def _create_record(self, fields: Dict[str, Any], token: str) -> bool:
        """Create new record in Bitable"""
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.base_token}/tables/{self.table_id}/records"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"fields": fields}
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            data = response.json()
            if data.get("code") == 0:
                logger.info(f"Article synced to Lark: {fields.get('Tiêu đề')}")
                return True
            else:
                logger.error(f"Failed to create Lark record: {data.get('msg')} (Code: {data.get('code')})")
                logger.error(f"Full response: {json.dumps(data, ensure_ascii=False)}")
                return False
        except Exception as e:
            logger.error(f"Lark create error: {e}")
            return False

    def _update_record(self, record_id: str, fields: Dict[str, Any], token: str) -> bool:
        """Update existing record in Bitable"""
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.base_token}/tables/{self.table_id}/records/{record_id}"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"fields": fields}
        
        try:
            response = requests.put(url, headers=headers, json=payload)
            data = response.json()
            if data.get("code") == 0:
                logger.info(f"Article updated in Lark: {fields.get('Tiêu đề')}")
                return True
            else:
                logger.error(f"Failed to update Lark record: {data.get('msg')} (Code: {data.get('code')})")
                logger.error(f"Full response: {json.dumps(data, ensure_ascii=False)}")
                return False
        except Exception as e:
            logger.error(f"Lark update error: {e}")
            return False


# Global service instance
lark_service = LarkService()
