#!/usr/bin/env python3
"""Positive/negative regression cases. ALL fixtures are synthetic tests, not evidence."""
import argparse
import copy
import csv
import json
import subprocess
import sys
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--pdf-python", type=Path)
    args = p.parse_args()
    root = args.output_dir.resolve()
    root.mkdir(parents=True, exist_ok=False)
    script = Path(__file__).with_name("render_reference_template.py")
    cases = []
    def run(name, spec, fields, rows, succeeds):
        folder = root / name
        folder.mkdir()
        with (folder / "synthetic_fixture.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(fields)
            writer.writerows(rows)
        spec = copy.deepcopy(spec)
        spec.update(source_csv="synthetic_fixture.csv", figure_id=name, fixture_notice="SYNTHETIC_TEST_ONLY_NOT_EXPERIMENT_EVIDENCE")
        path = folder / "spec.json"
        path.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
        command = [sys.executable, str(script), "--spec", str(path), "--output-dir", str(folder / "render")]
        if args.pdf_python:
            command += ["--pdf-python", str(args.pdf_python)]
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        (folder / "stdout.json").write_text(proc.stdout, encoding="utf-8")
        (folder / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
        okay = (proc.returncode == 0) == succeeds
        if succeeds and proc.returncode == 0:
            manifest = json.loads(proc.stdout)
            okay &= manifest["semantic_claim_validation"] is False
            okay &= manifest["source"]["sha256"] == manifest["source"]["sha256_after"]
            okay &= manifest["spec"]["sha256"] == manifest["spec"]["sha256_after"]
            okay &= manifest["style"]["final_width_mm"] == 160
            okay &= manifest["style"]["effective_min_font_pt"] >= 8
            okay &= len(manifest["outputs"]) == 3
            okay &= bool(manifest["style"]["font_family"])
            okay &= not any("Glyph" in warning and "missing" in warning for warning in manifest["warnings"])
            if spec["template_id"] == "warm-surface-projection":
                okay &= manifest["render_contract"]["chart_type"] == "surface_3d"
            if spec["template_id"] == "teal-coral-inset":
                okay &= manifest["style"]["legend_strategy"] == "top"
            if args.pdf_python:
                okay &= all(value is True for value in manifest["reopen_check"].values())
            retry = subprocess.run([sys.executable, str(script), "--spec", str(path), "--output-dir", str(folder / "render")], capture_output=True, text=True, encoding="utf-8")
            cases.append({"name": name + "_no_overwrite", "passed": retry.returncode != 0 and "immutable" in retry.stderr})
        elif not succeeds:
            okay &= not (folder / "render").exists()
        cases.append({"name": name, "expected_success": succeeds, "exit_code": proc.returncode, "passed": bool(okay), "error": proc.stderr[-800:]})

    heat = dict(template_id="rose-heatmap", row="因素", column="场景", value="响应", row_order=["因素甲", "因素乙", "因素丙"], column_order=["场景一", "场景二", "场景三"], vmin=0, vmax=1, annotate_cells=True, xlabel="场景", ylabel="扰动因素", colorbar_label="归一化响应")
    hrows = [[r,c,(i*3+j+1)/10] for i,r in enumerate(heat["row_order"]) for j,c in enumerate(heat["column_order"])]
    hfields = ["因素", "场景", "响应"]
    run("heatmap", heat,hfields,hrows,True)
    run("heat_missing",heat,hfields,hrows[:-1],False)
    run("heat_duplicate",heat,hfields,hrows+[hrows[0]],False)
    run("heat_clipping",dict(heat,vmax=.5),hfields,hrows,False)
    run("heat_nonfinite",heat,hfields,hrows[:-1]+[["因素丙","场景三","nan"]],False)
    run("heat_order_missing",dict(heat,column_order=["场景一"]),hfields,hrows,False)
    run("heat_font_small",dict(heat,base_font_pt=8),hfields,hrows,False)
    run("heat_reversed_range",dict(heat,vmin=2,vmax=1),hfields,hrows,False)
    run("heat_no_transforms",dict(heat,transformations="normalize"),hfields,hrows,False)
    run("heat_duplicate_header",heat,["因素","场景","响应","响应"],[row+[0] for row in hrows],False)
    surface = dict(template_id="warm-surface-projection", x="参数甲",y="参数乙",z="响应",vmin=0,vmax=10,xlabel="参数甲",ylabel="参数乙",zlabel="响应值",colorbar_label="响应值")
    srows=[[x,y,1+.2*x*x+.15*y] for y in range(6) for x in range(5)]
    sfields=["参数甲","参数乙","响应"]
    run("surface",surface,sfields,srows,True)
    run("surface_missing",surface,sfields,srows[:-1],False)
    run("surface_duplicate",surface,sfields,srows+[srows[0]],False)
    run("surface_projection_above",dict(surface,projection_z=5),sfields,srows,False)
    line = dict(template_id="teal-coral-inset",x="时间",series=[dict(column="方案甲",label="方案甲",lower="下界",upper="上界"),dict(column="方案乙",label="方案乙")],inset_bounds=[4,8,1,4],uncertainty_type="预先计算的上下界",uncertainty_source="synthetic_fixture.csv（测试数据）",xlabel="时间 / 秒",ylabel="响应值")
    lrows=[[x,1+x*.25,1.3+x*.2,.9+x*.25,1.1+x*.25] for x in range(13)]
    lfields=["时间","方案甲","方案乙","下界","上界"]
    run("inset",line,lfields,lrows,True)
    run("inset_reverse",dict(line,inset_bounds=[8,4,1,4]),lfields,lrows,False)
    run("inset_empty",dict(line,inset_bounds=[4,8,8,9]),lfields,lrows,False)
    run("inset_duplicate_x",line,lfields,lrows+[lrows[-1]],False)
    run("inset_reversed_band",line,lfields,[lrows[0][0:3]+[9,1]]+lrows[1:],False)
    run("inset_missing_band_provenance",dict(line,uncertainty_source=""),lfields,lrows,False)
    run("inset_nonfinite",line,lfields,[lrows[0][0:2]+["inf"]+lrows[0][3:]]+lrows[1:],False)
    summary={"fixture_notice":"ALL DATA ARE SYNTHETIC TEST FIXTURES, NOT RESULTS OR EVIDENCE", "passed":sum(c["passed"] for c in cases),"total":len(cases),"cases":cases}
    (root/"TEST_REPORT.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 0 if all(c["passed"] for c in cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
