"""Markdown output generation for scraped content and summaries."""

from datetime import datetime
from pathlib import Path
from typing import Union

from .extractor import ExtractedContent
from .summarizer import Summary


class MarkdownGenerator:
    """Generates markdown files from scraped content and summaries."""

    def __init__(self, output_dir: Union[str, Path] = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for use as filename."""
        # Remove/replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, "_")
        # Limit length and strip whitespace
        return name.strip()[:100]

    def _extract_org_name(self, titles: list[str]) -> str:
        """
        Extract organization name from page titles.

        Handles common patterns like:
        - "Home - WHEELS Global Foundation" → "WHEELS Global Foundation"
        - "About | Company Name" → "Company Name"
        - "Company Name :: Products" → "Company Name"
        """
        if not titles:
            return "website"

        # Common separators in page titles
        separators = [' - ', ' | ', ' :: ', ' : ', ' — ', ' – ']

        # Common page type prefixes/suffixes to ignore
        page_types = {
            'home', 'about', 'about us', 'contact', 'contact us',
            'products', 'services', 'blog', 'news', 'team', 'careers',
            'faq', 'help', 'support', 'login', 'sign in', 'register'
        }

        # Try to find common part across multiple titles
        candidates = []

        for title in titles[:5]:  # Check first 5 pages
            if not title:
                continue

            # Split by separators and find the org name part
            parts = [title]
            for sep in separators:
                new_parts = []
                for part in parts:
                    new_parts.extend(part.split(sep))
                parts = new_parts

            # Filter out page type words, keep likely org names
            for part in parts:
                part = part.strip()
                if part.lower() not in page_types and len(part) > 2:
                    candidates.append(part)

        if not candidates:
            return titles[0] if titles else "website"

        # Find the most common candidate (likely the org name)
        from collections import Counter
        counts = Counter(candidates)
        most_common = counts.most_common(1)[0][0]

        return most_common

    def generate_summary_report(self, summary: Summary) -> Path:
        """
        Generate a comprehensive markdown report from summary.

        Returns path to the generated file.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        site_name = self._sanitize_filename(summary.site_title) or "website"

        lines = [
            f"# Website Summary: {summary.site_title}",
            "",
            f"**URL:** {summary.site_url}",
            f"**Pages Crawled:** {summary.total_pages}",
            f"**Generated:** {timestamp}",
            "",
            "---",
            "",
        ]

        # Questions and Answers section
        if summary.answers:
            lines.extend([
                "## Questions & Answers",
                "",
            ])

            for i, qa in enumerate(summary.answers, 1):
                confidence_emoji = {
                    "high": "[checkmark]",
                    "medium": "[partial]",
                    "low": "[?]"
                }.get(qa.confidence, "")

                lines.extend([
                    f"### {i}. {qa.question}",
                    "",
                    qa.answer,
                    "",
                ])

                if qa.sources:
                    lines.append("**Sources:**")
                    for source in qa.sources:
                        lines.append(f"- {source}")
                    lines.append("")

                lines.extend([
                    f"*Confidence: {qa.confidence}*",
                    "",
                    "---",
                    "",
                ])

        # Page summaries section
        if summary.page_summaries:
            lines.extend([
                "## Pages Crawled",
                "",
            ])

            for page in summary.page_summaries:
                lines.extend([
                    f"### {page['title'] or 'Untitled Page'}",
                    "",
                    f"**URL:** {page['url']}",
                    "",
                ])

                if page.get('description'):
                    lines.extend([
                        page['description'],
                        "",
                    ])

                if page.get('headings'):
                    lines.append("**Key sections:**")
                    for heading in page['headings']:
                        lines.append(f"- {heading}")
                    lines.append("")

                lines.append("---")
                lines.append("")

        # Write to file
        output_path = self.output_dir / f"{site_name} - Summary.md"
        output_path.write_text("\n".join(lines), encoding="utf-8")

        return output_path

    def generate_raw_dump(self, content: list[ExtractedContent], site_name: str = None) -> Path:
        """
        Generate a complete dump of all extracted content.

        Returns path to the generated file.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Extract organization name from page titles
        if site_name is None:
            titles = [page.title for page in content if page.title]
            site_name = self._extract_org_name(titles)

        site_name = self._sanitize_filename(site_name)

        lines = [
            f"# Full Content Dump: {site_name}",
            "",
            f"**Total Pages:** {len(content)}",
            f"**Generated:** {timestamp}",
            "",
            "---",
            "",
        ]

        for i, page in enumerate(content, 1):
            lines.extend([
                f"## Page {i}: {page.title or 'Untitled'}",
                "",
                f"**URL:** {page.url}",
                "",
            ])

            if page.description:
                lines.extend([
                    "### Description",
                    "",
                    page.description,
                    "",
                ])

            if page.metadata:
                lines.extend([
                    "### Metadata",
                    "",
                ])
                for key, value in page.metadata.items():
                    lines.append(f"- **{key}:** {value}")
                lines.append("")

            if page.headings:
                lines.extend([
                    "### Headings",
                    "",
                ])
                for heading in page.headings:
                    indent = "  " * (heading["level"] - 1)
                    lines.append(f"{indent}- {heading['text']}")
                lines.append("")

            if page.main_content:
                lines.extend([
                    "### Content",
                    "",
                    page.main_content,
                    "",
                ])

            lines.extend([
                "---",
                "",
            ])

        # Write to file
        output_path = self.output_dir / f"{site_name}.md"
        output_path.write_text("\n".join(lines), encoding="utf-8")

        return output_path

    def generate_index(self, generated_files: list[Path]) -> Path:
        """
        Generate an index file linking to all generated reports.

        Returns path to the index file.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            "# Website Scraper Output",
            "",
            f"**Generated:** {timestamp}",
            "",
            "## Generated Files",
            "",
        ]

        for file_path in generated_files:
            relative_path = file_path.name
            lines.append(f"- [{file_path.stem}]({relative_path})")

        lines.append("")

        # Write to file
        output_path = self.output_dir / "index.md"
        output_path.write_text("\n".join(lines), encoding="utf-8")

        return output_path
