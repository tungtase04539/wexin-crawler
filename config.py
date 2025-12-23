"""
Configuration management for WeChat Content Integration System
"""
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
    )
    
    # WeWe-RSS Configuration
    wewe_rss_url: str = "http://localhost:4000"
    wewe_rss_auth_code: Optional[str] = None
    
    # Database Configuration
    database_url: str = "sqlite:///data/articles.db"
    
    # Sync Configuration
    sync_interval_minutes: int = 30
    max_articles_per_sync: int = 100
    enable_auto_sync: bool = True
    
    # Content Processing
    download_images: bool = True
    image_storage_path: str = "data/images"
    enable_content_cleaning: bool = True
    generate_summaries: bool = False
    
    # Export Configuration
    export_path: str = "exports"
    default_export_format: str = "json"
    
    # Web Dashboard
    web_host: str = "0.0.0.0"
    web_port: int = 5000
    web_debug: bool = True
    
    # AI & Metrics Configuration
    jizhile_api_key: Optional[str] = "JZLd4c982ae0dd1d3b0"
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    gemini_api_key: Optional[str] = None
    ai_model: str = "gemini-2.0-flash"

    # LarkSuite (Feishu) Configuration
    lark_app_id: Optional[str] = None
    lark_app_secret: Optional[str] = None
    lark_base_token: Optional[str] = None # Base token from Bitable URL
    lark_table_id: Optional[str] = None  # Table name or ID
    enable_lark_sync: bool = False
    
    standard_tags: List[str] = [
        "AI & LLM",
        "Tự động hóa",
        "Công cụ & Tiện ích",
        "Lập trình & API",
        "Marketing & Branding",
        "Sáng tạo nội dung",
        "Năng suất & Công việc",
        "Kinh doanh & Khởi nghiệp",
        "Tin tức công nghệ",
        "Hướng dẫn & Thủ thuật"
    ]
    
    summarization_prompt: str = """
    Bạn là một trợ lý phân tích nội dung chuyên nghiệp. 
    Nhiệm vụ của bạn là đọc bài viết dưới đây và thực hiện 2 việc:
    1. Tóm tắt nội dung bài viết bằng tiếng Việt một cách ngắn gọn, súc tích (dạng bullet points).
    2. Gắn các tag phù hợp nhất từ danh sách quy chuẩn sau: {tags_list}

    YÊU CẦU QUAN TRỌNG: 
    - Chỉ sử dụng các tag trong danh sách được cung cấp.
    - Bạn có thể chọn từ 1 đến 3 tag phù hợp nhất.
    - Trả về kết quả DUY NHẤT dưới dạng JSON với cấu trúc:
    {{
        "summary": "Nội dung tóm tắt ở đây...",
        "tags": ["Tag 1", "Tag 2"]
    }}
    - Nếu nội dung quá ngắn hoặc không có ý nghĩa, trả về giá trị null cho các trường.
    """
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    log_max_bytes: int = 10485760  # 10MB
    log_backup_count: int = 5
    
    # Cache
    cache_ttl_seconds: int = 3600
    enable_cache: bool = True
    
    # Rate Limiting
    max_requests_per_minute: int = 30
    
    @property
    def base_dir(self) -> Path:
        """Get base directory of the project"""
        return Path(__file__).parent
    
    @property
    def is_vercel(self) -> bool:
        """Check if running on Vercel"""
        import os
        return bool(os.environ.get("VERCEL"))

    @property
    def data_dir(self) -> Path:
        """Get data directory"""
        if self.is_vercel:
            path = Path("/tmp/data")
        else:
            path = self.base_dir / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def images_dir(self) -> Path:
        """Get images directory"""
        if self.is_vercel:
            path = Path("/tmp/data/images")
        else:
            path = self.base_dir / self.image_storage_path
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def exports_dir(self) -> Path:
        """Get exports directory"""
        if self.is_vercel:
            path = Path("/tmp/exports")
        else:
            path = self.base_dir / self.export_path
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    @property
    def logs_dir(self) -> Path:
        """Get logs directory"""
        if self.is_vercel:
            path = Path("/tmp/logs")
        else:
            path = self.base_dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def get_feed_url(self, feed_id: str, format: str = "json") -> str:
        """
        Get RSS feed URL for a specific account
        
        Args:
            feed_id: The feed/account ID
            format: Feed format (json, rss, atom)
        
        Returns:
            Full URL to the feed
        """
        return f"{self.wewe_rss_url}/feeds/{feed_id}.{format}"
    
    def get_all_feeds_url(self, format: str = "json") -> str:
        """
        Get URL for all feeds
        
        Args:
            format: Feed format (json, rss, atom)
        
        Returns:
            Full URL to all feeds
        """
        return f"{self.wewe_rss_url}/feeds/all.{format}"


# Global settings instance
settings = Settings()
