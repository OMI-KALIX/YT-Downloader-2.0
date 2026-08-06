"""
Modular Extractor Registry for AnyDownloader.
Allows registering site-specific extraction options, domain matchers, and custom headers.
"""
from typing import Dict, Any, List, Optional
import re

class SiteExtractorConfig:
    def __init__(self, name: str, domain_pattern: str, cookie_domain: str, default_format: str = "best"):
        self.name = name
        self.domain_pattern = re.compile(domain_pattern, re.IGNORECASE)
        self.cookie_domain = cookie_domain
        self.default_format = default_format

class ExtractorRegistry:
    def __init__(self):
        self._extractors: List[SiteExtractorConfig] = []
        self._register_defaults()

    def _register_defaults(self):
        # Register standard supported sites
        self.register(SiteExtractorConfig("YouTube", r"(youtube\.com|youtu\.be)", ".youtube.com"))
        self.register(SiteExtractorConfig("Vimeo", r"vimeo\.com", ".vimeo.com"))
        self.register(SiteExtractorConfig("Twitter/X", r"(twitter\.com|x\.com)", ".twitter.com"))
        self.register(SiteExtractorConfig("TikTok", r"tiktok\.com", ".tiktok.com"))

    def register(self, config: SiteExtractorConfig):
        self._extractors.append(config)

    def match(self, url: str) -> Optional[SiteExtractorConfig]:
        for ext in self._extractors:
            if ext.domain_pattern.search(url):
                return ext
        return None

extractor_registry = ExtractorRegistry()
