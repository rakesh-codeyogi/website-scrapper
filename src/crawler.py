"""Web crawler with dual-mode support (static and JavaScript rendering)."""

import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse
from collections import deque

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()


@dataclass
class PageData:
    """Data extracted from a single page."""
    url: str
    html: str
    title: str = ""
    status_code: int = 200
    error: Optional[str] = None


@dataclass
class CrawlerConfig:
    """Configuration for the crawler."""
    max_pages: int = 50
    max_depth: int = 5
    delay: float = 1.0
    timeout: int = 30
    use_js: bool = False
    user_agent: str = "WebsiteScraper/1.0 (Educational purposes)"


class WebCrawler:
    """Crawls websites and extracts HTML content from all pages."""

    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or CrawlerConfig()
        self.visited: set[str] = set()
        self.pages: list[PageData] = []
        self.base_domain: str = ""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})
        self._playwright = None
        self._browser = None

    def _normalize_url(self, url: str) -> str:
        """Normalize URL by removing fragments and trailing slashes."""
        parsed = urlparse(url)
        # Remove fragment and normalize
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if normalized.endswith("/") and len(parsed.path) > 1:
            normalized = normalized.rstrip("/")
        return normalized

    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain."""
        parsed = urlparse(url)
        return parsed.netloc == self.base_domain or parsed.netloc == ""

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL should be crawled."""
        parsed = urlparse(url)

        # Skip non-http(s) URLs
        if parsed.scheme and parsed.scheme not in ("http", "https"):
            return False

        # Skip file extensions that aren't web pages
        skip_extensions = (
            ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
            ".mp3", ".mp4", ".avi", ".mov", ".zip", ".tar", ".gz",
            ".css", ".js", ".ico", ".woff", ".woff2", ".ttf", ".eot"
        )
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in skip_extensions):
            return False

        return True

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract all internal links from HTML."""
        soup = BeautifulSoup(html, "lxml")
        links = []

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()

            # Skip empty, javascript, and mailto links
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            normalized = self._normalize_url(full_url)

            if self._is_same_domain(normalized) and self._is_valid_url(normalized):
                links.append(normalized)

        return links

    def _fetch_static(self, url: str) -> PageData:
        """Fetch page using requests (no JavaScript rendering)."""
        try:
            response = self.session.get(url, timeout=self.config.timeout)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            title = soup.title.string.strip() if soup.title and soup.title.string else ""

            return PageData(
                url=url,
                html=response.text,
                title=title,
                status_code=response.status_code
            )
        except requests.RequestException as e:
            return PageData(
                url=url,
                html="",
                error=str(e),
                status_code=getattr(e.response, "status_code", 0) if hasattr(e, "response") else 0
            )

    def _init_playwright(self):
        """Initialize Playwright browser."""
        if self._playwright is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)

    def _fetch_js(self, url: str) -> PageData:
        """Fetch page using Playwright (with JavaScript rendering)."""
        try:
            self._init_playwright()
            page = self._browser.new_page()
            page.set_extra_http_headers({"User-Agent": self.config.user_agent})

            response = page.goto(url, timeout=self.config.timeout * 1000, wait_until="networkidle")
            html = page.content()
            title = page.title()
            status = response.status if response else 200

            page.close()

            return PageData(
                url=url,
                html=html,
                title=title,
                status_code=status
            )
        except Exception as e:
            return PageData(
                url=url,
                html="",
                error=str(e),
                status_code=0
            )

    def _fetch_page(self, url: str) -> PageData:
        """Fetch a page using configured method."""
        if self.config.use_js:
            return self._fetch_js(url)
        return self._fetch_static(url)

    def crawl(self, start_url: str) -> list[PageData]:
        """
        Crawl website starting from the given URL.

        Uses breadth-first search to discover and fetch pages.
        Returns list of PageData objects containing extracted content.
        """
        # Parse and normalize starting URL
        parsed = urlparse(start_url)
        if not parsed.scheme:
            start_url = f"https://{start_url}"
            parsed = urlparse(start_url)

        self.base_domain = parsed.netloc
        start_url = self._normalize_url(start_url)

        # BFS queue: (url, depth)
        queue: deque[tuple[str, int]] = deque([(start_url, 0)])
        self.visited.clear()
        self.pages.clear()

        console.print(f"\n[bold blue]Starting crawl of {self.base_domain}[/bold blue]")
        console.print(f"Max pages: {self.config.max_pages}, Max depth: {self.config.max_depth}")
        console.print(f"Mode: {'JavaScript rendering' if self.config.use_js else 'Static HTML'}\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Crawling...", total=self.config.max_pages)

            while queue and len(self.pages) < self.config.max_pages:
                url, depth = queue.popleft()

                # Skip if already visited or too deep
                if url in self.visited or depth > self.config.max_depth:
                    continue

                self.visited.add(url)

                # Fetch the page
                progress.update(task, description=f"[cyan]Fetching: {url[:60]}...")
                page_data = self._fetch_page(url)

                if page_data.error:
                    console.print(f"[yellow]Warning: Failed to fetch {url}: {page_data.error}[/yellow]")
                else:
                    self.pages.append(page_data)
                    progress.update(task, completed=len(self.pages))

                    # Extract and queue new links
                    if depth < self.config.max_depth:
                        new_links = self._extract_links(page_data.html, url)
                        for link in new_links:
                            if link not in self.visited:
                                queue.append((link, depth + 1))

                # Polite delay between requests
                if self.config.delay > 0:
                    time.sleep(self.config.delay)

        console.print(f"\n[bold green]Crawl complete![/bold green] Fetched {len(self.pages)} pages.")

        return self.pages

    def close(self):
        """Clean up resources."""
        self.session.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
