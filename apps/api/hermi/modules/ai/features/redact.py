# ruff: noqa: E501
"""Personal data out of a prompt, and back into the result (06 sections 12.2 and 12.3).

Names become `Traveler A`, `Traveler B` ... per call. Emails and long digit runs (phone, card and loyalty numbers)
become `[EMAIL_n]` and `[REF_n]`. The map lives only in the Redactor for one call and is dropped with it.
"""

import re
import string

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_DIGITS = re.compile(r"(?<![\w-])\+?\d[\d ().-]{7,}\d(?![\w-])")
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_MIN_PART = 3  # shortcut: name parts under 3 letters are not matched alone. Ceiling: "Al" in free text goes through. Trigger: a leak report.


class Redactor:
    def __init__(self, names: list[str]) -> None:
        self._names: dict[str, str] = {}  # lowercase name or name part -> placeholder
        self._back: dict[str, str] = {}  # placeholder -> the full name as stored
        seen: set[str] = set()
        for full in dict.fromkeys(n.strip() for n in names if n and n.strip()):
            if full.lower() in seen:
                continue
            ph = f"Traveler {string.ascii_uppercase[len(self._back) % 26]}{'' if len(self._back) < 26 else len(self._back) // 26}"
            self._back[ph] = full
            for key in {full.lower(), *(p.lower() for p in re.split(r"\s+", full) if len(p) >= _MIN_PART)}:
                if key not in seen:
                    seen.add(key)
                    self._names[key] = ph
        self._values: dict[str, str] = {}  # [EMAIL_1] -> original

    def clean(self, text: str | None, *, pii: bool = True) -> str:
        """Names always. With `pii` (free text) also emails and long digit runs; structured data skips it."""
        if not text:
            return ""
        out = text
        for kind, rx in (("EMAIL", _EMAIL), ("REF", _DIGITS)) if pii else ():

            def sub(m: re.Match, kind: str = kind) -> str:
                if _DATE.fullmatch(m.group(0)):
                    return m.group(0)
                n = sum(1 for k in self._values if k.startswith(f"[{kind}_")) + 1
                ph = f"[{kind}_{n}]"
                self._values[ph] = m.group(0)
                return ph

            out = rx.sub(sub, out)
        for key in sorted(self._names, key=len, reverse=True):
            out = re.sub(rf"(?<!\w){re.escape(key)}(?!\w)", self._names[key], out, flags=re.IGNORECASE)
        return out

    def clean_deep(self, value):
        """`clean` over every string in a nested value (dict keys are left alone)."""
        if isinstance(value, str):
            return self.clean(value, pii=False)
        if isinstance(value, list):
            return [self.clean_deep(v) for v in value]
        if isinstance(value, dict):
            return {k: self.clean_deep(v) for k, v in value.items()}
        return value

    def restore(self, text: str) -> str:
        for ph, original in {**self._back, **self._values}.items():
            text = text.replace(ph, original)
        return text

    def restore_deep(self, value):
        if isinstance(value, str):
            return self.restore(value)
        if isinstance(value, list):
            return [self.restore_deep(v) for v in value]
        if isinstance(value, dict):
            return {k: self.restore_deep(v) for k, v in value.items()}
        return value
