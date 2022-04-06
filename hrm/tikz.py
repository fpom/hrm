import sys, pathlib, subprocess, tempfile

from .parse import tokenize

color = {"inbox" : "green",
         "outbox" : "green",
         "copyfrom" : "red",
         "copyto" : "red",
         "add" : "orange",
         "sub" : "orange",
         "bumpup" : "orange",
         "bumpdn" : "orange",
         "jump" : "blue",
         "jumpz" : "blue",
         "jumpn" : "blue"}
label = {"inbox" : "\\raisebox{-.2ex}{\\ding{231}}\\texttt{inbox}",
         "outbox" : "\\texttt{outbox}\,\\raisebox{-.2ex}{\\ding{231}}",
         "copyfrom" : "\\texttt{copyfrom}",
         "copyto" : "\\texttt{copyto}",
         "add" : "\\texttt{add}",
         "sub" : "\\texttt{sub}",
         "bumpup" : "\\texttt{bump+}",
         "bumpdn" : "\\texttt{bump-}",
         "jump" : "\\texttt{jump}",
         "jumpz" : "\\texttt{jump}${}^{\\texttt{\\relsize{-1}if}}_{\\texttt{\\relsize{-1}zero}}$",
         "jumpn" : "\\texttt{jump}${}^{\\texttt{\\relsize{-1}if}}_{\\texttt{\\relsize{-1}negative}}$"}

def tikz (src, out=sys.stdout, headers=False) :
    if isinstance(out, str) :
        out = open(out, "w")
    if headers :
        out.write("\\documentclass{standalone}\n"
                  "\\usepackage{tikz}\n"
                  "\\usetikzlibrary{backgrounds,calc}\n"
                  "\\usepackage{relsize}\n"
                  "\\usepackage{pifont}\n"
                  "\\tikzstyle{hrm}=[anchor=west,minimum height=7mm,thick,draw=#1!60!black,fill=#1!20!white,rounded corners]\n"
                  "\\tikzstyle{lbl}=[hrm=blue,minimum width=15mm]\n"
                  "\\tikzstyle{jmp}=[->,line width=3pt,line cap=round,draw=blue!40!white]\n"
                  "\\begin{document}\n")
    out.write("\\begin{tikzpicture}[yscale=.9]\n")
    skip = False
    y = 0
    jumps = []
    labels = set()
    for num, kind, obj in tokenize(src) :
        if kind == "lbl" :
            out.write(f"% {obj}:\n"
                      f"\\node[lbl] ({obj}) at (0,{y}) {{}};\n")
            labels.add(obj)
        elif kind == "op" :
            op, *args = obj
            op = op.lower()
            if op == "comment" :
                continue
            elif op in ("jumpz", "jumpn", "jump") :
                out.write(f"% {' '.join(obj)}\n"
                          f"\\node[hrm={color[op]}] (n{-y}) at (0,{y})"
                          f" {{{label[op]}}};\n")
                if args[0] in labels :
                    jumps.append((f"n{-y}.east", f"{args[0]}.east", 40))
                else :
                    jumps.append((f"n{-y}.east", f"{args[0]}.east", -40))
            else :
                out.write(f"% {' '.join(obj)}\n"
                          f"\\node[hrm={color[op]}] at (0,{y}) {{{label[op]}"
                          f" \\texttt{{{' '.join(args)}}}}};\n")
        y -= 1
    out.write(f"\\begin{{scope}}[on background layer]\n"
              f"% jumps\n")
    for src, dst, angle in jumps :
        out.write(f"\\draw[jmp] ({src})"
                  f" .. controls ($({src})+(1,0)$) and ($({src})!.1!({dst})+(1.5,0)$) .."
                  f" ($({src})!.5!({dst})+(1.5,0)$)"
                  f" .. controls ($({dst})!.1!({src})+(1.5,0)$) and ($({dst})+(1,0)$) .."
                  f" ({dst});\n")
    out.write(f"\\end{{scope}}\n"
              "\\end{tikzpicture}\n"
              "\\end{document}")

def draw (src, out) :
    with tempfile.TemporaryDirectory() as tmp :
        tex = pathlib.Path(tmp) / "hrm.tex"
        pdf = tex.with_suffix(".pdf")
        tikz(src, tex.open("w"), True)
        subprocess.check_output(["pdflatex", "-interaction=batchmode", tex.name],
                                cwd=tex.parent)
        pdf.rename(out)
