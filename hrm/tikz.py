import sys

from .parse import tokenize

def tikz (src, out=None) :
    if out is None :
        out = sys.stdout
    elif isinstance(out, str) :
        out = open(out, "w")
    out.write("\\documentclass{standalone}\n"
              "\\usepackage{hrm}\n"
              "\\begin{document}\n"
              "\\begin{tikzpicture}[yscale=.9]\n")
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
    skip = False
    y = 0
    for num, kind, obj in tokenize(src) :
        if kind == "lbl" :
            out.write(f"% {obj}:\n"
                      f"\\node[lbl] ({obj}) at (0,{y}) {{}};\n")
            y -= 1;
        elif kind == "op" :
            op, *args = obj
            op = op.lower()
            if op == "comment" :
                continue
            elif op in ("jumpz", "jumpn", "jump") :
                out.write(f"% {' '.join(obj)}\n"
                          f"\\node[hrm={color[op]}] (n{-y}) at (0,{y})"
                          f" {{{label[op]}}};\n"
                          f"\\begin{{scope}}[on background layer]\n"
                          f"\\draw (n{-y}.east) edge[jmp=40] ({args[0]}.east);\n"
                          f"\\end{{scope}}\n")
            else :
                out.write(f"% {' '.join(obj)}\n"
                          f"\\node[hrm={color[op]}] at (0,{y}) {{{label[op]}"
                          f" \\texttt{{{' '.join(args)}}}}};\n")
            y -= 1
    out.write("\\end{tikzpicture}\n"
              "\\end{document}")
