"""
Prompt Injection Detection Engine.

Classifies content by trust level and scans for injection patterns
in external/untrusted content (web pages, PDFs, emails, etc.).

Trust levels:
  TRUSTED (user direct input) > SYSTEM (system prompts) >
  ELEVATED (approved files) > UNTRUSTED (external content)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from loguru import logger


class TrustLevel(IntEnum):
    UNTRUSTED = 0    # External: web, PDFs, emails, clipboard from web
    ELEVATED = 25    # User-approved files, known-good sources
    SYSTEM = 50      # System prompts, internal config
    TRUSTED = 100    # Direct user input


@dataclass
class InjectionResult:
    detected: bool
    confidence: float          # 0.0 - 1.0
    patterns_matched: list[str]
    severity: str              # "low", "medium", "high", "critical"
    sanitized_text: str        # Text with injections neutralized
    details: str = ""


# ── Injection patterns ───────────────────────────────────────────────────

# High-confidence: these almost always indicate injection attempts
HIGH_CONFIDENCE_PATTERNS = [
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|directives?)", "ignore_previous_instructions"),
    (r"(disregard|forget|override)\s+(all\s+)?(your|the|any)\s+(instructions?|rules?|guidelines?|constraints?)", "override_instructions"),
    (r"you\s+are\s+now\s+(a|an|the)\s+", "role_reassignment"),
    (r"new\s+(instructions?|directives?|rules?)\s*:", "new_instructions"),
    (r"system\s*:\s*(you|the|this)", "fake_system_prompt"),
    (r"\[SYSTEM\]|\[ADMIN\]|\[OVERRIDE\]|\[ROOT\]", "fake_privilege_tag"),
    (r"<\|?(system|im_start|endoftext|im_end)\|?>", "model_token_injection"),
    (r"```\s*(system|prompt|instructions?)\s*\n", "code_block_injection"),
    (r"(act|behave|respond)\s+as\s+if\s+(you|there)\s+(are|were|have)\s+no\s+(restrict|rules?|limit)", "remove_restrictions"),
    (r"pretend\s+(that\s+)?(you|there)\s+(are|is)\s+no\s+(filter|restrict|censor|modera)", "bypass_filter"),
]

# Medium-confidence: suspicious but could be legitimate
MEDIUM_CONFIDENCE_PATTERNS = [
    (r"(do\s+not|don'?t)\s+(follow|obey|listen\s+to)\s+(the|your|any)\s+(rules?|instructions?)", "refuse_rules"),
    (r"(reveal|show|tell|output|print)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?|rules?|guidelines?)", "prompt_extraction"),
    (r"(what|repeat|recite)\s+(is|are)\s+(your|the)\s+(system\s+)?(prompt|instructions?)", "prompt_extraction_query"),
    (r"from\s+now\s+on,?\s+(you|always|never|only)", "persistent_override"),
    (r"(answer|reply|respond)\s+(only\s+)?(with|in)\s+(yes|no|true|json)", "output_constraint"),
    (r"(base64|rot13|hex)\s*(encode|decode|convert)", "encoding_evasion"),
    (r"translate.*to.*and\s+(then|also|additionally)", "chained_instruction"),
]

# Low-confidence: might be injection, context-dependent
LOW_CONFIDENCE_PATTERNS = [
    (r"(please|kindly)\s+(ignore|skip|bypass|disable)", "polite_bypass"),
    (r"(in\s+)?your\s+(role|capacity)\s+as\s+(a|an)\s+", "role_suggestion"),
    (r"jailbreak|DAN\s+mode|developer\s+mode", "known_jailbreak"),
]


class InjectionDetector:
    """Scans text for prompt injection patterns."""

    def __init__(self) -> None:
        self._high: list[tuple[re.Pattern, str]] = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE), name)
            for p, name in HIGH_CONFIDENCE_PATTERNS
        ]
        self._medium: list[tuple[re.Pattern, str]] = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE), name)
            for p, name in MEDIUM_CONFIDENCE_PATTERNS
        ]
        self._low: list[tuple[re.Pattern, str]] = [
            (re.compile(p, re.IGNORECASE | re.MULTILINE), name)
            for p, name in LOW_CONFIDENCE_PATTERNS
        ]

    def scan(
        self,
        text: str,
        trust_level: TrustLevel = TrustLevel.UNTRUSTED,
    ) -> InjectionResult:
        """Scan text for injection patterns. More aggressive for untrusted content."""
        if not text or not text.strip():
            return InjectionResult(
                detected=False, confidence=0.0, patterns_matched=[],
                severity="none", sanitized_text=text,
            )

        matched: list[tuple[str, str, float]] = []  # (name, severity, conf)

        # Always check high patterns
        for pat, name in self._high:
            if pat.search(text):
                matched.append((name, "critical", 0.95))

        # Check medium for UNTRUSTED and ELEVATED
        if trust_level <= TrustLevel.ELEVATED:
            for pat, name in self._medium:
                if pat.search(text):
                    matched.append((name, "high", 0.70))

        # Check low only for UNTRUSTED
        if trust_level <= TrustLevel.UNTRUSTED:
            for pat, name in self._low:
                if pat.search(text):
                    matched.append((name, "medium", 0.45))

        if not matched:
            return InjectionResult(
                detected=False, confidence=0.0, patterns_matched=[],
                severity="none", sanitized_text=text,
            )

        # Aggregate
        max_conf = max(m[2] for m in matched)
        max_sev = max(matched, key=lambda m: m[2])[1]
        pattern_names = [m[0] for m in matched]

        # Combined confidence: increases with more matches
        combined_conf = min(1.0, max_conf + 0.05 * (len(matched) - 1))

        # Sanitize: wrap detected injections with neutralization markers
        sanitized = text
        for pat, name in self._high:
            sanitized = pat.sub(f"[INJECTION_BLOCKED:{name}]", sanitized)
        if trust_level <= TrustLevel.ELEVATED:
            for pat, name in self._medium:
                sanitized = pat.sub(f"[INJECTION_SUSPECT:{name}]", sanitized)

        details = f"Detected {len(matched)} pattern(s): {', '.join(pattern_names)}"

        logger.warning(f"Injection detected (trust={trust_level.name}): {details}")

        return InjectionResult(
            detected=True,
            confidence=combined_conf,
            patterns_matched=pattern_names,
            severity=max_sev,
            sanitized_text=sanitized,
            details=details,
        )

    def classify_source(self, source: str) -> TrustLevel:
        """Classify a content source by trust level."""
        source_lower = source.lower()
        trusted_sources = {"user_input", "chat_message", "direct_command"}
        system_sources = {"system_prompt", "mode_prompt", "config"}
        elevated_sources = {"local_file", "approved_skill", "workspace_file"}

        if source_lower in trusted_sources:
            return TrustLevel.TRUSTED
        if source_lower in system_sources:
            return TrustLevel.SYSTEM
        if source_lower in elevated_sources:
            return TrustLevel.ELEVATED
        return TrustLevel.UNTRUSTED

    def scan_and_block(
        self,
        text: str,
        source: str = "external",
        threshold: float = 0.70,
    ) -> tuple[bool, InjectionResult]:
        """Convenience: scan and return (should_block, result)."""
        trust = self.classify_source(source)
        result = self.scan(text, trust)
        should_block = result.detected and result.confidence >= threshold
        return should_block, result


# ── Singleton ────────────────────────────────────────────────────────────

_detector: InjectionDetector | None = None


def get_injection_detector() -> InjectionDetector:
    global _detector
    if _detector is None:
        _detector = InjectionDetector()
    return _detector
