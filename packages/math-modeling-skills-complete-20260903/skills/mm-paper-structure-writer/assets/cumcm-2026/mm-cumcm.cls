\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{mm-cumcm}[2026/09/02 CUMCM electronic paper helper]
\LoadClass[UTF8,a4paper,12pt]{ctexart}
\RequirePackage[margin=2.5cm]{geometry}
\RequirePackage{amsmath,amssymb,booktabs,longtable,graphicx,subcaption,float,xcolor,hyperref,listings,fancyhdr}
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
\newcommand{\makeMMTitle}{\begin{center}\zihao{3}\bfseries \@mmTitle\end{center}\vspace{0.8em}}
\newenvironment{mmabstract}{\par\noindent\textbf{摘要}\quad}{\par\vspace{0.7em}\noindent\textbf{关键词}\quad\@mmKeywords\par}
\newcommand{\mmBodyStart}{\clearpage\label{mm:body-start}}
\newcommand{\mmAppendixStart}{\clearpage\label{mm:appendix-start}\appendix}
\newcommand{\mmSupportFileList}[1]{\section*{支撑材料文件列表}\begin{itemize}#1\end{itemize}}
\newcommand{\mmCodeFile}[2]{\lstinputlisting[caption={#1},basicstyle=\ttfamily\small,breaklines=true,frame=single]{#2}}
