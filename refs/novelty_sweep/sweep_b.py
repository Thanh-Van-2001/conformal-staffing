"""Second novelty sweep (2024-2026 priority): OpenAlex title/abstract search + arXiv API."""
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding="utf-8")
UA = {"User-Agent": "ref-check/0.1 (academic reference verification)"}


def get(u):
    for t in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=60).read()
        except Exception as e:  # noqa: BLE001 - retried, then reported
            err = e
            time.sleep(5 * (t + 1))
    print("ERROR", u, err)
    return None


OA = ["conformal staffing", "conformal prediction nurse staffing", "conformal prediction emergency department",
      "conformal prediction call center", "conformal prediction ambulance", "conformal emergency medical services",
      "conformal prediction capacity planning", "conformal prediction workforce scheduling",
      "conformal risk control decision", "conformal chance constrained", "conformal PID control",
      "conformal prediction queue", "distribution-free staffing", "conformal prediction hospital operations",
      "conformal prediction service level"]
ARX = ['abs:conformal AND abs:staffing', 'abs:conformal AND abs:ambulance', 'abs:conformal AND abs:"emergency medical"',
       'abs:conformal AND abs:"call center"', 'abs:conformal AND abs:"service level"', 'abs:conformal AND abs:nurse',
       'abs:conformal AND abs:"capacity planning"', 'abs:conformal AND abs:queueing']
out = {"openalex": {}, "arxiv": {}}
for q in OA:
    raw = get("https://api.openalex.org/works?filter=title_and_abstract.search:" + urllib.parse.quote(q)
              + ",from_publication_date:2023-01-01&per-page=25&sort=relevance_score:desc")
    if raw is None:
        continue
    res = json.loads(raw)["results"]
    out["openalex"][q] = [dict(year=w["publication_year"], title=w["title"], doi=w.get("doi"),
                               venue=((w.get("primary_location") or {}).get("source") or {}).get("display_name"))
                          for w in res]
    print(f"## OA {q}: {json.loads(raw)['meta']['count']} hits")
    for w in out["openalex"][q][:12]:
        print("  ", w["year"], "|", (w["title"] or "")[:110], "|", (w["venue"] or "")[:35], "|", w["doi"])
    time.sleep(0.5)
ns = {"a": "http://www.w3.org/2005/Atom"}
for q in ARX:
    raw = get("http://export.arxiv.org/api/query?search_query=" + urllib.parse.quote(q)
              + "&max_results=40&sortBy=submittedDate&sortOrder=descending")
    if raw is None:
        continue
    feed = ET.fromstring(raw)
    ents = [dict(id=e.find("a:id", ns).text.split("/")[-1], date=e.find("a:published", ns).text[:10],
                 title=" ".join(e.find("a:title", ns).text.split())) for e in feed.findall("a:entry", ns)]
    out["arxiv"][q] = ents
    print(f"## arXiv {q}: {len(ents)}")
    for e in ents:
        print("  ", e["date"], e["id"], "|", e["title"][:120])
    time.sleep(3)
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
