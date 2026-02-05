#!/usr/bin/env python3
"""
Website Scraper - CLI tool for crawling websites and generating summaries.

Usage:
    python -m src.main https://example.com --questions config/questions.yaml
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .crawler import WebCrawler, CrawlerConfig
from .extractor import ContentExtractor
from .summarizer import Summarizer
from .output import MarkdownGenerator

console = Console()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Crawl a website and generate summaries based on questions.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s https://example.com --questions config/questions.yaml
  %(prog)s https://example.com --questions questions.yaml --max-pages 100 --js
  %(prog)s https://spa-site.com --js --delay 2 --output reports/
        """
    )

    parser.add_argument(
        "url",
        help="The URL of the website to crawl"
    )

    parser.add_argument(
        "-q", "--questions",
        type=Path,
        help="Path to YAML file containing questions to answer"
    )

    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("output"),
        help="Output directory for generated files (default: output/)"
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=50,
        help="Maximum number of pages to crawl (default: 50)"
    )

    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="Maximum depth to crawl (default: 5)"
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)"
    )

    parser.add_argument(
        "--js",
        action="store_true",
        help="Use JavaScript rendering (requires Playwright)"
    )

    parser.add_argument(
        "--dump-only",
        action="store_true",
        help="Only generate raw content dump, skip Q&A summary"
    )

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Validate arguments
    if not args.dump_only and not args.questions:
        console.print("[yellow]Warning: No questions file specified. Running in dump-only mode.[/yellow]")
        args.dump_only = True

    if args.questions and not args.questions.exists():
        console.print(f"[red]Error: Questions file not found: {args.questions}[/red]")
        sys.exit(1)

    # Display configuration
    console.print(Panel.fit(
        f"[bold]Website Scraper[/bold]\n\n"
        f"URL: {args.url}\n"
        f"Questions: {args.questions or 'None (dump only)'}\n"
        f"Output: {args.output}\n"
        f"Max pages: {args.max_pages}\n"
        f"JS rendering: {'Yes' if args.js else 'No'}",
        title="Configuration"
    ))

    # Initialize components
    config = CrawlerConfig(
        max_pages=args.max_pages,
        max_depth=args.max_depth,
        delay=args.delay,
        timeout=args.timeout,
        use_js=args.js
    )

    generated_files = []

    try:
        # Step 1: Crawl
        console.print("\n[bold cyan]Step 1: Crawling website...[/bold cyan]")
        with WebCrawler(config) as crawler:
            pages = crawler.crawl(args.url)

        if not pages:
            console.print("[red]Error: No pages were successfully crawled.[/red]")
            sys.exit(1)

        # Step 2: Extract content
        console.print("\n[bold cyan]Step 2: Extracting content...[/bold cyan]")
        extractor = ContentExtractor()
        content = extractor.extract_all(pages)
        console.print(f"[green]Extracted content from {len(content)} pages.[/green]")

        # Step 3: Generate outputs
        console.print("\n[bold cyan]Step 3: Generating outputs...[/bold cyan]")
        output_gen = MarkdownGenerator(args.output)

        # Always generate raw dump (org name extracted automatically from page titles)
        dump_path = output_gen.generate_raw_dump(content)
        generated_files.append(dump_path)
        console.print(f"  [green]Created:[/green] {dump_path}")

        # Generate Q&A summary if questions provided
        if not args.dump_only and args.questions:
            console.print("\n[bold cyan]Step 4: Generating Q&A summary...[/bold cyan]")
            summarizer = Summarizer()
            summary = summarizer.summarize(content, args.questions)

            summary_path = output_gen.generate_summary_report(summary)
            generated_files.append(summary_path)
            console.print(f"  [green]Created:[/green] {summary_path}")

            # Display summary preview
            console.print("\n[bold]Summary Preview:[/bold]")
            table = Table(show_header=True)
            table.add_column("Question", style="cyan", max_width=50)
            table.add_column("Confidence", justify="center")
            table.add_column("Answer Preview", max_width=40)

            for qa in summary.answers[:5]:
                answer_preview = qa.answer[:80] + "..." if len(qa.answer) > 80 else qa.answer
                answer_preview = answer_preview.replace("\n", " ")
                conf_color = {"high": "green", "medium": "yellow", "low": "red"}.get(qa.confidence, "white")
                table.add_row(
                    qa.question[:50],
                    f"[{conf_color}]{qa.confidence}[/{conf_color}]",
                    answer_preview
                )

            console.print(table)

        # Generate index
        index_path = output_gen.generate_index(generated_files)
        console.print(f"\n  [green]Index:[/green] {index_path}")

        # Final summary
        console.print(Panel.fit(
            f"[bold green]Scraping complete![/bold green]\n\n"
            f"Pages crawled: {len(pages)}\n"
            f"Files generated: {len(generated_files) + 1}\n"
            f"Output directory: {args.output.absolute()}",
            title="Complete"
        ))

    except KeyboardInterrupt:
        console.print("\n[yellow]Crawl interrupted by user.[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        raise


if __name__ == "__main__":
    main()
