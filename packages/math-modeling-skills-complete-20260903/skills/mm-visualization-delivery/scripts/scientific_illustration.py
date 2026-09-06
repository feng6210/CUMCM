"""Prepare native tool requests and collect real native raster outputs.

This helper never generates pixels and never treats capability discovery as a
successful generation. Invocation remains with the host's actual image tool.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

def checked_ref(record, root):
    if not isinstance(record, dict) or not record.get("file"):
        raise ValueError("hash-bound source required")
    path = Path(record["file"])
    path = path if path.is_absolute() else root / path
    if not path.is_file() or sha(path) != record.get("sha256"):
        raise ValueError(f"missing/stale source: {path}")
    return path.resolve()

def validate_brief(brief, root):
    for key in ("figure_id", "purpose", "caption_zh", "nodes", "style", "source_files"):
        if not brief.get(key):
            raise ValueError(f"brief.{key} required")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", brief["figure_id"]):
        raise ValueError("unsafe figure_id")
    if brief.get("narrative_role", "mechanism") not in {"orientation", "mechanism"}:
        raise ValueError("native generation is not a quantitative evidence backend")
    if brief.get("exact_geometry_required"):
        raise ValueError("exact geometry requires a deterministic backend")
    ids = [n["id"] for n in brief["nodes"]]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate node id")
    for n in brief["nodes"]:
        if not re.search(r"[\u3400-\u9fff]", n.get("label_zh", "")):
            raise ValueError("node requires a Chinese label")
    for edge in brief.get("edges", []):
        if edge.get("from") not in ids or edge.get("to") not in ids:
            raise ValueError("edge references unknown node")
    if not brief["style"].get("palette") or not brief["style"].get("composition"):
        raise ValueError("style requires palette and composition")
    for ref in brief["source_files"]:
        checked_ref(ref, root)

def choose_backend(preference, names):
    # Names must come from actual host discovery, never from PATH probing.
    names = [str(x) for x in names]
    native = next((x for x in names if x in {"image_gen__imagegen", "image_gen.imagegen"}), None)
    bridge = [x for x in names if "codex" in x and "image2" in x]
    sync = next((x for x in bridge if x.endswith("__generate")), None)
    start = next((x for x in bridge if x.endswith("__generate_start")), None)
    status = next((x for x in bridge if x.endswith("__generate_status")), None)
    if preference not in {"auto", "image2", "imagegen"}:
        raise ValueError("unknown backend preference")
    if preference in {"auto", "imagegen"} and native:
        return "imagegen", [native]
    if preference in {"auto", "image2"} and (sync or (start and status)):
        return "image2", [sync] if sync else [start, status]
    raise ValueError(f"BLOCKED_BACKEND: {preference}; requested native tool not callable")

def prepare(brief_path, tools_path, out):
    brief = load(brief_path)
    validate_brief(brief, brief_path.parent)
    actual, names = choose_backend(brief.get("backend_preference", "auto"), load(tools_path)["names"])
    out.mkdir(parents=True, exist_ok=False)
    prompt = (
        "绘制中文 CUMCM 科研方法示意图，不是数值结果图。\n"
        f"用途：{brief['purpose']}\n"
        f"构图：{brief['style']['composition']}\n"
        f"配色：{', '.join(brief['style']['palette'])}。鲜明精致、清晰留白；允许轻渐变和层次。\n"
        "节点标签逐字使用：" + json.dumps(brief["nodes"], ensure_ascii=False) + "\n"
        "仅允许以下关系：" + json.dumps(brief.get("edges", []), ensure_ascii=False) + "\n"
        "分支与停止条件：" + json.dumps({k:brief.get(k, []) for k in ("branches", "stop_conditions")}, ensure_ascii=False) + "\n"
        "不增加节点、关系、数据曲线、结果数字或性能声明。中文清晰，箭头方向准确，反馈与主链可区分。"
        "按约160毫米论文插图宽度设计足够大的文字，不放作者、学校、logo或图内论文标题。"
    )
    (out/"prompt.txt").write_text(prompt, encoding="utf-8")
    dump(out/"request.json", {"status":"READY_TO_CALL_NOT_GENERATED", "actual_backend":actual,
         "tool_names":names, "brief_sha256":sha(brief_path), "prompt_sha256":sha(out/"prompt.txt"),
         "source_files":brief["source_files"],
         "capabilities_sha256":sha(tools_path), "recorded_model":None})
    return load(out/"request.json")

def finalize(brief_path, image_path, receipt_path, out):
    from PIL import Image
    brief = load(brief_path)
    validate_brief(brief, brief_path.parent)
    receipt = load(receipt_path)
    request_path = checked_ref(receipt.get("request"), receipt_path.parent)
    request = load(request_path)
    if request.get("brief_sha256") != sha(brief_path):
        raise ValueError("request bound to a different/stale brief")
    if request.get("source_files") != brief["source_files"]:
        raise ValueError("request source bindings differ from brief")
    prompt_path = checked_ref(receipt.get("prompt"), receipt_path.parent)
    if request.get("prompt_sha256") != sha(prompt_path):
        raise ValueError("request prompt hash mismatch")
    backend = receipt.get("actual_backend")
    if backend not in {"image2", "imagegen"}:
        raise ValueError("receipt.actual_backend must be image2/imagegen")
    preference = brief.get("backend_preference", "auto")
    if preference != "auto" and preference != backend:
        raise ValueError("receipt backend differs from explicitly requested backend")
    tool = receipt.get("tool_name", "")
    if backend == "imagegen" and tool not in {"image_gen__imagegen", "image_gen.imagegen"}:
        raise ValueError("actual tool is not the native generator")
    if backend == "image2" and not (("image2" in tool and "codex" in tool) and
                                     tool.endswith(("__generate", "__generate_start"))):
        raise ValueError("actual tool is not the image2 generator")
    if request.get("actual_backend") != backend or tool not in request.get("tool_names", []):
        raise ValueError("receipt tool/backend differs from prepared request")
    if choose_backend(backend, request["tool_names"])[0] != backend:
        raise ValueError("tool name not compatible with backend")
    if receipt.get("status") != "completed" or receipt.get("native_generation") is not True:
        raise ValueError("no successful native generation receipt")
    if sha(image_path) != receipt.get("output_sha256"):
        raise ValueError("receipt output hash mismatch")
    record = checked_ref(receipt.get("tool_record"), receipt_path.parent)
    record_data = load(record)
    if not isinstance(record_data, dict) or record_data.get("tool_name") != tool:
        raise ValueError("tool record must identify the actual invoked tool")
    if record_data.get("request_sha256") != sha(request_path) or record_data.get("output_sha256") != sha(image_path):
        raise ValueError("tool record request/output mismatch")
    response = record_data.get("response")
    if not isinstance(response, (dict, list)) or not response:
        raise ValueError("actual tool response must be retained")
    def failed_response(value):
        if isinstance(value, list):
            return any(failed_response(v) for v in value)
        if not isinstance(value, dict):
            return False
        return (bool(value.get("isError") or value.get("error")) or
                str(value.get("status", "")).lower() in {"failed","error","cancelled","canceled","blocked","rejected"} or
                any(failed_response(v) for v in value.values() if isinstance(v,(dict,list))))
    if failed_response(response):
        raise ValueError("failed tool response cannot be finalized")
    with Image.open(image_path) as im:
        if im.format != "PNG":
            raise ValueError("expected real native PNG, not a renamed vector/project file")
        im.load()
        width, height = im.size
    if min(width, height) < 256:
        raise ValueError("native output is too small for a paper figure")
    out.mkdir(parents=True, exist_ok=False)
    shutil.copy2(image_path, out/"figure.png")
    # Canonical sources make this generated brief independent of its original directory.
    final_brief = dict(brief)
    final_brief["source_files"] = [
        {"file": str(checked_ref(r, brief_path.parent)), "sha256":r["sha256"]}
        for r in brief["source_files"]]
    dump(out/"brief.json", final_brief)
    shutil.copy2(record, out/"tool_record.json")
    shutil.copy2(brief_path, out/"generation_brief.json")
    shutil.copy2(request_path, out/"request.json")
    shutil.copy2(prompt_path, out/"prompt.txt")
    final_receipt = dict(receipt)
    final_receipt["tool_record"] = {"file":"tool_record.json", "sha256":sha(out/"tool_record.json")}
    final_receipt["request"] = {"file":"request.json", "sha256":sha(out/"request.json")}
    final_receipt["prompt"] = {"file":"prompt.txt", "sha256":sha(out/"prompt.txt")}
    dump(out/"receipt.json", final_receipt)
    # Escape caption metacharacters without treating source prose as TeX commands.
    escapes = {"\\":r"\textbackslash{}", "&":r"\&", "%":r"\%", "$":r"\$",
               "#":r"\#", "_":r"\_", "{":r"\{", "}":r"\}", "~":r"\textasciitilde{}", "^":r"\textasciicircum{}"}
    caption = "".join(escapes.get(c,c) for c in brief["caption_zh"])
    tex = "\\begin{figure}[htbp]\n\\centering\n\\includegraphics[width=0.95\\linewidth]{\\detokenize{" + (out/"figure.png").resolve().as_posix() + "}}\n\\caption{" + caption + "}\n\\label{fig:" + brief["figure_id"] + "}\n\\end{figure}\n"
    (out/"latex_include.tex").write_text(tex, encoding="utf-8")
    report = {"status":"RUNTIME_VERIFIED", "semantic_claim_validation":False,
        "actual_backend":backend, "editability":"prompt_and_spec_only",
        "recorded_model":receipt.get("recorded_model"), "pixel_size":[width,height],
        "generation_brief_sha256":sha(brief_path),
        "generation_brief":{"file":"generation_brief.json","sha256":sha(out/"generation_brief.json")},
        "effective_dpi_at_160mm":round(width/(160/25.4),1),
        "receipt":{"file":"receipt.json","sha256":sha(out/"receipt.json")},
        "sources":final_brief["source_files"],
        "outputs":[{"path":p.name,"sha256":sha(p)} for p in [out/"brief.json",out/"figure.png"]],
        "style":{"style_profile":"cumcm-vivid"},
        "reopen_check":{"png":True,"brief":True},
        "visual_status":"NOT_EVALUATED",
        "warnings":["Raster image: prompt/spec editing only; separate independent visual review required."]}
    dump(out/"backend_report.json", report)
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    for name in ("prepare","finalize"):
        q=sub.add_parser(name)
        q.add_argument("--brief",type=Path,required=True)
        q.add_argument("--output-dir",type=Path,required=True)
        if name=="prepare":
            q.add_argument("--tools",type=Path,required=True)
        else:
            q.add_argument("--image",type=Path,required=True)
            q.add_argument("--receipt",type=Path,required=True)
    a=p.parse_args()
    try:
        r=prepare(a.brief,a.tools,a.output_dir) if a.command=="prepare" else finalize(a.brief,a.image,a.receipt,a.output_dir)
        print(json.dumps(r,ensure_ascii=False,indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as e:
        print(json.dumps({"status":"FAILED","error":str(e)},ensure_ascii=False))
        return 1
if __name__=="__main__":
    raise SystemExit(main())
