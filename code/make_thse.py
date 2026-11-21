"""Submission package for IISE Transactions on Healthcare Systems Engineering (THSE).

THSE reviews double-anonymously and takes a LaTeX manuscript as a compiled PDF
plus a single flat zip of its sources. This script builds
paper/submission/package_thse/ from

  paper/main_thse.tex   anonymous manuscript (T&F order, endfloat, APA-like refs)
  paper/supp_thse.tex   Supplementary Table S1 (anonymous)
  paper/submission/thse_title_page_template.md, thse_cover_letter_template.md
  code/make_checklist.py (STRESS-DES rows, anonymous variant)

No number is typed here: results come from out/macros.json (the same values
as paper/macros.tex); word and page counts are computed from the sources and
the built PDF. The PEC package (paper/submission/package) is not touched.

Steps: APA-like .bst derived from TinyTeX's apalike.bst; build the manuscript
in a flat temporary directory; count words; rebuild; zip the flat sources and
prove the zip compiles on its own in a fresh directory; supplement, figures
(vector PDF and 600 dpi TIFF), checklist, title page, cover letter, plain
abstract and keywords; anonymity and defect checks. Exits non-zero on any
failed check.

Run from the repository root (not with -I: PyMuPDF lives in the user site-packages):
  C:/ProgramData/anaconda3/python.exe code/make_thse.py
"""
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import fitz
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_checklist  # noqa: E402

PAPER = "paper"
PKG = os.path.join(PAPER, "submission", "package_thse")
JOB = "manuscript_anonymous"
M = json.load(open("out/macros.json", encoding="utf-8"))
FIGS = [("fig_coverage_cost.pdf", "Figure1"), ("fig_drift.pdf", "Figure2")]
SOURCES = ["macros.tex", "thse_counts.tex", "refs.bib", "thseapa.bst"] + [f for f, _ in FIGS]
# strings that would identify the author; none may appear in anonymous files
FORBIDDEN = [r"nguyen", r"thanh", r"tsinghua", r"gmail", r"github", r"felice", r"shenzhen", r"\bsigs\b",
             r"holy_grail", r"users[\\/]+admin", r"titan"]
FAIL = []


def check(ok, msg):
    print(("ok    " if ok else "FAIL  ") + msg)
    if not ok:
        FAIL.append(msg)


def read(p):
    return io.open(p, encoding="utf-8").read().replace("\r\n", "\n")


