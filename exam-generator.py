#!/usr/bin/env python

import sys
import yaml 
import random
import subprocess
import argparse

log_lines = []

def read_yaml(fname):
    with open(fname, 'r') as f:
        content = yaml.safe_load(f.read())
        return content

def make_test_question(question, answers, max_answers, infomap, debug=False):
    ca = answers['correct']
    wa = answers['wrong']
    if debug:
        wa_final = wa
    else:
        num_wa = max_answers - len(ca)
        wa_final = random.sample(wa, num_wa)
    catex = list(map(lambda s: "    \CorrectChoice{" + s + "}", ca))
    watex = list(map(lambda s: f"    \\choice {s}", wa_final))
    ncorr = len(ca)
    if ncorr in infomap:
        current = infomap[ncorr]
    else:
        current = 0
    infomap[ncorr] = current + 1
    fatex = catex + watex
    if not debug:
        random.shuffle(fatex)
    tex = [
        "\\filbreak",
        f"  \question {question}",
        "  \\begin{checkboxes}"
    ]
    tex += fatex
    tex.append("  \\end{checkboxes}")
    tex.append("\\vspace{0.5cm}")
    return tex

def make_open_question(openq, debug=False):
    question = openq['question']
    answer = openq['answer']
    tex = [
        "\\filbreak",
        f"  \question {question}",
        "\\vspace{0.2cm}",
    ]
    if debug:
        tex.append(
        "    \\noindent\\fbox{\parbox{\\textwidth}{\\textbf{Possible Expected Answer:}\\\\" + answer + "}}"
        )
    else:
        tex.append(
        "   \makeemptybox{10cm}"
        )
    return tex

def make_questions(yaml, max_answers, debug=False):
    tex = ["\\begin{questions}"]
    full_questions = []
    open_questions = []
    infomap = {}
    open = 0
    for fullq in filter(lambda q: 'full-question' in q and 'skip' not in q, yaml['questions']):
          full_questions.append(make_test_question(fullq['question'], fullq['answers'], max_answers, infomap, debug=debug))
    for openq in filter(lambda q: 'open-question' in q and 'skip' not in q, yaml['questions']):
          open_questions.append(make_open_question(openq, debug=debug))
          open += 1
    if not debug:
        random.shuffle(full_questions)
        random.shuffle(open_questions)
    for question in full_questions:
        tex += question
    tex += ["\\newpage"]
    for question in  open_questions:
        tex += question
    tex += ["\end{questions}"]
    global log_lines 
    log_lines += ["--- Question Distribution"]
    for k, v in infomap.items():
        log_lines += [f"# of Questions with {k} correct answers: {v}"]
    log_lines += [f"Open Questions: {open}"]
    return tex

def make_descr(yaml):
    tex = ["\subsection*{Instructions}", "\\begin{itemize}"]
    tex += map(lambda s: "\item{" + s + "}", yaml)
    tex += ["\\end{itemize}"]
    return tex

def make_exam(yaml, version, max_answers=4, debug=False):
    title = yaml['title']
    institution = yaml['institution']
    course = yaml['course']
    edition = yaml['edition']
    descr = yaml['description']
    date = yaml['date']
    hash_parts = yaml['hash'].split(',')
    hash_version = hash_parts[0] + str(version) + hash_parts[1]
    tex = [ 
        "\\usepackage{tcolorbox}",
        "\\usepackage{listings}",
        "\\usepackage{tikz}",
        "\lstset{basicstyle=\\ttfamily,breaklines=true}",
        "\lstset{framextopmargin=50pt,frame=bottomline}",
        "\\renewcommand\labelitemi{-}",
        "\pagestyle{headandfoot}",
        "\\runningheadrule",
        "\\runningheader{" + course + "}{}{" + edition + "}",
        "\\firstpagefootrule",
        "\\firstpagefooter{" + date + "}{" + institution + "}{\\thepage\,/\,\\numpages}",
        "\\runningfootrule",
        "\\runningfooter{" + date + "}{" + hash_version + "}{\\thepage\,/\,\\numpages}",
        "\\usepackage{etoolbox}",
        "\BeforeBeginEnvironment{checkboxes}{\\vspace*{0.25cm}\par\\nopagebreak\minipage{\linewidth}}",
        "\AfterEndEnvironment{checkboxes}{\\vspace*{0.25cm}\endminipage}"
        "\\begin{document}",
        "\\begin{tcolorbox}[width=\\textwidth]",
        "\section*{\centering " + title + "}",
        "\end{tcolorbox}",
        "\\vspace{0.1in}",
        "\\thispagestyle{empty}",
        "\\begin{tikzpicture}[remember picture, overlay]",
        "\\node[below left] (coin)  at (16,4)",
        "{\\begin{tabular}{l p{7cm}}",
        "Name \& Student ID: & \\hrule \\\\",
        "\end{tabular}",
        "};"
        "\end{tikzpicture}",
        "\\vspace{0.5cm}",
          ]   
    tex += make_descr(descr)
    tex += ["\\vspace{1cm}", "\par\\noindent\\rule{\\textwidth}{0.4pt}"]
    tex += make_questions(yaml, max_answers, debug=debug)
    tex += [ "\end{document}" ]
    questions_tex = [ "\documentclass[addpoints,11pt]{exam}" ] + tex
    answers_tex = [ "\documentclass[answers,addpoints,11pt]{exam}" ] + tex
    return (questions_tex, answers_tex)


def print_tex(tex, outfile):
    with open(outfile, "w") as o:
        for line in tex:
            o.write(f"{line}\n")


def compile_file(tex_files):
    for tex_file in tex_files:
        subprocess.run([latex_cmd, tex_file])
        subprocess.run([latex_cmd, tex_file])

parser = argparse.ArgumentParser(description='Create exam and answers from a template.')
parser.add_argument('input', type=str, help='the input YAML file')
parser.add_argument('prefix', type=str, help='prefix for the output files')
parser.add_argument('--versions', type=int, default=1,
                    help='number of versions to produce')
parser.add_argument('--debug', action='store_true',
                    help='print all answers for each question')
args = parser.parse_args(sys.argv[1:])
content = read_yaml(args.input)
latex_cmd = "/Library/TeX/texbin/pdflatex" 

if args.debug:
    debug_file = f"{args.prefix}-debug.tex"
    (questions, answers) = make_exam(content['exam'], version=0, debug=True)
    print_tex(answers, debug_file)
    compile_file([debug_file])
else:
    for version in range(0, args.versions):
        (questions, answers) = make_exam(content['exam'], version=version, debug=False)
        questions_file = f"{args.prefix}-questions-v{version}.tex"
        answers_file = f"{args.prefix}-answers-v{version}.tex"
        print_tex(questions, questions_file)
        print_tex(answers, answers_file)
        compile_file([questions_file, answers_file])

for line in log_lines:
    print(line)

