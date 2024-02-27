from playwright.sync_api import sync_playwright
from urllib.parse import urlparse


class WebScraper:
    def __init__(self, url):
        self.main_url = url
        self.browser = None
        self.page = None

    def setup_browser(self, playwright):
        self.browser = playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()

    def navigate_and_extract(self):
        self.page.goto(self.main_url, wait_until="networkidle")
        self.page.wait_for_selector("xpath=//div[@id='root']", timeout=5000)
        html_content = self.page.content()
        title = self.page.title()

        links = self.page.query_selector_all("a")
        hrefs = [self.page.evaluate("el => el.getAttribute('href')", link) for link in links]

        main_domain = urlparse(self.main_url).netloc

        for href in hrefs:
            if href.startswith("/") and not href.startswith("/#"):
                href = self.main_url.rstrip("/") + href
            if urlparse(href).netloc == main_domain:
                print(f"Navegando a {href}")
                try:
                    self.page.goto(href, wait_until="networkidle")
                    page_content = self.page.content()

                except Exception as e:
                    print(f"Error al navegar a {href}: {e}")
                finally:
                    self.page.goto(self.main_url, wait_until="networkidle")
            else:
                print(f"Enlace externo o sección omitida: {href}")

        return html_content, page_content, title
        
    def run(self):
        with sync_playwright() as playwright:
            self.setup_browser(playwright)
            html_content, page_content, title = self.navigate_and_extract()
            self.browser.close()
            return html_content, page_content, title