def run(cmd, cwd, inp=None):
    return subprocess.run(cmd, cwd=cwd, input=inp, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


# ---------------------------------------------------------------- bibliography style
def write_bst():
    """apalike.bst plus DOIs, '&' before the last author, 'vol(no), pages' and 'pp.'.
    apalike's licence allows modified copies only under a new name: thseapa.bst."""
    src = run(["kpsewhich", "apalike.bst"], ".").stdout.strip()
    b = io.open(src, encoding="latin-1").read().replace("\r\n", "\n")

    def sub(pat, rep, s, regex=False):
        n = len(re.findall(pat, s)) if regex else s.count(pat)
        assert n == 1, (pat, n)
        return re.sub(pat, lambda _: rep, s) if regex else s.replace(pat, rep)

    b = sub("    chapter\n", "    chapter\n    doi\n", b)
    b = sub("FUNCTION {fin.entry}\n{ add.period$\n  write$",
            "FUNCTION {fin.entry}\n{ add.period$\n  doi empty$\n    'skip$\n"
            "    { \" \\url{https://doi.org/\" * doi * \"}\" * }\n  if$\n  write$", b)
    # APA puts a comma before '&' even for two authors: drop apalike's 'more than two' test
    b = sub(r"\{ numnames #2 >\s*\{ \",\" \* \}\s*'skip\$\s*if\$", '{ "," *', b, regex=True)
    b = sub(r'\{ " et~al\." \* \}(\s*)\{ " and " \* t \* \}', '{ " et~al." * }\n                { " \\& " * t * }',
            b, regex=True)
    b = sub('{ " and " * s #2 "{vv~}{ll}" format.name$ * }', '{ " \\& " * s #2 "{vv~}{ll}" format.name$ * }', b)
    b = sub("FUNCTION {format.vol.num.pages}\n{ volume field.or.null",
            "FUNCTION {format.vol.num.pages}\n{ volume empty$ { \"\" } { \"{\\em \" volume * \"\\/}\" * } if$", b)
    b = sub('{ ":" * pages n.dashify * }', '{ ", " * pages n.dashify * }', b)
    b = sub('"pages" pages n.dashify tie.or.space.connect', '"pp." pages n.dashify tie.or.space.connect', b)
    b = sub('"page" pages tie.or.space.connect', '"p." pages tie.or.space.connect', b)
    head = ("% thseapa.bst -- written by code/make_thse.py from apalike.bst (Oren Patashnik), renamed as its\n"
            "% licence requires. Changes for an APA-like (Taylor & Francis APA) reference list: DOIs as\n"
            "% https://doi.org/ links, '&' before the last author, italic volume, 'vol(no), pages', 'pp.'.\n")
    io.open(os.path.join(PAPER, "thseapa.bst"), "w", encoding="latin-1", newline="\n").write(head + b)


# ---------------------------------------------------------------- word counts
def cite_labels(bbl):
    lab = {}
    for m in re.finditer(r"\\bibitem\[(.*?)\]\{([^}]*)\}", bbl, flags=re.S):
        lab[m.group(2)] = re.sub(r"[{}]", "", m.group(1)).replace("~", " ")
    return lab


def expand(s, labels):
    s = re.sub(r"(?<!\\)%[^\n]*", "", s)
    s = re.sub(r"\\res\{([^}]+)\}", lambda m: M[m.group(1)], s)
    s = re.sub(r"\\cite(?:p|alp)\{([^}]*)\}",
               lambda m: "(" + "; ".join(labels.get(k.strip(), k) for k in m.group(1).split(",")) + ")", s)
    return s


def words(s):
    s = re.sub(r"\\[a-zA-Z]+\*?|[{}$~]", " ", s)
    return [w for w in s.split() if re.search(r"[A-Za-z0-9]", w)]


def drop_floats(s):
    return re.sub(r"\\begin\{(table|figure)\}.*?\\end\{\1\}", " ", s, flags=re.S)


def counts(tex, bbl):
    lab = cite_labels(bbl)
    abs_tex = tex[tex.index("% ABSTRACT-BEGIN"):tex.index("% ABSTRACT-END")]
    main = tex[tex.index("\\section{Introduction}"):tex.index("\\section*{Acknowledgments}")]
    back = tex[tex.index("\\section*{Abstract}"):tex.index("\\end{document}")]
    bbl_body = re.sub(r"\\bibitem\[.*?\]\{[^}]*\}", " ", bbl, flags=re.S)
    bbl_body = re.sub(r"\\url\{[^}]*\}|\\newblock|\\begin\{thebibliography\}\{[^}]*\}|\\end\{thebibliography\}", " ",
                      bbl_body)
    return {"wcAbs": len(words(expand(abs_tex, lab))),
            "wcMain": len(words(drop_floats(expand(main, lab)))),
            "wcTotal": len(words(expand(back, lab))) + len(words(bbl_body))}


def fmt(n):
    return f"{n:,}"


def write_counts(c):
    io.open(os.path.join(PAPER, "thse_counts.tex"), "w", encoding="utf-8", newline="\n").write(
        "% generated by code/make_thse.py -- do not edit\n"
        f"\\newcommand{{\\wcMain}}{{{fmt(c['wcMain'])}}}\n\\newcommand{{\\wcAbs}}{{{fmt(c['wcAbs'])}}}\n")


# ---------------------------------------------------------------- LaTeX builds
def latex(d, job, bibtex=True):
    """pdflatex (+ bibtex) to a fixed point; returns the log text."""
    r = run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", job], d)
    assert r.returncode == 0, io.open(os.path.join(d, job + ".log"), encoding="latin-1").read()[-3000:]
    if bibtex:
        b = run(["bibtex", job], d)
        assert b.returncode in (0, 1), b.stdout[-2000:]
        for w in re.findall(r"Warning--[^\n]*", b.stdout):
            print("      bibtex:", w)
    for _ in range(3):
        r = run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", job], d)
        log = io.open(os.path.join(d, job + ".log"), encoding="latin-1").read()
        if "Rerun to get" not in log and "Label(s) may have changed" not in log:
            break
    assert r.returncode == 0 and os.path.exists(os.path.join(d, job + ".pdf")), log[-3000:]
    return log


def log_checks(log, name):
    warn = re.findall(r"(?:LaTeX|Package \w+) Warning: [^\n]*", log)
    undef = [w for w in warn if "undefined" in w] + (["undefined references"] if "There were undefined" in log else [])
    check(not undef, f"{name}: no undefined citations or references" + (f" -> {undef[:5]}" if undef else ""))
    check("multiply defined" not in log, f"{name}: no multiply defined labels")
    over = re.findall(r"Overfull \\hbox \((\d+\.\d+)pt too wide\)", log)
    check(not over, f"{name}: no overfull boxes" + (f" (found {over})" if over else ""))
    und = re.findall(r"Undefined control sequence", log)
    check(not und, f"{name}: no undefined control sequences")


def pdf_text(p):
    doc = fitz.open(p)
    return doc, "\n".join(pg.get_text() for pg in doc)


def stage(d):
    shutil.copy2(os.path.join(PAPER, "main_thse.tex"), os.path.join(d, JOB + ".tex"))
    for f in SOURCES:
        shutil.copy2(os.path.join(PAPER, f), os.path.join(d, f))


# ---------------------------------------------------------------- anonymity
def forbidden_in(text):
    return [p for p in FORBIDDEN if re.search(p, text, flags=re.I)]


def anon_pdf(p):
    doc, text = pdf_text(p)
    meta = json.dumps(doc.metadata) + (doc.get_xml_metadata() or "")
    raw = open(p, "rb").read().decode("latin-1")
    hits = forbidden_in(text) + forbidden_in(meta) + forbidden_in(raw)
    check(not hits, f"anonymous: {os.path.basename(p)} text, metadata and raw bytes" + (f" -> {hits}" if hits else ""))


def anon_zip(p, label):
    with zipfile.ZipFile(p) as z:
        hits = {n: forbidden_in(z.read(n).decode("latin-1")) for n in z.namelist()}
    hits = {k: v for k, v in hits.items() if v}
    check(not hits, f"anonymous: {label}" + (f" -> {hits}" if hits else ""))


# ---------------------------------------------------------------- pandoc helpers
def pandoc(src_text, fmt_from, out, extra=()):
    r = subprocess.run(["pandoc", "-f", fmt_from, "-o", out, *extra], input=src_text, capture_output=True,
                       text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr


def to_plain(tex):
    r = subprocess.run(["pandoc", "-f", "latex", "-t", "plain", "--wrap=none"], input=tex, capture_output=True,
                       text=True, encoding="utf-8", check=True)
    return re.sub(r"\n{3,}", "\n\n", r.stdout).strip() + "\n"


def fill(t, cnt):
    t = re.sub(r"\\res\{([^}]+)\}", lambda m: M[m.group(1)], t)
    t = re.sub(r"\\cnt\{([^}]+)\}", lambda m: cnt[m.group(1)], t)
    assert "\\res{" not in t and "\\cnt{" not in t
    return t


def main():
    os.makedirs(PKG, exist_ok=True)
    write_bst()
    tex = read(os.path.join(PAPER, "main_thse.tex"))

    # ---- manuscript: build, count, rebuild
    work = tempfile.mkdtemp(prefix="thse_build_")
    write_counts({"wcMain": 0, "wcAbs": 0})
    stage(work)
    latex(work, JOB)
    bbl = read(os.path.join(work, JOB + ".bbl"))
    c = counts(tex, bbl)
    write_counts(c)
    stage(work)
    log = latex(work, JOB)
    shutil.copy2(os.path.join(work, JOB + ".bbl"), os.path.join(PAPER, "main_thse.bbl"))
    pdf = os.path.join(PKG, JOB + ".pdf")
    shutil.copy2(os.path.join(work, JOB + ".pdf"), pdf)
    doc, text = pdf_text(pdf)
    pages = doc.page_count
    doc.close()
    print(f"manuscript: {pages} pages; main text {c['wcMain']} words; abstract {c['wcAbs']}; total ~{c['wcTotal']}")
    log_checks(log, "manuscript")
    check("??" not in text, "manuscript: no '??' (missing macro or reference) in the PDF text")
    check(c["wcAbs"] <= 200, f"abstract {c['wcAbs']} <= 200 words")
    check(pages <= 30, f"manuscript {pages} pages <= 30 (typical length)")
    check("\\footnote" not in tex, "manuscript: no footnotes")
    check(fmt(c["wcMain"]) in text.replace("\n", " "), "manuscript: printed word count matches the computed one")
    n_tables = len(re.findall(r"\\begin\{table\}", tex))
    n_figs = len(re.findall(r"\\begin\{figure\}", tex))

    # ---- flat LaTeX source zip, proved in a fresh directory
    zpath = os.path.join(PKG, "latex_source.zip")
    members = [JOB + ".tex", JOB + ".bbl"] + SOURCES
    readme = ("Anonymous manuscript for double-anonymous review.\n"
              f"Main file: {JOB}.tex. Compile with pdflatex (run bibtex once with thseapa.bst if the\n"
              f"bibliography is to be regenerated; {JOB}.bbl is included). All files are in one flat\n"
              "directory: figures are vector PDFs, numbers are in macros.tex and thse_counts.tex.\n")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in members:
            z.write(os.path.join(work, f), f)
        z.writestr("README.txt", readme)
    with zipfile.ZipFile(zpath) as z:
        names = z.namelist()
    check(all("/" not in n and "\\" not in n for n in names), f"zip is flat ({len(names)} files)")
    for mode in ("bbl only", "with bibtex"):
        fresh = tempfile.mkdtemp(prefix="thse_zip_")
        with zipfile.ZipFile(zpath) as z:
            z.extractall(fresh)
        if mode == "with bibtex":
            os.remove(os.path.join(fresh, JOB + ".bbl"))
        zlog = latex(fresh, JOB, bibtex=(mode == "with bibtex"))
        zdoc, ztext = pdf_text(os.path.join(fresh, JOB + ".pdf"))
        check(zdoc.page_count == pages and ztext == text, f"zip compiles standalone ({mode}): same {pages} pages, same text")
        zdoc.close()
        log_checks(zlog, f"zip build ({mode})")
        shutil.rmtree(fresh, ignore_errors=True)

    # ---- supplementary table S1 (single source: the table body must equal the one in main.tex)
    supp = read(os.path.join(PAPER, "supp_thse.tex"))
    body = supp[supp.index("\\begin{tabular}"):supp.index("\\end{tabular}")]
    check(body in read(os.path.join(PAPER, "main.tex")), "Supplementary Table S1 rows identical to main.tex")
    sd = tempfile.mkdtemp(prefix="thse_supp_")
    shutil.copy2(os.path.join(PAPER, "supp_thse.tex"), os.path.join(sd, "Supplementary_Table_S1.tex"))
    shutil.copy2(os.path.join(PAPER, "macros.tex"), sd)
    slog = latex(sd, "Supplementary_Table_S1", bibtex=False)
    log_checks(slog, "supplement")
    shutil.copy2(os.path.join(sd, "Supplementary_Table_S1.pdf"), PKG)
    _, stext = pdf_text(os.path.join(PKG, "Supplementary_Table_S1.pdf"))
    check("??" not in stext, "supplement: no '??'")

    # ---- figures: vector PDF as made by make_figures.py, and 600 dpi TIFF rendered from it
    for src, name in FIGS:
        shutil.copy2(os.path.join(PAPER, src), os.path.join(PKG, name + ".pdf"))
        fd = fitz.open(os.path.join(PAPER, src))
        pix = fd[0].get_pixmap(dpi=600, alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        img.save(os.path.join(PKG, name + ".tif"), compression="tiff_lzw", dpi=(600, 600))
        fonts = sorted({f[2] for f in fd[0].get_fonts()})
        print(f"{name}: {pix.width}x{pix.height} px at 600 dpi; PDF font types {fonts}")
        fd.close()

    # ---- STRESS-DES checklist, anonymous
    n = make_checklist.build(os.path.join(PKG, "STRESS_DES_checklist.docx"), make_checklist.thse_rows(), anonymous=True)
    print("checklist:", n, "items")

    # ---- plain abstract and keywords for the portal
    abs_tex = tex[tex.index("% ABSTRACT-BEGIN") + len("% ABSTRACT-BEGIN"):tex.index("% ABSTRACT-END")]
    abs_tex = re.sub(r"\\res\{([^}]+)\}", lambda m: M[m.group(1)], abs_tex).replace("\\noindent", "")
    abs_tex = re.sub(r"\$\\rho=([^$]*)\$", lambda m: "ρ = " + m.group(1).replace("-", "−"), abs_tex)
    abs_tex = re.sub(r"\$([0-9.,−-]+)\$", r"\1", abs_tex)
    plain = to_plain(abs_tex)
    io.open(os.path.join(PKG, "abstract_plain.txt"), "w", encoding="utf-8", newline="\n").write(plain)
    check(len(plain.split()) <= 200, f"plain abstract {len(plain.split())} <= 200 words")
    kw_tex = tex[tex.index("% KEYWORDS-BEGIN") + len("% KEYWORDS-BEGIN"):tex.index("% KEYWORDS-END")]
    kws = [k.strip() for k in kw_tex.split(";") if k.strip()]
    io.open(os.path.join(PKG, "keywords.txt"), "w", encoding="utf-8", newline="\n").write("\n".join(kws) + "\n")
    check(len(kws) <= 10, f"{len(kws)} keywords <= 10")

    # ---- title page (docx and pdf) and cover letter (docx)
    ai = tex[tex.index("\\section*{Declaration of generative AI use}") + len("\\section*{Declaration of generative AI use}"):
             tex.index("\\section*{Data availability statement}")].strip()
    assert "\\" not in ai, ai
    cnt = {"wcMain": fmt(c["wcMain"]), "wcAbs": fmt(c["wcAbs"]), "wcTotal": fmt(round(c["wcTotal"], -2)),
           "pages": str(pages), "nTables": str(n_tables), "nFigures": str(n_figs), "keywords": "; ".join(kws),
           "aiDeclaration": ai}
    tp = fill(read(os.path.join(PAPER, "submission", "thse_title_page_template.md")), cnt)
    pandoc(tp, "markdown", os.path.join(PKG, "title_page.docx"))
    pandoc(tp, "markdown", os.path.join(PKG, "title_page.pdf"), ["--pdf-engine=pdflatex"])
    today = datetime.date.today()
    cl = fill(read(os.path.join(PAPER, "submission", "thse_cover_letter_template.md")),
              {"date": f"{today:%B} {today.day}, {today.year}"})
    pandoc(cl, "markdown", os.path.join(PKG, "cover_letter.docx"))
    print("cover letter:", len(cl.split()), "words")

    # ---- anonymity of everything the reviewers see
    for f in (JOB + ".pdf", "Supplementary_Table_S1.pdf", "Figure1.pdf", "Figure2.pdf"):
        anon_pdf(os.path.join(PKG, f))
    anon_zip(zpath, "latex_source.zip (every member)")
    anon_zip(os.path.join(PKG, "STRESS_DES_checklist.docx"), "STRESS_DES_checklist.docx (every XML part)")
    for f in ("abstract_plain.txt", "keywords.txt"):
        check(not forbidden_in(read(os.path.join(PKG, f))), f"anonymous: {f}")
    check(not forbidden_in(tex), "anonymous: main_thse.tex source")
    # the identified files must carry the author (they go to the editor only)
    with zipfile.ZipFile(os.path.join(PKG, "title_page.docx")) as z:
        check("Thanh Van Nguyen" in z.read("word/document.xml").decode("utf-8"), "title page names the author")

    json.dump({"pages": pages, **c, "tables": n_tables, "figures": n_figs, "keywords": kws,
               "plain_abstract_words": len(plain.split()), "zip_members": names},
              io.open(os.path.join(PKG, "build_info.json"), "w", encoding="utf-8"), indent=1)
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(sd, ignore_errors=True)
    print("\n".join(sorted(os.listdir(PKG))))
    if FAIL:
        print(f"\n{len(FAIL)} check(s) failed")
        return 1
    print("\nall checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
