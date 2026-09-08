"""Behavioral parser fixtures; no paper-specific content or TeX engine required."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from extract_latex_caption import CaptionError, extract_caption, extract_file


def figure(caption="目标说明", label="fig:target", env="figure"):
    return "\\begin{" + env + "}[tbp]\n\\caption{" + caption + "}\n\\label{" + label + "}\n\\end{" + env + "}"


class CaptionTests(unittest.TestCase):
    def test_neighboring_figures_do_not_leak(self):
        source = figure("前图说明", "fig:previous") + "\n正文与公式不属于图注。\n" + figure()
        result = extract_caption(source, "fig:target")
        self.assertEqual(result.caption_latex, "目标说明")
        self.assertEqual(source[slice(*result.figure_span)], figure())

    def test_nested_braces_and_math(self):
        caption = r"区域\textbf{甲与\emph{乙}}满足 $u_{i_{j}}=\{x\}$。"
        self.assertEqual(extract_caption(figure(caption), "fig:target").caption_latex, caption)

    def test_multiline_and_optional_short_caption(self):
        source = "\\begin{figure}\n\\caption\n[短{题]}与[补充]]\n{完整\n图注}\n\\label{fig:target}\n\\end{figure}"
        result = extract_caption(source, "fig:target")
        self.assertEqual(result.short_caption_latex, "短{题]}与[补充]")
        self.assertEqual(result.caption_latex, "完整\n图注")

    def test_comments_between_command_arguments(self):
        source = "\\begin{figure}\n\\caption% 假图注{不应读取}\n[短题]% 注释\n{真实图注}\n\\label% 注释\n{fig:target}\n\\end{figure}"
        result = extract_caption(source, "fig:target")
        self.assertEqual(result.caption_latex, "真实图注")
        self.assertEqual(result.short_caption_latex, "短题")

    def test_comment_line_join(self):
        self.assertEqual(extract_caption(figure("连续% }伪结束\n文字"), "fig:target").caption_latex, "连续文字")

    def test_escaped_percent(self):
        self.assertEqual(extract_caption(figure(r"占比为 50\%"), "fig:target").caption_latex, r"占比为 50\%")

    def test_double_backslash_does_not_escape_comment(self):
        caption = "甲\\\\% }隐藏的右括号\n乙"
        self.assertEqual(extract_caption(figure(caption), "fig:target").caption_latex, "甲\\\\乙")

    def test_commented_fake_figure(self):
        commented = "\n".join("% " + line for line in figure("伪图").splitlines())
        self.assertEqual(extract_caption(commented + "\n" + figure(), "fig:target").caption_latex, "目标说明")

    def test_figure_star(self):
        self.assertEqual(extract_caption(figure(env="figure*"), "fig:target").environment, "figure*")

    def test_caption_inside_center(self):
        source = r"\begin{figure}\begin{center}\caption{居中}\label{fig:target}\end{center}\end{figure}"
        self.assertEqual(extract_caption(source, "fig:target").caption_latex, "居中")

    def test_subfigure_captions_are_not_parent_caption(self):
        source = r"\begin{figure}\begin{subfigure}{.4\textwidth}\caption{子图}\label{fig:child}\end{subfigure}\caption{总图}\label{fig:target}\end{figure}"
        self.assertEqual(extract_caption(source, "fig:target").caption_latex, "总图")
        with self.assertRaises(CaptionError):
            extract_caption(source, "fig:child")

    def test_inline_verbatim_ignored(self):
        source = r"\verb|\label{fig:target}|" + "\n" + figure()
        self.assertEqual(extract_caption(source, "fig:target").caption_latex, "目标说明")

    def test_subfloat_child_label_is_not_parent_label(self):
        source = r"\begin{figure}\subfloat[短题][子图]{内容\label{fig:child}}\caption{总体}\label{fig:target}\end{figure}"
        self.assertEqual(extract_caption(source, "fig:target").caption_latex, "总体")
        with self.assertRaisesRegex(CaptionError, "subfigure"):
            extract_caption(source, "fig:child")

    def test_subcaptionbox_child_label_is_not_parent_label(self):
        source = r"\begin{figure}\subcaptionbox[短题]{子图\label{fig:child}}[.4\textwidth][c]{内容}\caption{总体}\label{fig:target}\end{figure}"
        self.assertEqual(extract_caption(source, "fig:target").caption_latex, "总体")
        with self.assertRaisesRegex(CaptionError, "subfigure"):
            extract_caption(source, "fig:child")

    def test_verbatim_environments_ignored(self):
        for env in ("verbatim", "Verbatim", "lstlisting", "minted", "comment"):
            with self.subTest(env=env):
                source = "\\begin{" + env + "}\n" + figure("假图") + "\n\\end{" + env + "}\n" + figure()
                self.assertEqual(extract_caption(source, "fig:target").caption_latex, "目标说明")

    def test_label_inside_caption(self):
        source = r"\begin{figure}\caption{完整\label{fig:target}说明}\end{figure}"
        self.assertEqual(extract_caption(source, "fig:target").caption_latex, r"完整\label{fig:target}说明")

    def test_duplicate_labels_in_distinct_figures(self):
        with self.assertRaisesRegex(CaptionError, "found 2"):
            extract_caption(figure() + figure(), "fig:target")

    def test_duplicate_labels_in_one_figure(self):
        with self.assertRaisesRegex(CaptionError, "found 2"):
            extract_caption(figure().replace(r"\end{figure}", r"\label{fig:target}\end{figure}"), "fig:target")

    def test_missing_label(self):
        with self.assertRaisesRegex(CaptionError, "found 0"):
            extract_caption(figure(label="fig:else"), "fig:target")

    def test_outside_label_rejected(self):
        with self.assertRaisesRegex(CaptionError, "outside label"):
            extract_caption(r"\label{fig:target}" + figure(label="fig:else"), "fig:target")

    def test_missing_caption(self):
        with self.assertRaisesRegex(CaptionError, "found 0"):
            extract_caption(r"\begin{figure}\label{fig:target}\end{figure}", "fig:target")

    def test_duplicate_captions(self):
        with self.assertRaisesRegex(CaptionError, "found 2"):
            extract_caption(figure().replace(r"\label", r"\caption{又一个}\label"), "fig:target")

    def test_empty_and_starred_captions_rejected(self):
        for source in (figure(""), figure().replace(r"\caption", r"\caption*")):
            with self.subTest(source=source), self.assertRaises(CaptionError):
                extract_caption(source, "fig:target")

    def test_malformed_source_fails_closed(self):
        samples = [r"\begin{figure}\caption{丢失右括号\label{fig:target}\end{figure}",
                   r"\begin{figure}\caption[未关闭{正文}\label{fig:target}\end{figure}",
                   r"\begin{figure}\caption{正文}\label{fig:target}",
                   r"\begin{figure}\caption{正文}\label{fig:target}\end{table}",
                   r"\begin{figure}\begin{figure}\caption{正文}\label{fig:target}\end{figure}\end{figure}"]
        for source in samples:
            with self.subTest(source=source), self.assertRaises(CaptionError):
                extract_caption(source, "fig:target")

    def test_unterminated_verbatim_fails_closed(self):
        for source in (r"\verb|unterminated", r"\begin{verbatim}" + figure()):
            with self.subTest(source=source), self.assertRaises(CaptionError):
                extract_caption(source, "fig:target")

    def test_control_symbol_is_not_a_label_command(self):
        source = r"\\label{fig:target}" + "\n" + figure()
        self.assertEqual(extract_caption(source, "fig:target").caption_latex, "目标说明")

    def test_inactive_conditional_branch_is_not_silently_selected(self):
        source = r"\iffalse" + figure() + r"\fi" + figure(label="fig:visible")
        with self.assertRaisesRegex(CaptionError, "Conditional TeX"):
            extract_caption(source, "fig:target")

    def test_file_hash_bom_crlf_and_line_numbers(self):
        raw = b"\xef\xbb\xbf" + ("前言\r\n" + figure()).encode("utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "正文.tex"
            path.write_bytes(raw)
            result = extract_file(path, "fig:target")
            self.assertEqual(result.source_sha256, hashlib.sha256(raw).hexdigest())
            self.assertEqual((result.figure_line, result.caption_line), (2, 3))

    def test_cli_success_and_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "source.tex"
            path.write_text(figure(), encoding="utf-8")
            script = Path(__file__).with_name("extract_latex_caption.py")
            command = [sys.executable, "-X", "utf8", str(script), str(path), "--label"]
            success = subprocess.run(command + ["fig:target"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertEqual(json.loads(success.stdout)["caption_latex"], "目标说明")
            failure = subprocess.run(command + ["fig:missing"], capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(failure.returncode, 0)
            self.assertEqual(failure.stdout, "")
            self.assertEqual(json.loads(failure.stderr)["status"], "FAILED")


if __name__ == "__main__":
    unittest.main(verbosity=2)
