"""Inline the small data (summary, docs gap, the 240-question index) into the page. Writes index.html (full document,
for static hosting) and artifact.html (body only, for the private review copy)."""
import json, sys
from pathlib import Path
root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
D = root / "data"
qs = {}
for key, name in (("practice", "Practice"), ("test", "Test"), ("holdout", "Holdout")):
    for q in json.loads((D / f"replies-{key}.json").read_text())["questions"]:
        qs[q["id"]] = {k: q[k] for k in ("title", "url", "category", "fix", "community_has_fix")} | {"set": name}
data = {"summary": json.loads((D / "summary.json").read_text()), "docsgap": json.loads((D / "docsgap.json").read_text()), "questions": qs}
blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
body = (root / "template3.html").read_text().replace("/*__DATA__*/", blob)
(root / "artifact.html").write_text(body)
head = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')
i = body.index("<style>")
full = head + body[:i] + body[i:body.index("</style>") + 8] + "\n</head>\n<body>\n" + body[body.index("</style>") + 8:] + "\n</body>\n</html>\n"
(root / "index.html").write_text(full)
print("artifact.html", len(body), "index.html", len(full))
