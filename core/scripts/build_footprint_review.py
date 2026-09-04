#!/usr/bin/env python3
"""Build a local pre-generation review page for frozen footprint labels."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path


VALID_FOOTPRINTS = ("contraction", "comparable", "expansion")
CSV_COLUMNS = (
    "dataset_index",
    "part",
    "edit",
    "source_prompt",
    "target_prompt",
    "footprint_change",
)


def _load_labels(path: Path) -> dict[int, dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(CSV_COLUMNS).issubset(reader.fieldnames):
            raise ValueError(f"label CSV must contain columns: {list(CSV_COLUMNS)}")
        rows = list(reader)
    labels = {int(row["dataset_index"]): row for row in rows}
    if len(labels) != len(rows):
        raise ValueError("label CSV contains duplicate dataset_index values")
    return labels


def _load_review_records(
    *,
    repo_root: Path,
    manifest_path: Path,
    labels_path: Path,
    output_path: Path,
) -> list[dict[str, str | int]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(manifest) != 60:
        raise ValueError(f"footprint review requires exactly 60 cases, found {len(manifest)}")
    by_index = {int(record["dataset_index"]): record for record in manifest}
    expected = set(range(60))
    if set(by_index) != expected:
        raise ValueError("manifest must contain dataset indices 0 through 59 exactly once")

    labels = _load_labels(labels_path)
    if set(labels) != expected:
        raise ValueError("label CSV must contain dataset indices 0 through 59 exactly once")

    records: list[dict[str, str | int]] = []
    for index in range(60):
        source = by_index[index]
        label = labels[index]
        for field in ("part", "edit", "source_prompt", "target_prompt"):
            if str(label[field]).strip() != str(source[field]).strip():
                raise ValueError(f"label CSV does not match manifest at index {index}: {field}")
        footprint = label["footprint_change"].strip()
        if footprint not in VALID_FOOTPRINTS:
            raise ValueError(f"invalid footprint_change at index {index}: {footprint}")

        source_image = Path(str(source["source_image"]))
        if not source_image.is_absolute():
            source_image = repo_root / source_image
        if not source_image.is_file():
            raise FileNotFoundError(source_image)
        browser_image = Path(
            os.path.relpath(source_image, output_path.parent)
        ).as_posix()
        records.append(
            {
                "case_uid": str(source["case_uid"]),
                "dataset_index": index,
                "part": str(source["part"]),
                "edit": str(source["edit"]),
                "part_size": str(source["part_size"]),
                "source_prompt": str(source["source_prompt"]),
                "target_prompt": str(source["target_prompt"]),
                "source_image": browser_image,
                "footprint_change": footprint,
            }
        )
    return records


def _render_html(records: list[dict[str, str | int]]) -> str:
    payload = json.dumps(records, ensure_ascii=True).replace("<", "\\u003c")
    columns = json.dumps(CSV_COLUMNS)
    footprints = json.dumps(VALID_FOOTPRINTS)
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Footprint label review</title>
  <style>
    :root { color-scheme:light; --ink:#182126; --muted:#647178; --line:#d4dbde; --paper:#f2f4f3; --surface:#fff; --active:#176b58; --active-soft:#dcece7; --warning:#9a5a13; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--paper); color:var(--ink); font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; letter-spacing:0; }
    button { font:inherit; letter-spacing:0; }
    header { position:sticky; top:0; z-index:20; display:flex; align-items:center; justify-content:space-between; gap:16px; min-height:68px; padding:12px 22px; border-bottom:1px solid var(--line); background:rgba(255,255,255,.96); }
    h1 { margin:0; font-size:18px; }
    .subtle,.progress,.counter { color:var(--muted); font-size:12px; }
    .header-actions,.tabs,.nav,.export-actions { display:flex; align-items:center; gap:8px; }
    .button,.choice { min-height:38px; padding:0 13px; border:1px solid #aeb9bd; border-radius:5px; background:#fff; color:var(--ink); cursor:pointer; font-weight:700; }
    .button:hover,.choice:hover { border-color:#708087; }
    .button.active,.choice.selected { border-color:var(--active); background:var(--active-soft); color:#0d5848; }
    .button.primary { border-color:var(--active); background:var(--active); color:#fff; }
    .button:disabled { cursor:not-allowed; opacity:.4; }
    input[type=file] { position:absolute; width:1px; height:1px; opacity:0; pointer-events:none; }
    main { min-height:calc(100vh - 136px); padding:20px 22px; }
    #reviewView { display:grid; grid-template-columns:minmax(320px,1.05fr) minmax(340px,.95fr); gap:22px; max-width:1280px; margin:0 auto; }
    .image-panel,.detail-panel { min-width:0; }
    .image-frame { width:100%; aspect-ratio:1/1; overflow:hidden; border:1px solid var(--line); background:#e5e9e8; }
    .image-frame img { display:block; width:100%; height:100%; object-fit:contain; }
    .case-head { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; padding-bottom:14px; border-bottom:1px solid var(--line); }
    .case-id { margin:0 0 8px; font:700 17px ui-monospace,SFMono-Regular,Menlo,monospace; }
    .tags { display:flex; flex-wrap:wrap; gap:6px; }
    .tag { padding:3px 7px; border:1px solid #bcc6ca; border-radius:4px; background:#fff; font-size:12px; }
    .prompt-block { padding:18px 0; border-bottom:1px solid var(--line); }
    .prompt-label { display:block; margin-bottom:5px; color:var(--muted); font-size:11px; font-weight:800; text-transform:uppercase; }
    .prompt { margin:0 0 16px; line-height:1.5; }
    .prompt:last-child { margin-bottom:0; }
    .decision { padding:18px 0; }
    .decision h2 { margin:0 0 6px; font-size:16px; }
    .decision p { margin:0 0 13px; color:var(--muted); font-size:13px; line-height:1.45; }
    .choices { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }
    .choice { min-height:48px; padding:7px; }
    .choice.confirmed { box-shadow:inset 0 -3px 0 var(--active); }
    .review-state { margin-top:12px; color:var(--warning); font-size:12px; font-weight:700; }
    .review-state.done { color:var(--active); }
    #overviewView[hidden],#reviewView[hidden] { display:none; }
    .overview-head { display:flex; justify-content:space-between; gap:16px; margin:0 auto 16px; max-width:1480px; }
    .overview-head h2 { margin:0; font-size:17px; }
    .overview-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:10px; max-width:1480px; margin:0 auto; }
    .overview-item { padding:0; overflow:hidden; border:1px solid var(--line); border-radius:6px; background:#fff; text-align:left; cursor:pointer; }
    .overview-item.reviewed { border-color:#7ea99d; }
    .overview-item img { display:block; width:100%; aspect-ratio:1/1; object-fit:cover; background:#e5e9e8; }
    .overview-copy { display:block; padding:9px; }
    .overview-title { display:block; overflow:hidden; font:700 12px ui-monospace,SFMono-Regular,Menlo,monospace; text-overflow:ellipsis; white-space:nowrap; }
    .overview-meta { display:block; overflow:hidden; margin-top:4px; color:var(--muted); font-size:11px; text-overflow:ellipsis; white-space:nowrap; }
    .overview-label { display:block; margin-top:7px; color:var(--warning); font-size:11px; font-weight:800; }
    .overview-item.reviewed .overview-label { color:var(--active); }
    footer { position:sticky; bottom:0; z-index:20; display:flex; align-items:center; justify-content:space-between; gap:12px; min-height:68px; padding:12px 22px; border-top:1px solid var(--line); background:rgba(255,255,255,.96); }
    @media(max-width:820px) { header,footer{align-items:stretch;flex-direction:column;padding:10px 14px}main{padding:14px}#reviewView{grid-template-columns:1fr}.choices{grid-template-columns:1fr}.header-actions,.export-actions,.nav{display:grid;grid-template-columns:repeat(2,1fr)}.overview-grid{grid-template-columns:repeat(2,minmax(0,1fr))} }
  </style>
</head>
<body>
  <header>
    <div><h1>Footprint label review</h1><div class="subtle">Review prompts and source images only. Outputs and references are intentionally excluded.</div></div>
    <div class="header-actions"><div class="progress" id="progress"></div><div class="tabs"><button class="button active" id="reviewTab" type="button">Review</button><button class="button" id="overviewTab" type="button">Overview</button></div></div>
  </header>
  <main>
    <section id="reviewView">
      <div class="image-panel"><div class="image-frame"><img id="sourceImage" alt="Source image"></div></div>
      <div class="detail-panel">
        <div class="case-head"><div><div class="case-id" id="caseUid"></div><div class="tags"><span class="tag" id="indexTag"></span><span class="tag" id="sizeTag"></span><span class="tag" id="editTag"></span></div></div><div class="counter" id="counter"></div></div>
        <div class="prompt-block"><span class="prompt-label">Source prompt</span><p class="prompt" id="sourcePrompt"></p><span class="prompt-label">Target prompt</span><p class="prompt" id="targetPrompt"></p></div>
        <div class="decision"><h2>Expected edit footprint</h2><p>Select the expected spatial support relative to the visible source part. Selecting the proposed value still counts as an explicit review.</p><div class="choices" id="choices"></div><div class="review-state" id="reviewState"></div></div>
      </div>
    </section>
    <section id="overviewView" hidden><div class="overview-head"><div><h2>Review all 60 cases</h2><div class="subtle">Select any item to return to its detailed review.</div></div></div><div class="overview-grid" id="overviewGrid"></div></section>
  </main>
  <footer>
    <div class="nav"><button class="button" id="previous" type="button">Previous</button><button class="button" id="next" type="button">Next</button><button class="button" id="nextUnreviewed" type="button">Next unreviewed</button></div>
    <div class="export-actions"><label class="button" for="importFile" style="display:flex;align-items:center">Import CSV</label><input id="importFile" type="file" accept=".csv,text/csv"><button class="button" id="copy" type="button">Copy CSV</button><button class="button primary" id="download" type="button" disabled>Download CSV</button></div>
  </footer>
  <script>
    const records=__RECORDS__, csvColumns=__COLUMNS__, footprintValues=__FOOTPRINTS__;
    const storageKey="partedit-synth60-footprint-review-v1";
    const state=Object.fromEntries(records.map((record)=>[record.case_uid,{label:record.footprint_change,reviewed:false}]));
    let currentIndex=0,currentView="review";
    function restore(){try{const saved=JSON.parse(localStorage.getItem(storageKey)||"{}");records.forEach((record)=>{const item=saved[record.case_uid];if(item&&footprintValues.includes(item.label)){state[record.case_uid]={label:item.label,reviewed:Boolean(item.reviewed)};}});}catch(error){console.warn("Could not restore footprint review",error);}}
    function save(){localStorage.setItem(storageKey,JSON.stringify(state));renderProgress();}
    function reviewedCount(){return records.filter((record)=>state[record.case_uid].reviewed).length;}
    function renderProgress(){const count=reviewedCount();document.getElementById("progress").textContent=`${count} / ${records.length} reviewed`;document.getElementById("download").disabled=count!==records.length;}
    function selectLabel(value){const record=records[currentIndex];state[record.case_uid]={label:value,reviewed:true};save();renderReview();}
    function renderReview(){const record=records[currentIndex],item=state[record.case_uid];document.getElementById("sourceImage").src=record.source_image;document.getElementById("caseUid").textContent=record.case_uid;document.getElementById("indexTag").textContent=`dataset ${record.dataset_index}`;document.getElementById("sizeTag").textContent=`${record.part_size} part`;document.getElementById("editTag").textContent=`${record.part} -> ${record.edit}`;document.getElementById("counter").textContent=`${currentIndex+1} / ${records.length}`;document.getElementById("sourcePrompt").textContent=record.source_prompt;document.getElementById("targetPrompt").textContent=record.target_prompt;
      const choices=document.getElementById("choices");choices.replaceChildren();footprintValues.forEach((value,index)=>{const button=document.createElement("button");button.type="button";button.className="choice";button.textContent=`${index+1}. ${value}`;button.classList.toggle("selected",item.label===value);button.classList.toggle("confirmed",item.reviewed&&item.label===value);button.addEventListener("click",()=>selectLabel(value));choices.appendChild(button);});const status=document.getElementById("reviewState");status.textContent=item.reviewed?`Reviewed: ${item.label}`:`Proposed: ${item.label} (not yet reviewed)`;status.classList.toggle("done",item.reviewed);document.getElementById("previous").disabled=currentIndex===0;document.getElementById("next").disabled=currentIndex===records.length-1;renderProgress();}
    function renderOverview(){const grid=document.getElementById("overviewGrid");grid.replaceChildren();records.forEach((record,index)=>{const item=state[record.case_uid],button=document.createElement("button");button.type="button";button.className="overview-item";button.classList.toggle("reviewed",item.reviewed);const image=document.createElement("img");image.src=record.source_image;image.alt="";image.loading="lazy";const copy=document.createElement("span");copy.className="overview-copy";const title=document.createElement("span");title.className="overview-title";title.textContent=record.case_uid;const meta=document.createElement("span");meta.className="overview-meta";meta.textContent=`${record.part} -> ${record.edit}`;const label=document.createElement("span");label.className="overview-label";label.textContent=`${item.reviewed?"Reviewed":"Proposed"}: ${item.label}`;copy.append(title,meta,label);button.append(image,copy);button.addEventListener("click",()=>{currentIndex=index;setView("review");});grid.appendChild(button);});renderProgress();}
    function setView(view){currentView=view;document.getElementById("reviewView").hidden=view!=="review";document.getElementById("overviewView").hidden=view!=="overview";document.getElementById("reviewTab").classList.toggle("active",view==="review");document.getElementById("overviewTab").classList.toggle("active",view==="overview");if(view==="review")renderReview();else renderOverview();}
    function move(delta){currentIndex=Math.max(0,Math.min(records.length-1,currentIndex+delta));renderReview();}
    function nextUnreviewed(){const offset=records.findIndex((record,index)=>index>currentIndex&&!state[record.case_uid].reviewed);const wrapped=records.findIndex((record)=>!state[record.case_uid].reviewed);const next=offset>=0?offset:wrapped;if(next>=0){currentIndex=next;setView("review");}}
    function csvCell(value){const text=String(value??"");return `"${text.replaceAll('"','""')}"`;}
    function buildCsv(){const header=csvColumns.map(csvCell).join(",");const rows=records.map((record)=>csvColumns.map((column)=>csvCell(column==="footprint_change"?state[record.case_uid].label:record[column])).join(","));return [header,...rows].join("\\r\\n")+"\\r\\n";}
    function parseCsv(text){const rows=[];let row=[],cell="",quoted=false;for(let i=0;i<text.length;i++){const char=text[i];if(quoted){if(char==='"'&&text[i+1]==='"'){cell+='"';i++;}else if(char==='"'){quoted=false;}else cell+=char;}else if(char==='"')quoted=true;else if(char===','){row.push(cell);cell="";}else if(char==='\\n'){row.push(cell.replace(/\\r$/, ""));rows.push(row);row=[];cell="";}else cell+=char;}if(cell||row.length){row.push(cell);rows.push(row);}const header=rows.shift()||[];return rows.filter((values)=>values.some(Boolean)).map((values)=>Object.fromEntries(header.map((key,index)=>[key,values[index]??""])));}
    function importCsv(file){const reader=new FileReader();reader.onload=()=>{const imported=parseCsv(String(reader.result)),byIndex=new Map(imported.map((row)=>[String(row.dataset_index),row]));let matched=0;records.forEach((record)=>{const row=byIndex.get(String(record.dataset_index));if(!row||!footprintValues.includes(row.footprint_change))return;state[record.case_uid]={label:row.footprint_change,reviewed:true};matched++;});if(matched!==records.length){window.alert(`Imported ${matched} valid rows; expected ${records.length}.`);return;}save();setView(currentView);};reader.readAsText(file);}
    function downloadCsv(){if(reviewedCount()!==records.length)return;const blob=new Blob(["\ufeff",buildCsv()],{type:"text/csv;charset=utf-8"}),url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download="synth_60_footprint_labels_reviewed.csv";document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    async function copyCsv(){try{await navigator.clipboard.writeText(buildCsv());}catch(error){window.prompt("Copy the CSV below:",buildCsv());}}
    document.getElementById("reviewTab").addEventListener("click",()=>setView("review"));document.getElementById("overviewTab").addEventListener("click",()=>setView("overview"));document.getElementById("previous").addEventListener("click",()=>move(-1));document.getElementById("next").addEventListener("click",()=>move(1));document.getElementById("nextUnreviewed").addEventListener("click",nextUnreviewed);document.getElementById("download").addEventListener("click",downloadCsv);document.getElementById("copy").addEventListener("click",copyCsv);document.getElementById("importFile").addEventListener("change",(event)=>{const file=event.target.files[0];if(file)importCsv(file);event.target.value="";});document.addEventListener("keydown",(event)=>{if(currentView!=="review")return;if(event.key==="ArrowLeft")move(-1);if(event.key==="ArrowRight")move(1);if(["1","2","3"].includes(event.key))selectLabel(footprintValues[Number(event.key)-1]);});restore();setView("review");
  </script>
</body>
</html>
""".replace("__RECORDS__", payload).replace("__COLUMNS__", columns).replace(
        "__FOOTPRINTS__", footprints
    )


def build_footprint_review_page(
    *,
    repo_root: Path,
    manifest_path: Path,
    labels_path: Path,
    output_path: Path,
) -> list[dict[str, str | int]]:
    records = _load_review_records(
        repo_root=repo_root,
        manifest_path=manifest_path,
        labels_path=labels_path,
        output_path=output_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_render_html(records), encoding="utf-8")
    return records


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    repo_root = Path(__file__).resolve().parents[2]
    parser.add_argument("--repo-root", type=Path, default=repo_root)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("core/data/partedit_subset/synth_60_frozen_manifest.json"),
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=Path("core/data/partedit_subset/synth_60_footprint_labels.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "core/results/heldout_control_comparison/footprint_label_review.html"
        ),
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    output = _resolve(repo_root, args.output)
    records = build_footprint_review_page(
        repo_root=repo_root,
        manifest_path=_resolve(repo_root, args.manifest),
        labels_path=_resolve(repo_root, args.labels),
        output_path=output,
    )
    print(f"saved: {output}")
    print(f"review items: {len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
