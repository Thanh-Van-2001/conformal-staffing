"""Word version of the manuscript for Prehospital Emergency Care.

Expands the \\res macros, takes the non-anonymous branch, removes figures
(uploaded separately; captions are listed at the end, as the journal asks),
moves tables after the caption list, and converts with pandoc + citeproc
(NLM/Vancouver numbered citations).
Run from the repository root: python -I code/make_docx.py
"""
import json
import os
import re
import subprocess

M = json.load(open("out/macros.json"))
tex = open("paper/main.tex", encoding="utf-8").read()

# body only
body = tex[tex.index("\\begin{document}") + len("\\begin{document}"):tex.index("\\end{document}")]
body = body.replace("\\maketitle", "").replace("\\linenumbers", "")


def take_else(s):
    """\\ifdefined\\ANON A \\else B \\fi -> B ; \\ifdefined\\ANON\\else B \\fi -> B"""
    out, i = [], 0
    while True:
        j = s.find("\\ifdefined\\ANON", i)
        if j < 0:
            out.append(s[i:])
            return "".join(out)
        out.append(s[i:j])
        k = s.index("\\fi", j)
        block = s[j + len("\\ifdefined\\ANON"):k]
        out.append(block.split("\\else", 1)[1] if "\\else" in block else "")
        i = k + len("\\fi")


body = take_else(body)
body = re.sub(r"\\res\{([^}]+)\}", lambda m: M[m.group(1)], body)
body = body.replace("\\repolink", "\\url{https://github.com/Thanh-Van-2001/conformal-staffing}")
body = body.replace("\\bibliographystyle{unsrtnat}", "").replace("\\bibliography{refs}", "")

# figures: drop, keep captions
fig_caps = []
for m in re.finditer(r"\\begin\{figure\}.*?\\end\{figure\}", body, flags=re.S):
    cap = re.search(r"\\caption\{(.*)\}\s*\\label", m.group(0), flags=re.S).group(1)
    fig_caps.append(cap)
body = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", "", body, flags=re.S)
# tables: move to the end, keep captions for the list
tables, tab_caps = [], []
for m in re.finditer(r"\\begin\{table\}.*?\\end\{table\}", body, flags=re.S):
    t = m.group(0)
    cap = re.search(r"\\caption\{(.*?)\}\s*\\label", t, flags=re.S).group(1)
    tab_caps.append(cap)
    t = re.sub(r"\\caption\{.*?\}\s*\\label\{[^}]*\}", "", t, flags=re.S)
    t = re.sub(r"\\begin\{table\}\[[^]]*\]|\\end\{table\}|\\centering|\\small|\\setlength\{[^}]*\}\{[^}]*\}", "", t)
    tables.append(t)
body = re.sub(r"\\begin\{table\}.*?\\end\{table\}", "", body, flags=re.S)
body = body.replace("Figure~\\ref{fig:cc}", "Figure 1").replace("Figure~\\ref{fig:drift}", "Figure 2")
body = body.replace("Table~\\ref{tab:data}", "Table 1").replace("Tables~\\ref{tab:res} and~\\ref{tab:cost}", "Tables 2 and 3")
body = body.replace("equation~\\eqref{eq:guarantee}", "equation (1)").replace("\\label{eq:guarantee}", "")
assert "\\ref{" not in body, re.findall(r".{40}\\ref\{.{20}", body)

# abstract environment -> section
body = body.replace("\\begin{abstract}", "\\section*{Abstract}").replace("\\end{abstract}", "")

title = re.search(r"\\title\{(.*?)\}\n", tex).group(1)
words = len(re.sub(r"\\[a-zA-Z]+|[{}$]", " ", body[body.index("\\section{Introduction}"):body.index("\\section*{Acknowledgements}")]).split())
front = (f"\\section*{{{title}}}\n\nThanh Van Nguyen\n\nTsinghua Shenzhen International Graduate School, Tsinghua University, "
         f"Shenzhen, China\n\nCorresponding author: Thanh Van Nguyen, felicenguyen2001@gmail.com\n\n"
         f"Word count (main text, approximate): {words}\n\n\\newpage\n")
os.makedirs("paper/docx", exist_ok=True)
with open("paper/docx/body.tex", "w", encoding="utf-8") as f:
    f.write(front + body)
md = subprocess.run(["pandoc", "paper/docx/body.tex", "-f", "latex", "-t", "markdown"], capture_output=True,
                    text=True, encoding="utf-8", check=True).stdout
caps = ["# Table Captions & Figure Captions", ""]
for i, c in enumerate(tab_caps, 1):
    caps.append(f"**Table {i}.** " + subprocess.run(["pandoc", "-f", "latex", "-t", "markdown"], input=c, capture_output=True,
                                                     text=True, encoding="utf-8", check=True).stdout.strip())
    caps.append("")
for i, c in enumerate(fig_caps, 1):
    caps.append(f"**Figure {i}.** " + subprocess.run(["pandoc", "-f", "latex", "-t", "markdown"], input=c, capture_output=True,
                                                      text=True, encoding="utf-8", check=True).stdout.strip())
    caps.append("")
tabs = []
for i, t in enumerate(tables, 1):
    tm = subprocess.run(["pandoc", "-f", "latex", "-t", "markdown"], input=t, capture_output=True, text=True,
                        encoding="utf-8", check=True).stdout
    tabs += [f"**Table {i}.**", "", tm, ""]
md = md + "\n\n# References\n\n::: {#refs}\n:::\n\n" + "\n".join(caps) + "\n\n# Tables\n\n" + "\n".join(tabs)
with open("paper/docx/manuscript.md", "w", encoding="utf-8") as f:
    f.write(md)
subprocess.run(["pandoc", "paper/docx/manuscript.md", "-o", "paper/docx/manuscript.docx", "--citeproc",
                "--bibliography", "paper/refs.bib", "--csl", "refs/csl/nlm-pandoc212.csl"], check=True)
print("docx written;", words, "words in main text;", len(tab_caps), "tables;", len(fig_caps), "figures")
