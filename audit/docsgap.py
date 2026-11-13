"""Docs-gap report (TEST-PLAN-v3 section 17): where the fix for each of the 240 questions lived, and what n8n could
write or tell a bot. Built from the final labels and the labelers' one-line fix summaries (site/data/replies-*.json,
written by audit.site3) and the theme map in data/docs_gap_themes.json. No model call.

  python3 -m audit.docsgap        # writes DOCS-GAP.md and site/data/docsgap.json
"""
import json
from collections import Counter

from .common import ROOT

SETS = (("practice", "Practice"), ("test", "Test"), ("holdout", "Holdout"))
CATS = [("n8n_docs", "In n8n's docs"), ("general_tech", "General technical know-how"),
        ("undocumented_n8n", "n8n know-how the docs don't have"), ("bug_or_release", "A known bug or release issue"),
        ("account_access", "Only n8n staff can act")]


def load():
    qs = {}
    for key, name in SETS:
        for q in json.loads((ROOT / f"site/data/replies-{key}.json").read_text())["questions"]:
            qs[q["id"]] = {**q, "set": name}
    return qs


def build():
    qs, T = load(), json.loads((ROOT / "data/docs_gap_themes.json").read_text())
    seen = Counter(i for t in T["themes"] for i in t["ids"])
    human = {i for i, q in qs.items() if q["side"] == "human"}
    problems = [f"{i} in {n} themes" for i, n in seen.items() if n > 1]
    problems += [f"{i} on the human side but in no theme" for i in human - set(seen)]
    problems += [f"{i} in a theme but not on the human side" for i in set(seen) - human]
    for t in T["themes"]:
        cat = T["groups"][t["group"]]["category"]
        problems += [f"{i} is {qs[i]['category']}, theme group wants {cat}" for i in t["ids"] if i in qs and qs[i]["category"] != cat]
    problems += [f"{i} (exactly-once list) is {qs[i]['category']}" for i in T["general"]["ids"] if qs[i]["category"] != "general_tech"]
    table = {c: Counter(q["set"] for q in qs.values() if q["category"] == c) for c, _ in CATS}
    return qs, T, table, problems


def row(q):
    flag = " (forum had the fix earlier)" if q.get("community_has_fix") else ""
    return f"| [{q['title'].replace('|', '/')}]({q['url']}) | {q['set']} | {q['fix'].replace('|', '/')}{flag} |"


def markdown(qs, T, table):
    n = len(qs); nh = sum(q["side"] == "human" for q in qs.values())
    L = ["# Docs-gap report: where the fix lived for 240 n8n community questions", "",
         f"Every question in this audit came from the [n8n community forum](https://community.n8n.io) and had an accepted answer "
         f"from someone other than the asker. Two AI labelers from different companies, a blind tie-breaker and a human "
         f"reading of their disagreements decided where each fix lived. {nh} of the {n} questions ({round(100 * nh / n)}%) "
         f"needed something the docs don't have. This report sorts them into what n8n could write, what a bot should be told, "
         f"and what will always need a person.", "",
         f"It is written to be useful to n8n's team. The docs are open source and held the fix for {sum(table['n8n_docs'].values())} "
         f"of these {n} questions outright, and the forum answers that make up the answer key are the community's work. "
         "The point is that support conversations already show which articles to write next.", "",
         "| Where the fix lived | " + " | ".join(s for _, s in SETS) + f" | All {n} |", "|---|" + "---|" * (len(SETS) + 1)]
    for c, label in CATS:
        L.append(f"| {label} | " + " | ".join(str(table[c][s]) for _, s in SETS) + f" | **{sum(table[c].values())}** |")
    L += ["", "Fix summaries are the labeler's own one-line paraphrase of the accepted answer, not the forum text. "
          "Follow the link to read the thread and credit its author.", ""]
    for g, G in T["groups"].items():
        th = [t for t in T["themes"] if t["group"] == g]
        L += [f"## {G['title']} ({sum(len(t['ids']) for t in th)})", "", G["lede"], ""]
        for t in sorted(th, key=lambda t: -len(t["ids"])):
            L += [f"### {t['title']} ({len(t['ids'])})", "", f"**{'Write' if g == 'article' else 'Tell the bot' if g == 'known_issue' else 'Route'}:** {t['suggestion']}", "",
                  "| Question | Set | The fix that worked |", "|---|---|---|"] + [row(qs[i]) for i in t["ids"]] + [""]
    G = T["general"]
    L += [f"## {G['title']} ({len(G['ids'])} of {sum(table['general_tech'].values())})", "", G["suggestion"], "",
          "| Question | Set | The fix that worked |", "|---|---|---|"] + [row(qs[i]) for i in G["ids"]] + [""]
    comm = [q for q in qs.values() if q.get("community_has_fix") is not None]
    L += ["## What the forum already knew", "",
          f"For the {len(comm)} practice and test questions on the n8n-know-how and known-issue side, we searched a harvest of "
          f"2,739 solved threads, keeping for each question only answers posted before it (about 2,070 per question). The fix was there for "
          f"{sum(bool(q['community_has_fix']) for q in comm)} of {len(comm)}. Most gaps are new when they reach the forum, so a "
          f"bot fed past answers mostly can't close them; articles and a known-issues feed can.", "",
          "## How this was built, and its limits", "",
          "- Labels: two labelers (Claude Sonnet 5.5 and Gemini 3.8 Flash) each searched the docs three ways and chose a "
          "category; a blind tie-breaker (Muse Spark 1.3) settled disagreements; Jonathan Marx read every disagreement that "
          "crossed the line between answerable and needs-a-human. Rules: `rubric/LABELING-v2.md`.",
          "- The docs are pinned to one commit (`data/docs_commit.txt`); the questions span January to September 2026.",
          "- People post on a forum after the docs failed them, so forum questions overstate the gap compared with a "
          "normal support queue.",
          "- Themes were assigned by hand from the fix summaries (`data/docs_gap_themes.json`); `audit/docsgap.py` checks "
          "that every needs-a-human question appears exactly once.", ""]
    return "\n".join(L)


def main():
    qs, T, table, problems = build()
    if problems:
        raise SystemExit("theme map problems:\n" + "\n".join(problems))
    (ROOT / "DOCS-GAP.md").write_text(markdown(qs, T, table))
    out = {"table": {c: {"label": lab, **{s: table[c][s] for _, s in SETS}, "all": sum(table[c].values())} for c, lab in CATS},
           "groups": T["groups"], "themes": T["themes"], "general": T["general"],
           "community": {"checked": sum(q.get("community_has_fix") is not None for q in qs.values()),
                         "had_fix": sum(bool(q.get("community_has_fix")) for q in qs.values())}}
    (ROOT / "site/data/docsgap.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print("DOCS-GAP.md written;", {c: out["table"][c]["all"] for c, _ in CATS}, out["community"])


if __name__ == "__main__":
    main()
