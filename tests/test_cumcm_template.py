"""Optional real-XeLaTeX checks; set MM_RUN_TEX_TESTS=1 on a TeX-equipped host."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'packages/math-modeling-skills-complete-20260903/skills/mm-paper-structure-writer/assets/cumcm-2026'
FIXTURE=r'''\documentclass{mm-cumcm}
\hypersetup{pdfauthor={},pdftitle={模板回归样张}}
\makeatletter
\mmTitle{中文数模模板回归样张}
\mmKeywords{几何关系；Alpha\typeout{MM-KEYWORD-SERIES:\f@series}}
OVERRIDE
\begin{document}
\makeMMTitle
\begin{mmabstract}
\textbf{针对问题一，}这是排版测试文本，不是数学建模实验或竞赛答案。
用中文、希腊字母与单位检查格式；关键结论选择性强调，不将全文加粗。
\end{mmabstract}
\mmBodyStart
\section{问题分析}
本页检查正文起点、标题层级、符号与三线表。正文首先解释对象，再列关系。
\subsection{坐标与模型}
\[ F=kx,\qquad \theta=\alpha+\beta. \]
\input{symbols.tex}
\begin{figure}[tbp]\centering
\rule{.65\textwidth}{12mm}
\caption{排版占位矩形。仅用于浮动位置测试，不代表模型机制或数值结果。}
\end{figure}
\section{结果与说明}
段落说明图的作用，章节边界不应让图进入无关附录。
\mmAppendixStart
\section{测试附录}
这是附录，不计入正文页数。
\end{document}
'''

@unittest.skipUnless(os.environ.get('MM_RUN_TEX_TESTS')=='1', 'real TeX test is opt-in; not a simulated compile pass')
class CumcmTemplateCompileTests(unittest.TestCase):
    def compile_fixture(self, override):
        engine=shutil.which('xelatex')
        self.assertIsNotNone(engine, 'MM_RUN_TEX_TESTS=1 requires XeLaTeX')
        with tempfile.TemporaryDirectory(prefix='cumcm-template-') as tmp:
            base=Path(tmp)
            shutil.copy2(ASSETS/'mm-cumcm.cls',base/'mm-cumcm.cls')
            symbols=(ASSETS/'sections/04_symbols.tex').read_text(encoding='utf-8')
            symbols=symbols.replace('待填写 & 待填写 & 待填写',r'$x$ & 位移 & m')
            (base/'symbols.tex').write_text(symbols,encoding='utf-8')
            source=FIXTURE.replace('OVERRIDE', r'\renewcommand{\mmKeywordStyle}[1]{#1}' if override else '')
            (base/'main.tex').write_text(source,encoding='utf-8')
            version=subprocess.run([engine,'--version'],capture_output=True,text=True).stdout
            cmd=[engine]+(['--disable-installer'] if 'MiKTeX' in version else [])
            cmd+=['-no-shell-escape','-interaction=nonstopmode','-halt-on-error','main.tex']
            for _ in range(2):
                result=subprocess.run(cmd,cwd=base,capture_output=True,timeout=120)
                self.assertEqual(result.returncode,0,result.stdout.decode('utf-8',errors='replace')[-4000:])
            log=(base/'main.log').read_text(encoding='utf-8',errors='replace')
            aux=(base/'main.aux').read_text(encoding='utf-8',errors='replace')
            self.assertIn('MM-KEYWORD-SERIES:m' if override else 'MM-KEYWORD-SERIES:bx',log)
            self.assertRegex(aux,r'newlabel\{mm:body-start\}\{\{[^}]*\}\{2\}')
            appendix=re.search(r'newlabel\{mm:appendix-start\}\{\{[^}]*\}\{(\d+)\}',aux)
            self.assertIsNotNone(appendix)
            # Float placement may legitimately add one body page across TeX versions.
            self.assertIn(int(appendix.group(1)),[3,4])
            self.assertNotRegex(log,r'Missing character:|Overfull \\[hv]box|undefined on input line')
            self.assertTrue((base/'main.pdf').stat().st_size>1000)
            if os.environ.get('MM_TEX_QA_DIR'):
                target=Path(os.environ['MM_TEX_QA_DIR'])/('override' if override else 'default')
                target.mkdir(parents=True,exist_ok=True)
                for name in ['main.pdf','main.tex','symbols.tex','mm-cumcm.cls','main.log','main.aux']:
                    shutil.copy2(base/name,target/name)

    def test_default_keyword_weight_and_page_boundaries(self): self.compile_fixture(False)
    def test_explicit_user_keyword_override_is_respected(self): self.compile_fixture(True)

if __name__=='__main__': unittest.main()
