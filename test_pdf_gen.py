
import asyncio
from pdf_service import pdf_service
from database import db
from models import Article
from sqlalchemy import select

async def main():
    print("Testing PDF generation...")
    with db.get_session() as session:
        article = session.scalar(select(Article).where(Article.content_html.is_not(None)).limit(1))
        if not article:
            print("No article with HTML found")
            return
            
        output = "test_article.pdf"
        print(f"Generating PDF for: {article.title}")
        success = await pdf_service.generate_pdf(article.content_html, output)
        if success:
            print(f"PDF generated successfully: {output}")
        else:
            print("PDF generation failed")

if __name__ == "__main__":
    asyncio.run(main())
