#!/usr/bin/env python3
"""Build a reusable, standalone manual-review page from CSV and JSON."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path


REQUIRED_CONFIG_FIELDS = {
    "title",
    "storage_key",
    "download_filename",
    "id_field",
    "image_fields",
    "score_fields",
    "note_field",
}


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while current != current.parent:
        if (current / "pyproject.toml").is_file():
            return current
        current = current.parent
    raise FileNotFoundError(f"Could not find repository root from {start}")


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED_CONFIG_FIELDS - set(config))
    if missing:
        raise ValueError(f"Review config is missing fields: {missing}")
    if not config["image_fields"] or not config["score_fields"]:
        raise ValueError("Review config requires at least one image and score field")
    return config


def load_records(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Review CSV has no header: {path}")
        return list(reader), list(reader.fieldnames)


def validate_records(records: list[dict[str, str]], id_field: str) -> None:
    if not records:
        raise ValueError("Review CSV contains no records")
    seen = set()
    for index, record in enumerate(records, start=1):
        review_id = record.get(id_field, "").strip()
        if not review_id:
            raise ValueError(f"Missing review id in row {index}: {id_field}")
        if review_id in seen:
            raise ValueError(f"Duplicate review id: {review_id}")
        seen.add(review_id)


def browser_records(
    records: list[dict[str, str]],
    *,
    repo_root: Path,
    output_path: Path,
    image_fields: list[dict],
) -> list[dict[str, str]]:
    output = []
    for record in records:
        browser_record = dict(record)
        for field in image_fields:
            key = field["key"]
            value = record.get(key, "").strip()
            if not value:
                if field.get("optional", False):
                    continue
                raise ValueError(f"Missing required image field {key} for {record}")
            source_path = Path(value)
            if not source_path.is_absolute():
                source_path = repo_root / source_path
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            browser_record[key] = Path(
                os.path.relpath(source_path, output_path.parent)
            ).as_posix()
        output.append(browser_record)
    return output


def render_html(records: list[dict[str, str]], columns: list[str], config: dict) -> str:
    payload = json.dumps(records, ensure_ascii=True).replace("<", "\\u003c")
    columns_json = json.dumps(columns, ensure_ascii=True)
    config_json = json.dumps(config, ensure_ascii=True).replace("<", "\\u003c")
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__TITLE__</title>
  <style>
    :root { color-scheme: light; --ink:#172126; --muted:#617078; --line:#d7dee1; --paper:#f3f5f4; --surface:#fff; --accent:#087f73; --accent-soft:#d9efeb; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--paper); color:var(--ink); font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; letter-spacing:0; }
    button,textarea { font:inherit; letter-spacing:0; }
    header,footer { position:sticky; z-index:10; display:flex; align-items:center; justify-content:space-between; gap:18px; padding:16px 24px; background:var(--surface); border-color:var(--line); }
    header { top:0; border-bottom:1px solid var(--line); }
    footer { bottom:0; border-top:1px solid var(--line); }
    h1 { margin:0; font-size:19px; }
    .progress,.counter,.status { color:var(--muted); font-size:13px; }
    main { padding:20px 24px; }
    .meta { display:flex; justify-content:space-between; gap:16px; margin-bottom:14px; }
    .identity { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
    .uid { font:700 16px ui-monospace,SFMono-Regular,Menlo,monospace; }
    .tag { padding:3px 7px; border:1px solid #b9c7cb; border-radius:4px; background:#fff; font-size:12px; }
    .prompt { margin:7px 0 0; color:#34464d; line-height:1.4; }
    .images { display:grid; grid-template-columns:repeat(var(--image-count),minmax(0,1fr)); gap:10px; margin-bottom:16px; }
    figure { margin:0; min-width:0; }
    figcaption { height:26px; display:flex; align-items:center; color:#42545b; font-size:12px; font-weight:700; }
    .frame { width:100%; aspect-ratio:1/1; border:1px solid var(--line); background:#e6ebeb; overflow:hidden; }
    .frame img { width:100%; height:100%; object-fit:contain; display:block; }
    .review { display:grid; grid-template-columns:repeat(var(--score-count),minmax(180px,1fr)) minmax(260px,1.3fr); gap:12px; padding:15px; background:var(--surface); border:1px solid var(--line); }
    .label { display:block; margin-bottom:8px; font-size:13px; font-weight:750; }
    .hint { margin:7px 0 0; min-height:32px; color:var(--muted); font-size:12px; line-height:1.35; }
    .score-group { display:grid; grid-auto-flow:column; grid-auto-columns:1fr; gap:6px; }
    .score,.command { min-height:40px; border:1px solid #aebcc1; border-radius:5px; background:#fff; color:var(--ink); cursor:pointer; font-weight:700; }
    .score.selected { border-color:var(--accent); background:var(--accent-soft); color:#075f57; }
    textarea { width:100%; min-height:82px; resize:vertical; padding:9px; border:1px solid #aebcc1; border-radius:5px; }
    .actions,.nav { display:flex; gap:8px; align-items:center; }
    .command { padding:0 13px; }
    .command.primary { color:#fff; background:var(--accent); border-color:var(--accent); }
    .command:disabled { opacity:.4; cursor:not-allowed; }
    input[type=file] { position:absolute; width:1px; height:1px; opacity:0; pointer-events:none; }
    @media(max-width:900px) { header,footer,main{padding-left:14px;padding-right:14px}.images{grid-template-columns:repeat(2,minmax(0,1fr))}.review{grid-template-columns:1fr}footer{align-items:stretch;flex-direction:column}.actions,.nav{display:grid;grid-template-columns:repeat(2,1fr)} }
  </style>
</head>
<body>
  <header><h1 id="title"></h1><div class="progress" id="progress"></div></header>
  <main>
    <section class="meta"><div><div class="identity"><span class="uid" id="reviewUid"></span><span class="tag" id="method"></span><span class="tag" id="partSize"></span><span class="tag" id="partEdit"></span></div><p class="prompt" id="prompt"></p></div><div class="counter" id="counter"></div></section>
    <section class="images" id="images"></section>
    <section class="review" id="review"></section>
  </main>
  <footer>
    <div class="nav"><button class="command" id="previous" type="button">Previous</button><button class="command" id="next" type="button">Next</button></div>
    <div class="actions"><span class="status" id="status">Saved in this browser</span><label class="command" for="importFile" style="display:flex;align-items:center">Import CSV</label><input id="importFile" type="file" accept=".csv,text/csv"><button class="command" id="copy" type="button">Copy CSV</button><button class="command primary" id="download" type="button">Download CSV</button></div>
  </footer>
  <script>
    const records=__RECORDS__, csvColumns=__COLUMNS__, config=__CONFIG__;
    let currentIndex=0;
    const idField=config.id_field;
    document.documentElement.style.setProperty("--image-count",String(config.image_fields.length));
    document.documentElement.style.setProperty("--score-count",String(config.score_fields.length));
    document.getElementById("title").textContent=config.title;

    function savedPayload(record){const value={};config.score_fields.forEach((field)=>value[field.key]=record[field.key]??"");value[config.note_field]=record[config.note_field]??"";return value;}
    function restore(){try{const saved=JSON.parse(localStorage.getItem(config.storage_key)||"{}");records.forEach((record)=>{if(saved[record[idField]])Object.assign(record,saved[record[idField]]);});}catch(error){console.warn("Could not restore ratings",error);}}
    function save(){localStorage.setItem(config.storage_key,JSON.stringify(Object.fromEntries(records.map((record)=>[record[idField],savedPayload(record)]))));updateProgress();}
    function isScored(record){return config.score_fields.every((field)=>String(record[field.key]??"")!=="");}
    function updateProgress(){const scored=records.filter(isScored).length;document.getElementById("progress").textContent=`${scored} / ${records.length} items scored`;document.getElementById("status").textContent=scored===records.length?"All items scored":"Saved in this browser";}
    function scoreButtons(field){const group=document.createElement("div");group.className="score-group";field.values.forEach((score)=>{const button=document.createElement("button");button.type="button";button.className="score";button.textContent=String(score);button.classList.toggle("selected",String(records[currentIndex][field.key]??"")===String(score));button.addEventListener("click",()=>{records[currentIndex][field.key]=String(score);save();render();});group.appendChild(button);});return group;}
    function render(){const record=records[currentIndex];document.getElementById("reviewUid").textContent=record.case_uid||record[idField];document.getElementById("method").textContent=record.method||"";document.getElementById("partSize").textContent=record.part_size||"";document.getElementById("partEdit").textContent=[record.part,record.edit].filter(Boolean).join(" -> ");document.getElementById("prompt").textContent=record.target_prompt?`Target: ${record.target_prompt}`:"";document.getElementById("counter").textContent=`Item ${currentIndex+1} of ${records.length}`;
      const images=document.getElementById("images");images.replaceChildren();config.image_fields.forEach((field)=>{if(!record[field.key])return;const figure=document.createElement("figure");const caption=document.createElement("figcaption");caption.textContent=field.label;const frame=document.createElement("div");frame.className="frame";const image=document.createElement("img");image.src=record[field.key];image.alt=field.label;frame.appendChild(image);figure.append(caption,frame);images.appendChild(figure);});
      const review=document.getElementById("review");review.replaceChildren();config.score_fields.forEach((field)=>{const section=document.createElement("div");const label=document.createElement("span");label.className="label";label.textContent=field.label;const hint=document.createElement("p");hint.className="hint";hint.textContent=field.hint||"";section.append(label,scoreButtons(field),hint);review.appendChild(section);});const note=document.createElement("label");const noteLabel=document.createElement("span");noteLabel.className="label";noteLabel.textContent=config.note_label||"Short note";const textarea=document.createElement("textarea");textarea.value=record[config.note_field]||"";textarea.placeholder=config.note_placeholder||"Describe edit success and preservation separately.";textarea.addEventListener("input",(event)=>{record[config.note_field]=event.target.value;save();});note.append(noteLabel,textarea);review.appendChild(note);
      document.getElementById("previous").disabled=currentIndex===0;document.getElementById("next").disabled=currentIndex===records.length-1;updateProgress();}
    function csvCell(value){const text=String(value??"");return `"${text.replaceAll('"','""')}"`;}
    function buildCsv(){return [csvColumns.map(csvCell).join(","),...records.map((record)=>csvColumns.map((column)=>csvCell(record[column])).join(","))].join("\\r\\n")+"\\r\\n";}
    function parseCsv(text){const rows=[];let row=[],cell="",quoted=false;for(let i=0;i<text.length;i++){const char=text[i];if(quoted){if(char==='"'&&text[i+1]==='"'){cell+='"';i++;}else if(char==='"'){quoted=false;}else{cell+=char;}}else if(char==='"'){quoted=true;}else if(char===','){row.push(cell);cell="";}else if(char==='\\n'){row.push(cell.replace(/\\r$/, ""));rows.push(row);row=[];cell="";}else{cell+=char;}}if(cell||row.length){row.push(cell);rows.push(row);}const header=rows.shift()||[];return rows.filter((values)=>values.some(Boolean)).map((values)=>Object.fromEntries(header.map((key,index)=>[key,values[index]??""])));}
    function importCsv(file){const reader=new FileReader();reader.onload=()=>{const imported=parseCsv(String(reader.result));const byId=new Map(imported.map((row)=>[row[idField],row]));let matched=0;records.forEach((record)=>{const row=byId.get(record[idField]);if(!row)return;config.score_fields.forEach((field)=>{if(row[field.key]!==undefined)record[field.key]=row[field.key];});if(row[config.note_field]!==undefined)record[config.note_field]=row[config.note_field];matched++;});if(!matched){window.alert(`No rows matched ${idField}.`);return;}save();render();window.alert(`Imported ratings for ${matched} items.`);};reader.readAsText(file);}
    function downloadCsv(){const blob=new Blob(["\ufeff",buildCsv()],{type:"text/csv;charset=utf-8"});const url=URL.createObjectURL(blob);const link=document.createElement("a");link.href=url;link.download=config.download_filename;document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    async function copyCsv(){try{await navigator.clipboard.writeText(buildCsv());}catch(error){window.prompt("Copy the CSV below:",buildCsv());}}
    document.getElementById("previous").addEventListener("click",()=>{currentIndex=Math.max(0,currentIndex-1);render();});document.getElementById("next").addEventListener("click",()=>{currentIndex=Math.min(records.length-1,currentIndex+1);render();});document.getElementById("download").addEventListener("click",downloadCsv);document.getElementById("copy").addEventListener("click",copyCsv);document.getElementById("importFile").addEventListener("change",(event)=>{const file=event.target.files[0];if(file)importCsv(file);event.target.value="";});document.addEventListener("keydown",(event)=>{if(event.target.tagName==="TEXTAREA")return;if(event.key==="ArrowLeft")document.getElementById("previous").click();if(event.key==="ArrowRight")document.getElementById("next").click();});restore();render();
  </script>
</body>
</html>
""".replace("__TITLE__", str(config["title"]).replace("<", "&lt;")) \
        .replace("__RECORDS__", payload) \
        .replace("__COLUMNS__", columns_json) \
        .replace("__CONFIG__", config_json)


def build_review_page(
    *, repo_root: Path, input_path: Path, config_path: Path, output_path: Path
) -> list[dict[str, str]]:
    config = load_config(config_path)
    records, columns = load_records(input_path)
    validate_records(records, config["id_field"])
    required_columns = {
        config["id_field"], config["note_field"],
        *(field["key"] for field in config["image_fields"]),
        *(field["key"] for field in config["score_fields"]),
    }
    missing = sorted(required_columns - set(columns))
    if missing:
        raise ValueError(f"Review CSV is missing columns: {missing}")
    browser_rows = browser_records(
        records,
        repo_root=repo_root,
        output_path=output_path,
        image_fields=config["image_fields"],
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(browser_rows, columns, config), encoding="utf-8")
    return records


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    root = find_repo_root(Path.cwd())
    parser.add_argument("--repo-root", type=Path, default=root)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    records = build_review_page(
        repo_root=args.repo_root.resolve(),
        input_path=args.input.resolve(),
        config_path=args.config.resolve(),
        output_path=args.output.resolve(),
    )
    print(f"saved: {args.output.resolve()}")
    print(f"review items: {len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
