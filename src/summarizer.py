"""Summarizer that answers questions based on extracted content."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import yaml

from .extractor import ExtractedContent


@dataclass
class QuestionAnswer:
    """A question and its extracted answer."""
    question: str
    answer: str
    sources: list[str] = field(default_factory=list)
    confidence: str = "low"  # low, medium, high


@dataclass
class Summary:
    """Summary of a website based on questions."""
    site_url: str
    site_title: str
    total_pages: int
    answers: list[QuestionAnswer] = field(default_factory=list)
    page_summaries: list[dict] = field(default_factory=list)


class Summarizer:
    """Extracts answers to questions from website content."""

    def __init__(self):
        # Patterns for common data types
        self.patterns = {
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
            "address": r"\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\.?(?:\s*,\s*[\w\s]+)?(?:\s*,\s*[A-Z]{2}\s*\d{5})?",
            "url": r"https?://[^\s<>\"']+",
            "price": r"\$[\d,]+(?:\.\d{2})?",
            "year": r"\b(?:19|20)\d{2}\b",
        }

        # Keywords that indicate specific content types
        self.content_indicators = {
            "mission": ["mission", "vision", "purpose", "goal", "believe", "committed to"],
            "products": ["product", "service", "solution", "offering", "feature"],
            "team": ["team", "leadership", "founder", "ceo", "executive", "staff", "employee"],
            "contact": ["contact", "email", "phone", "address", "reach", "location"],
            "about": ["about", "who we are", "our story", "history", "founded"],
            "pricing": ["pricing", "price", "cost", "plan", "subscription", "free", "premium"],
        }

    def load_questions(self, config_path: Union[str, Path]) -> dict:
        """Load questions from YAML config file."""
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Questions config not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        return config

    def _extract_pattern(self, pattern_name: str, text: str) -> list[str]:
        """Extract all matches for a named pattern."""
        if pattern_name not in self.patterns:
            return []

        matches = re.findall(self.patterns[pattern_name], text, re.IGNORECASE)
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for m in matches:
            if m.lower() not in seen:
                seen.add(m.lower())
                unique.append(m)
        return unique

    def _find_relevant_sentences(
        self,
        text: str,
        keywords: list[str],
        max_sentences: int = 5
    ) -> list[str]:
        """Find sentences containing any of the keywords."""
        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)

        relevant = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(kw.lower() in sentence_lower for kw in keywords):
                cleaned = sentence.strip()
                if len(cleaned) > 20 and len(cleaned) < 500:
                    relevant.append(cleaned)
                    if len(relevant) >= max_sentences:
                        break

        return relevant

    def _extract_section_content(
        self,
        content: ExtractedContent,
        heading_keywords: list[str]
    ) -> str:
        """Extract content under headings matching keywords."""
        # Find relevant headings
        relevant_headings = []
        for heading in content.headings:
            heading_lower = heading["text"].lower()
            if any(kw.lower() in heading_lower for kw in heading_keywords):
                relevant_headings.append(heading["text"])

        if not relevant_headings:
            return ""

        # Try to find content near these headings in raw text
        results = []
        for heading in relevant_headings:
            # Find the heading in raw text and get following content
            pattern = re.escape(heading) + r"[:\s]*(.{50,500}?)(?=\n\n|$)"
            matches = re.findall(pattern, content.raw_text, re.IGNORECASE | re.DOTALL)
            results.extend(matches)

        return " ".join(results[:3])

    def _answer_question(
        self,
        question: str,
        all_content: list[ExtractedContent]
    ) -> QuestionAnswer:
        """Generate an answer for a question from content."""
        question_lower = question.lower()
        sources = []
        answer_parts = []

        # Check for pattern-based questions
        pattern_keywords = {
            "email": ["email", "mail", "contact"],
            "phone": ["phone", "call", "telephone", "number"],
            "address": ["address", "location", "where", "office"],
            "price": ["price", "cost", "pricing", "subscription"],
        }

        # Detect if this is a pattern question
        pattern_type = None
        for ptype, keywords in pattern_keywords.items():
            if any(kw in question_lower for kw in keywords):
                pattern_type = ptype
                break

        # Combine all text
        all_text = "\n".join([c.main_content + " " + c.raw_text for c in all_content])

        # Pattern-based extraction
        if pattern_type:
            matches = self._extract_pattern(pattern_type, all_text)
            if matches:
                answer_parts.extend(matches[:5])
                # Find source pages
                for content in all_content:
                    combined = content.main_content + " " + content.raw_text
                    if any(m in combined for m in matches):
                        sources.append(content.url)

        # Keyword-based extraction
        # Extract keywords from question
        question_words = re.findall(r"\b\w{4,}\b", question_lower)
        stop_words = {"what", "which", "where", "when", "does", "this", "that", "have", "with", "from", "about", "their"}
        keywords = [w for w in question_words if w not in stop_words]

        # Find relevant sentences
        if keywords:
            for content in all_content:
                sentences = self._find_relevant_sentences(
                    content.main_content or content.raw_text,
                    keywords,
                    max_sentences=3
                )
                if sentences:
                    answer_parts.extend(sentences)
                    sources.append(content.url)

        # Also check for section-based content
        section_keywords = self._get_section_keywords(question_lower)
        if section_keywords:
            for content in all_content:
                section_content = self._extract_section_content(content, section_keywords)
                if section_content:
                    answer_parts.append(section_content)
                    if content.url not in sources:
                        sources.append(content.url)

        # Compile answer
        if answer_parts:
            # Deduplicate and format
            unique_parts = []
            seen = set()
            for part in answer_parts:
                part_normalized = part.lower().strip()[:100]
                if part_normalized not in seen:
                    seen.add(part_normalized)
                    unique_parts.append(part.strip())

            answer = "\n\n".join(unique_parts[:5])
            confidence = "high" if len(unique_parts) >= 3 else "medium" if len(unique_parts) >= 1 else "low"
        else:
            answer = "No relevant information found."
            confidence = "low"

        return QuestionAnswer(
            question=question,
            answer=answer,
            sources=list(set(sources))[:3],
            confidence=confidence
        )

    def _get_section_keywords(self, question: str) -> list[str]:
        """Get section keywords based on question content."""
        for category, indicators in self.content_indicators.items():
            if any(ind in question for ind in indicators):
                return indicators
        return []

    def _create_page_summary(self, content: ExtractedContent) -> dict:
        """Create a brief summary for a single page."""
        # Get first few sentences of content
        text = content.main_content or content.raw_text
        sentences = re.split(r"(?<=[.!?])\s+", text)
        summary_sentences = [s.strip() for s in sentences[:3] if len(s.strip()) > 20]

        return {
            "url": content.url,
            "title": content.title,
            "description": content.description or " ".join(summary_sentences)[:300],
            "headings": [h["text"] for h in content.headings[:5]],
        }

    def summarize(
        self,
        content: list[ExtractedContent],
        questions_config: Union[dict, str, Path]
    ) -> Summary:
        """
        Generate a summary answering all questions from the config.

        Args:
            content: List of extracted content from pages
            questions_config: Either a dict of questions or path to YAML file

        Returns:
            Summary object with answers and page summaries
        """
        # Load questions if path provided
        if isinstance(questions_config, (str, Path)):
            questions = self.load_questions(questions_config)
        else:
            questions = questions_config

        # Flatten nested questions
        flat_questions = []
        self._flatten_questions(questions, flat_questions)

        # Get site info
        site_url = content[0].url if content else ""
        site_title = content[0].title if content else "Unknown Site"

        # Answer each question
        answers = []
        for question in flat_questions:
            answer = self._answer_question(question, content)
            answers.append(answer)

        # Create page summaries
        page_summaries = [self._create_page_summary(c) for c in content]

        return Summary(
            site_url=site_url,
            site_title=site_title,
            total_pages=len(content),
            answers=answers,
            page_summaries=page_summaries
        )

    def _flatten_questions(self, obj: Union[dict, list, str], result: list, prefix: str = ""):
        """Flatten nested question structure into a list of question strings."""
        if isinstance(obj, str):
            result.append(obj)
        elif isinstance(obj, list):
            for item in obj:
                self._flatten_questions(item, result, prefix)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                self._flatten_questions(value, result, f"{prefix}{key}.")
