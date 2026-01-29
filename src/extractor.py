"""Content extraction from HTML pages."""

import re
from dataclasses import dataclass, field
from typing import Optional

from bs4 import BeautifulSoup, NavigableString
from readability import Document

from .crawler import PageData


@dataclass
class ExtractedContent:
    """Extracted and cleaned content from a page."""
    url: str
    title: str
    description: str = ""
    main_content: str = ""
    headings: list[dict] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    raw_text: str = ""


class ContentExtractor:
    """Extracts clean, structured content from HTML pages."""

    def __init__(self):
        # Tags to remove completely
        self.remove_tags = [
            "script", "style", "noscript", "iframe", "svg",
            "canvas", "video", "audio", "map", "object", "embed"
        ]
        # Common navigation/footer class patterns
        self.skip_patterns = [
            r"nav", r"header", r"footer", r"sidebar", r"menu",
            r"breadcrumb", r"pagination", r"comment", r"social",
            r"share", r"related", r"advertisement", r"ad-", r"ads-",
            r"cookie", r"popup", r"modal", r"banner"
        ]

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        # Replace multiple whitespace with single space
        text = re.sub(r"\s+", " ", text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def _should_skip_element(self, element) -> bool:
        """Check if element should be skipped based on class/id."""
        classes = element.get("class", [])
        element_id = element.get("id", "")

        # Convert to string for pattern matching
        class_str = " ".join(classes) if isinstance(classes, list) else str(classes)
        check_str = f"{class_str} {element_id}".lower()

        for pattern in self.skip_patterns:
            if re.search(pattern, check_str, re.IGNORECASE):
                return True
        return False

    def _extract_with_readability(self, html: str, url: str) -> tuple[str, str]:
        """Use readability to extract main content."""
        try:
            doc = Document(html)
            title = doc.title()
            content_html = doc.summary()

            # Parse the extracted content
            soup = BeautifulSoup(content_html, "lxml")
            content_text = self._clean_text(soup.get_text())

            return title, content_text
        except Exception:
            return "", ""

    def _extract_headings(self, soup: BeautifulSoup) -> list[dict]:
        """Extract all headings with their hierarchy."""
        headings = []
        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                text = self._clean_text(heading.get_text())
                if text:
                    headings.append({
                        "level": level,
                        "text": text
                    })
        return headings

    def _extract_metadata(self, soup: BeautifulSoup) -> dict:
        """Extract page metadata from meta tags."""
        metadata = {}

        # Standard meta tags
        meta_mappings = {
            "description": ["description", "og:description", "twitter:description"],
            "keywords": ["keywords"],
            "author": ["author", "article:author"],
            "published": ["article:published_time", "datePublished"],
            "modified": ["article:modified_time", "dateModified"],
        }

        for key, names in meta_mappings.items():
            for name in names:
                meta = soup.find("meta", attrs={"name": name}) or \
                       soup.find("meta", attrs={"property": name})
                if meta and meta.get("content"):
                    metadata[key] = meta["content"]
                    break

        # Extract canonical URL
        canonical = soup.find("link", rel="canonical")
        if canonical and canonical.get("href"):
            metadata["canonical"] = canonical["href"]

        return metadata

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[dict]:
        """Extract all links with their text."""
        links = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            text = self._clean_text(anchor.get_text())
            if text and not href.startswith(("#", "javascript:", "mailto:")):
                links.append({
                    "text": text,
                    "url": href
                })
        return links

    def _get_raw_text(self, soup: BeautifulSoup) -> str:
        """Get all text content from the page."""
        # Remove unwanted tags
        for tag in self.remove_tags:
            for element in soup.find_all(tag):
                element.decompose()

        # Get text
        text = soup.get_text(separator=" ")
        return self._clean_text(text)

    def extract(self, page: PageData) -> ExtractedContent:
        """
        Extract structured content from a page.

        Returns ExtractedContent with cleaned text, headings, and metadata.
        """
        if page.error or not page.html:
            return ExtractedContent(
                url=page.url,
                title=page.title or "Error loading page"
            )

        soup = BeautifulSoup(page.html, "lxml")

        # Extract using readability for main content
        readability_title, main_content = self._extract_with_readability(page.html, page.url)

        # Extract metadata
        metadata = self._extract_metadata(soup)

        # Extract headings
        headings = self._extract_headings(soup)

        # Extract links
        links = self._extract_links(soup, page.url)

        # Get raw text as fallback
        raw_text = self._get_raw_text(soup)

        # Use best available title
        title = page.title or readability_title or metadata.get("title", "Untitled")

        return ExtractedContent(
            url=page.url,
            title=title,
            description=metadata.get("description", ""),
            main_content=main_content or raw_text[:5000],
            headings=headings,
            links=links,
            metadata=metadata,
            raw_text=raw_text
        )

    def extract_all(self, pages: list[PageData]) -> list[ExtractedContent]:
        """Extract content from multiple pages."""
        return [self.extract(page) for page in pages]
