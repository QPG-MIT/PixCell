"""Shared model-output recovery for evaluation and training."""

from __future__ import annotations

import re


_CODE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_code(text: str) -> str:
    """Recover a complete Python answer without exposing verifier feedback."""

    close = text.find("</think>")
    opening = text.find("<think>")
    if close >= 0 and (opening < 0 or opening > close):
        text = text[close + len("</think>") :]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    blocks = _CODE_RE.findall(text)
    if blocks:
        return blocks[-1].strip()
    if "import gdsfactory" in text and "write_gds" in text:
        start = text.find("import ")
        return text[start:].strip() if start >= 0 else text.strip()
    return text.strip()
