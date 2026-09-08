\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{mm-cumcm}[2026/09/02 CUMCM electronic paper helper]
\LoadClass[UTF8,a4paper,12pt]{ctexart}
\RequirePackage[margin=2.5cm]{geometry}
\RequirePackage{amsmath,amssymb,booktabs,longtable,graphicx,subcaption,float,xcolor,hyperref,listings,fancyhdr}
\RequirePackage[numbers,sort&compress]{natbib}
\RequirePackage{placeins}
% Readability defaults, not additional official contest requirements.
\ctexset{
 section={format=\centering\heiti\zihao{4},beforeskip=1.1ex plus .3ex,afterskip=.8ex plus .2ex},
 subsection={format=\heiti\zihao{-4},beforeskip=1ex plus .2ex,afterskip=.5ex plus .1ex},
 subsubsection={format=\heiti\zihao{-4},beforeskip=.7ex,afterskip=.3ex}}
\newcommand{\mmHeadingSpace}{\par\begingroup
 \dimen@=\pagegoal\advance\dimen@ by -\pagetotal
 \ifdim\dimen@<6\baselineskip\newpage\fi\endgroup}
\AddToHook{cmd/section/before}{\FloatBarrier\mmHeadingSpace}
\setlength{\@fptop}{0pt}
\setlength{\@fpsep}{12pt}
\setlength{\@fpbot}{0pt plus 1fil}
\raggedbottom
\captionsetup{font=small,labelfont=bf,labelsep=quad,skip=6pt}
\captionsetup[table]{position=top}
\setlength{\textfloatsep}{12pt plus 3pt minus 2pt}
\setlength{\floatsep}{10pt plus 2pt minus 2pt}
\setlength{\intextsep}{10pt plus 2pt minus 2pt}
\renewcommand{\lstlistingname}{程序}
\linespread{1.25}\selectfont
\setlength{\parindent}{2em}
\setlength{\parskip}{0pt}
\pagestyle{fancy}
\fancyhf{}
\cfoot{\thepage}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}
\renewcommand{\contentsname}{}
\newcommand{\mmTitle}[1]{\gdef\@mmTitle{#1}}
\newcommand{\mmKeywords}[1]{\gdef\@mmKeywords{#1}}
\newcommand{\@mmTitle}{[待填写题目]}
\newcommand{\@mmKeywords}{[待填写关键词]}
\newcommand{\mmKeywordStyle}[1]{\textbf{#1}}
\newcommand{\makeMMTitle}{\begin{center}\heiti\zihao{3}\@mmTitle\end{center}\vspace{0.4em}}
\newenvironment{mmabstract}{\begin{center}\heiti\zihao{4}摘要\end{center}\vspace{-0.3em}}{\par\vspace{0.7em}\noindent\mmKeywordStyle{关键词：\quad\@mmKeywords}\par}
\newcommand{\mmBodyStart}{\clearpage\label{mm:body-start}}
\newcommand{\mmAppendixStart}{\clearpage\label{mm:appendix-start}\appendix}
\newcommand{\mmSupportFileList}[1]{\section*{支撑材料文件列表}\begin{itemize}#1\end{itemize}}
\newcommand{\mmCodeFile}[2]{\lstinputlisting[caption={#1},basicstyle=\ttfamily\small,breaklines=true,frame=single]{#2}}
