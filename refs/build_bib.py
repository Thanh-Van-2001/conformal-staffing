"""Build refs.bib from Crossref BibTeX for DOIs (fails loudly if a DOI does
not resolve) and print each title for a by-eye check; arXiv entries are
checked against the arXiv API. Run: python build_bib.py <out.bib>"""
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "ref-check/0.1 (academic reference verification)"}
DOIS = {
    # staffing and queues
    "jennings1996server": "10.1287/mnsc.42.10.1383",
    "green2001improving": "10.1287/opre.49.4.549.11228",
    "green2007coping": "10.1111/j.1937-5956.2007.tb00164.x",
    "feldman2008staffing": "10.1287/mnsc.1070.0821",
    "halfin1981heavy": "10.1287/opre.29.3.567",
    "gans2003telephone": "10.1287/msom.5.2.79.16071",
    "gurvich2010staffing": "10.1287/mnsc.1100.1173",
    "bassamboo2010capacity": "10.1287/mnsc.1100.1203",
    "steckley2009forecast": "10.1017/S0269964809000187",
    "gans2015parametric": "10.1287/msom.2015.0546",
    "atlason2004call": "10.1023/B:ANOR.0000019095.91642.bb",
    "chan2008optimization": "10.1287/opre.1080.0559",
    # EMS
    "matteson2011forecasting": "10.1214/10-AOAS442",
    "channouf2007application": "10.1007/s10729-006-9006-3",
    "belanger2019recent": "10.1016/j.ejor.2018.02.055",
    "aboueljinane2013review": "10.1016/j.cie.2013.09.017",
    # conformal prediction
    "vovk2022algorithmic": "10.1007/978-3-031-06649-8",
    "lei2018distribution": "10.1080/01621459.2017.1307116",
    "angelopoulos2023gentle": "10.1561/2200000101",
    "barber2023beyond": "10.1214/23-AOS2276",
    # statistics
    "kunsch1989jackknife": "10.1214/aos/1176347265",
    "wilcoxon1945individual": "10.2307/3001968",
    "kleywegt2002saa": "10.1137/S1052623499363220",
}
ARXIV = {
    "gibbs2021adaptive": "2106.00170",
    "angelopoulos2024conformal": "2208.02814",
    "tibshirani2019conformal": "1904.06019",
    "koole2024call": "2402.19209",
}
EXTRA = r"""
@inproceedings{gibbs2021adaptive,
  author = {Gibbs, Isaac and Cand{\`e}s, Emmanuel J.},
  title = {Adaptive conformal inference under distribution shift},
  booktitle = {Advances in Neural Information Processing Systems 34},
  pages = {1660--1672},
  year = {2021},
  note = {arXiv:2106.00170}
}
@inproceedings{angelopoulos2024conformal,
  author = {Angelopoulos, Anastasios N. and Bates, Stephen and Fisch, Adam and Lei, Lihua and Schuster, Tal},
  title = {Conformal risk control},
  booktitle = {The Twelfth International Conference on Learning Representations (ICLR)},
  year = {2024},
  note = {arXiv:2208.02814}
}
@inproceedings{tibshirani2019conformal,
  author = {Tibshirani, Ryan J. and Foygel Barber, Rina and Cand{\`e}s, Emmanuel J. and Ramdas, Aaditya},
  title = {Conformal prediction under covariate shift},
  booktitle = {Advances in Neural Information Processing Systems 32},
  year = {2019},
  note = {arXiv:1904.06019}
}
@misc{koole2024call,
  author = {Koole, Ger and Li, Siqiao and Ding, Sihan},
  title = {Call center data analysis and model validation},
  year = {2024},
  eprint = {2402.19209},
  archivePrefix = {arXiv},
  note = {arXiv preprint arXiv:2402.19209}
}
@article{holm1979simple,
  author = {Holm, Sture},
  title = {A simple sequentially rejective multiple test procedure},
  journal = {Scandinavian Journal of Statistics},
  volume = {6},
  number = {2},
  pages = {65--70},
  year = {1979}
}
@misc{nycems2026,
  author = {{City of New York}},
  title = {{EMS} Incident Dispatch Data},
  howpublished = {NYC Open Data, dataset 76xm-jjuj},
  year = {2026},
  note = {Accessed November 2026}
}
@misc{sffire2026,
  author = {{City and County of San Francisco}},
  title = {Fire Department and Emergency Medical Services Dispatched Calls for Service},
  howpublished = {DataSF, dataset nuek-vuh3},
  year = {2026},
  note = {Accessed November 2026}
}
"""


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode("utf-8")


out = []
for key, doi in DOIS.items():
    bib = get(f"https://api.crossref.org/works/{doi}/transform/application/x-bibtex")
    bib = re.sub(r"^@(\w+)\{[^,]+,", lambda m: "@" + m.group(1) + "{" + key + ",", bib.strip(), count=1)
    bib = re.sub(r"\s*url=\{[^}]*\},", "", bib)
    t = re.search(r"title=\{(.*?)\},", bib)
    print(f"{key:28s} {t.group(1)[:90] if t else '??'}")
    out.append(bib)
    time.sleep(0.5)
ids = ",".join(ARXIV.values())
feed = ET.fromstring(get(f"http://export.arxiv.org/api/query?id_list={ids}&max_results=10"))
ns = {"a": "http://www.w3.org/2005/Atom"}
for e in feed.findall("a:entry", ns):
    print("arXiv", e.find("a:id", ns).text.split("/")[-1], "|", " ".join(e.find("a:title", ns).text.split())[:90],
          "|", ", ".join(a.find("a:name", ns).text for a in e.findall("a:author", ns))[:80])
open(sys.argv[1], "w", encoding="utf-8").write("\n\n".join(out) + "\n" + EXTRA)
print(len(out) + EXTRA.count("\n@"), "entries written")
