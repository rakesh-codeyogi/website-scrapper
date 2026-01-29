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
        output_path = self.output_dir / f"{site_name}_summary.md"
        output_path.write_text("\n".join(lines), encoding="utf-8")

        return output_path

    def generate_raw_dump(self, content: list[ExtractedContent], site_name: str = "website") -> Path:
        """
        Generate a complete dump of all extracted content.

        Returns path to the generated file.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        output_path = self.output_dir / f"{site_name}_site_dump.md"
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
