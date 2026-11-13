"""Reply normalizer (TEST-PLAN-v3 section 6).

Model judges tend to favor Markdown formatting, so every reply is converted to plain text before
anyone (graders or JC) sees it. The normalizer removes ONLY emphasis and heading markup:
  - ATX headings ("## Fix" -> "Fix") and setext underlines ("====");
  - bold and italic markers (**x**, __x__, *x*, _x_, ***x***).
It keeps, byte for byte: fenced code blocks, inline code, indentation, list bullets and numbers,
commands, URLs, table rows, snake_case names and environment variables. Originals are kept.
"""
import re

FENCE = re.compile(r"(^[ \t]*```.*?^[ \t]*```[ \t]*$|^[ \t]*```.*\Z)", re.S | re.M)
INLINE_CODE = re.compile(r"(`+)(?:(?!\1).)+?\1")
URL = re.compile(r"(?:https?://|www\.)[^\s<>()\]]+|<[^>\s]+>|\]\([^)\s]+\)")
DUNDER = re.compile(r"(?<!\w)__[a-z0-9_]+__(?!\w)")  # Python-style names such as __init__
PROTECT = re.compile(f"{INLINE_CODE.pattern}|{URL.pattern}|{DUNDER.pattern}")

ATX = re.compile(r"^([ \t]{0,3})#{1,6}[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
SETEXT = re.compile(r"^[ \t]{0,3}=+[ \t]*$")
BOLD_ITAL = re.compile(r"(?<![\w*])\*\*\*(?=\S)(.+?)(?<=\S)\*\*\*(?![\w*])")
BOLD_STAR = re.compile(r"(?<![\w*])\*\*(?=\S)(.+?)(?<=\S)\*\*(?![\w*])")
BOLD_UND = re.compile(r"(?<![\w_])__(?=\S)(.+?)(?<=\S)__(?![\w_])")
ITAL_STAR = re.compile(r"(?<![\w*])\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?![\w*])")
ITAL_UND = re.compile(r"(?<![\w_])_(?=[^\s_])(.+?)(?<=[^\s_])_(?![\w_])")


def _strip_emphasis(line):
    # Mask inline code and URLs so nothing inside them is touched.
    saved = []

    def mask(m):
        saved.append(m.group(0))
        return f"\x00{len(saved) - 1}\x00"
    s = PROTECT.sub(mask, line)
    for rx in (BOLD_ITAL, BOLD_STAR, BOLD_UND, ITAL_STAR, ITAL_UND):
        s = rx.sub(r"\1", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: saved[int(m.group(1))], s)


def _prose(block):
    out = []
    lines = block.split("\n")
    for i, line in enumerate(lines):
        m = ATX.match(line)
        if m:
            line = m.group(1) + m.group(2)
        elif SETEXT.match(line) and i > 0 and lines[i - 1].strip():
            continue  # underline of a setext heading
        out.append(_strip_emphasis(line))
    return "\n".join(out)


def normalize(text):
    if not text:
        return text
    parts, last = [], 0
    for m in FENCE.finditer(text):
        parts.append(_prose(text[last:m.start()]))
        parts.append(m.group(0))  # fenced code: untouched
        last = m.end()
    parts.append(_prose(text[last:]))
    return "".join(parts)


# ----------------------------------------------------------------------------- self-test
CASES = [
    ("## Likely cause\nThe **Merge** node", "Likely cause\nThe Merge node"),
    ("Set `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` and N8N_HOST_NAME too", "Set `N8N_BLOCK_ENV_ACCESS_IN_NODE=false` and N8N_HOST_NAME too"),
    ("* item one\n* item *two*\n  - nested", "* item one\n* item two\n  - nested"),
    ("1. Open **Settings** > _Credentials_", "1. Open Settings > Credentials"),
    ("See https://docs.n8n.io/hosting/configuration/environment-variables/_file_ and __init__", "See https://docs.n8n.io/hosting/configuration/environment-variables/_file_ and __init__"),
    ("```bash\n# not a heading\ndocker run **x** _y_\n```\nAfter **bold**", "```bash\n# not a heading\ndocker run **x** _y_\n```\nAfter bold"),
    ("| **Field** | Value |\n|---|---|\n| a_b | `x*y*z` |", "| Field | Value |\n|---|---|\n| a_b | `x*y*z` |"),
    ("Title\n=====\nBody", "Title\nBody"),
    ("2 * 3 * 4 = 24 and a*b", "2 * 3 * 4 = 24 and a*b"),
    ("    indented code **stays** only if fenced", "    indented code stays only if fenced"),
    ("[the docs](https://docs.n8n.io/a_b_c_) say ***this***", "[the docs](https://docs.n8n.io/a_b_c_) say this"),
    ("{{ $json.body.my_field }} and $('Node_A').item", "{{ $json.body.my_field }} and $('Node_A').item"),
]


def selftest(replies=()):
    bad = [(i, normalize(a), b) for i, (a, b) in enumerate(CASES) if normalize(a) != b]
    for i, got, want in bad:
        print(f"case {i}: got {got!r}\n        want {want!r}")
    # Property check on real replies: only emphasis/heading characters may disappear, and every
    # fenced block, inline code span and URL must survive byte for byte.
    prop_fail = 0
    for r in replies:
        n = normalize(r)
        keep = lambda t: re.sub(r"[*_#=\s]", "", t)
        if keep(n) != keep(r):
            prop_fail += 1
        for rx in (FENCE, INLINE_CODE, URL):
            if [m.group(0) for m in rx.finditer(r)] != [m.group(0) for m in rx.finditer(n)]:
                prop_fail += 1
                break
    return len(bad), prop_fail
