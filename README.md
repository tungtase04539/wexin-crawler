# WeChat Content Integration System

Hệ thống tích hợp nội dung WeChat - Công cụ Python để crawl và quản lý bài viết từ WeWe-RSS.

## 🚀 Tính năng

- ✅ **Tích hợp WeWe-RSS**: Kết nối với WeWe-RSS qua RSS feeds
- ✅ **Quản lý tài khoản**: Theo dõi nhiều tài khoản công chúng WeChat
- ✅ **Tự động đồng bộ**: Tự động cập nhật bài viết mới
- ✅ **Lưu trữ SQLite**: Database nhẹ, dễ triển khai
- ✅ **Xử lý nội dung**: Parse HTML, extract images, tạo summary
- ✅ **CLI mạnh mẽ**: Giao diện dòng lệnh với Rich UI
- ✅ **Export dữ liệu**: Xuất JSON, CSV
- ✅ **Cache thông minh**: Giảm tải cho WeWe-RSS server
- ✅ **Rate limiting**: Tránh quá tải requests

## 📋 Yêu cầu

- Python 3.10+
- WeWe-RSS đang chạy (mặc định: `http://localhost:4000`)

## 🔧 Cài đặt

### 1. Clone hoặc tải project

```bash
cd "c:\Users\Admin\crawl wexin"
```

### 2. Tạo virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 4. Cấu hình

```bash
copy .env.example .env
```

Chỉnh sửa `.env` nếu cần (mặc định đã OK cho localhost):

```env
WEWE_RSS_URL=http://localhost:4000
DATABASE_URL=sqlite:///data/articles.db
```

## 📖 Sử dụng

### Test kết nối

```bash
python cli.py test
```

### Thêm tài khoản WeChat

```bash
# Thêm và sync ngay
python cli.py add --feed-id "饼干的AI笔记AGI"

# Thêm không sync
python cli.py add --feed-id "your-feed-id" --no-sync
```

### Đồng bộ bài viết

```bash
# Sync một tài khoản
python cli.py sync --feed-id "饼干的AI笔记AGI"

# Sync tất cả tài khoản
python cli.py sync --all

# Full sync (cập nhật cả bài cũ)
python cli.py sync --feed-id "饼干的AI笔记AGI" --full
```

### Xem danh sách

```bash
# Xem tất cả tài khoản
python cli.py accounts

# Xem bài viết gần đây
python cli.py articles

# Xem bài viết của một tài khoản
python cli.py articles --feed-id "饼干的AI笔记AGI" --limit 50

# Xem thống kê
python cli.py stats
```

### Export dữ liệu

```bash
# Export JSON
python cli.py export --format json

# Export CSV
python cli.py export --format csv

# Export tài khoản cụ thể
python cli.py export --feed-id "饼干的AI笔记AGI" --format json --output my_export.json
```

## 🏗️ Cấu trúc Project

```
crawl wexin/
├── cli.py                   # CLI interface
├── config.py                # Configuration
├── database.py              # Database operations
├── models.py                # SQLAlchemy models
├── wewe_client.py          # RSS client
├── content_processor.py    # Content processing
├── sync_manager.py         # Sync orchestration
├── cache.py                # Caching utilities
├── logger.py               # Logging
├── requirements.txt        # Dependencies
├── .env                    # Environment variables
├── data/                   # Database & images
│   ├── articles.db
│   └── images/
├── logs/                   # Application logs
└── exports/                # Exported files
```

## 🔄 Workflow

1. **Thêm tài khoản**: `cli.py add --feed-id "your-feed-id"`
2. **Tự động sync**: Hệ thống fetch RSS feed từ WeWe-RSS
3. **Xử lý nội dung**: Parse HTML, extract images, tạo summary
4. **Lưu database**: SQLite lưu trữ bài viết
5. **Export**: Xuất dữ liệu khi cần

## 📊 Database Schema

### Accounts
- `id`, `feed_id`, `name`, `description`, `avatar_url`
- `feed_url`, `is_active`, `created_at`, `updated_at`

### Articles
- `id`, `account_id`, `title`, `author`, `url`, `guid`
- `content`, `summary`, `content_html`
- `cover_image`, `images`, `published_at`
- `word_count`, `reading_time_minutes`
- `is_read`, `is_favorite`, `created_at`, `updated_at`

### SyncHistory
- `id`, `account_id`, `sync_type`, `status`
- `articles_fetched`, `articles_new`, `articles_updated`
- `error_message`, `started_at`, `completed_at`

## 🎯 Use Cases

### 1. Crawl bài viết định kỳ

```bash
# Chạy mỗi 30 phút
python cli.py sync --all
```

### 2. Backup nội dung

```bash
python cli.py export --format json
```

### 3. Phân tích nội dung

```python
from database import db

# Lấy tất cả bài viết
articles = db.get_recent_articles(limit=100)

# Phân tích
for article in articles:
    print(f"{article.title}: {article.word_count} words")
```

## 🔍 Tips

1. **Feed ID**: Lấy từ WeWe-RSS UI (tên tài khoản công chúng)
2. **Cache**: Mặc định cache 30 phút, giảm tải server
3. **Rate Limit**: Mặc định 30 requests/phút
4. **Images**: Chưa tự động download, chỉ lưu URLs

## 🐛 Troubleshooting

### Lỗi kết nối WeWe-RSS

```bash
# Kiểm tra WeWe-RSS đang chạy
# Truy cập http://localhost:4000
python cli.py test
```

### Database locked

```bash
# Đóng tất cả connections
# Xóa file .db-journal nếu có
```

### Import errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## 📝 TODO

- [ ] Web dashboard (Flask/FastAPI)
- [ ] Tự động download images
- [ ] Scheduler tự động (APScheduler)
- [ ] AI summary generation
- [ ] Full-text search
- [ ] PostgreSQL/MySQL support

## 📄 License

MIT License

## 👨‍💻 Author

Created with ❤️ for WeChat content management
