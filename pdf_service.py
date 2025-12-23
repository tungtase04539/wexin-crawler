
import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
from config import settings
from logger import setup_logger

logger = setup_logger(__name__)

class PDFService:
    """Service to generate PDF from HTML content using Playwright"""
    
    async def generate_pdf(self, html_content: str, output_path: str) -> bool:
        """
        Generate PDF from HTML content
        """
        try:
            # Add print-specific styles to HTML if needed
            styled_html = f"""
            <html>
            <head>
                <meta name="referrer" content="no-referrer">
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; padding: 20px; }}
                    img {{ max-width: 100%; height: auto; }}
                    @media print {{
                        button {{ display: none !important; }}
                    }}
                </style>
            </head>
            <body>
                {html_content}
            </body>
            </html>
            """
            
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                page = await browser.new_page()
                
                # Use set_content with high fidelity
                await page.set_content(styled_html, wait_until="networkidle")
                
                # Generate PDF
                await page.pdf(
                    path=output_path,
                    format="A4",
                    print_background=True,
                    margin={"top": "1cm", "right": "1cm", "bottom": "1cm", "left": "1cm"}
                )
                
                await browser.close()
                return True
                
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            return False

pdf_service = PDFService()
