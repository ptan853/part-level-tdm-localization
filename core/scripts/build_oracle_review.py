#!/usr/bin/env python3
"""Build the standalone Oracle GT-mask manual-review page."""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path


REVIEW_COLUMNS = [
    "case_uid",
    "part",
    "edit",
    "part_size",
    "target_prompt",
    "oracle_local_edit_0_2",
    "oracle_preservation_0_2",
    "short_note",
]


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    while current != current.parent:
        if (current / "pyproject.toml").is_file():
            return current
        current = current.parent
    raise FileNotFoundError(f"Could not find repository root from {start}")


def load_review_records(repo_root: Path) -> list[dict[str, str]]:
    review_path = repo_root / "core/results/oracle_mask_eval/oracle_local_edit_review.csv"
    with review_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    if len(rows) != 12:
        raise ValueError(f"Expected 12 Oracle review rows, found {len(rows)}")

    records: list[dict[str, str]] = []
    for row in rows:
        case_uid = row["case_uid"]
        record = {column: row.get(column, "") for column in REVIEW_COLUMNS}
        record.update(
            {
                "source_image": f"core/data/partedit_subset/cases/{case_uid}/source.png",
                "gt_mask": f"core/data/partedit_subset/cases/{case_uid}/gt_mask.png",
                "oracle_image": (
                    f"core/results/fys_mask_ablation/oracle_gt_mask/"
                    f"{case_uid}/seed_000/img_0.jpg"
                ),
                "actual_mask": (
                    f"core/results/fys_mask_ablation/oracle_gt_mask/"
                    f"{case_uid}/seed_000/tdm/selected_injection_mask.png"
                ),
            }
        )
        records.append(record)
    return records


def _browser_records(
    records: list[dict[str, str]], repo_root: Path, output_path: Path
) -> list[dict[str, str]]:
    browser_rows = []
    for record in records:
        browser_row = dict(record)
        for key in ("source_image", "gt_mask", "oracle_image", "actual_mask"):
            source_path = repo_root / record[key]
            if not source_path.is_file():
                raise FileNotFoundError(source_path)
            browser_row[key] = Path(os.path.relpath(source_path, output_path.parent)).as_posix()
        browser_rows.append(browser_row)
    return browser_rows


def render_html(records: list[dict[str, str]]) -> str:
    records_json = json.dumps(records, ensure_ascii=True).replace("<", "\\u003c")
    columns_json = json.dumps(REVIEW_COLUMNS)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Oracle GT-mask manual review</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #172126;
      --muted: #607078;
      --line: #d7dee1;
      --paper: #f4f6f5;
      --surface: #ffffff;
      --accent: #087f73;
      --accent-soft: #d9efeb;
      --warning: #a45812;
      --shadow: 0 12px 32px rgba(22, 42, 48, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }}
    button, textarea {{ font: inherit; letter-spacing: 0; }}
    .shell {{ min-height: 100vh; display: grid; grid-template-rows: auto 1fr auto; }}
    header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      padding: 18px 28px;
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
    .progress {{ color: var(--muted); font-size: 14px; white-space: nowrap; }}
    .workspace {{ padding: 22px 28px 18px; }}
    .case-meta {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: start;
      gap: 16px;
      margin-bottom: 16px;
    }}
    .identity {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
    .case-id {{ font: 700 17px ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .tag {{
      padding: 3px 8px;
      border: 1px solid #b9c7cb;
      border-radius: 4px;
      background: var(--surface);
      color: #405158;
      font-size: 12px;
    }}
    .prompt {{ margin: 7px 0 0; color: #34464d; line-height: 1.45; }}
    .case-count {{ color: var(--muted); font-size: 14px; }}
    .images {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    figure {{ margin: 0; min-width: 0; }}
    figcaption {{
      height: 28px;
      display: flex;
      align-items: center;
      color: #42545b;
      font-size: 12px;
      font-weight: 650;
    }}
    .image-frame {{
      width: 100%;
      aspect-ratio: 1 / 1;
      background: #e6ebeb;
      border: 1px solid var(--line);
      overflow: hidden;
    }}
    .image-frame img {{ width: 100%; height: 100%; display: block; object-fit: contain; }}
    .review {{
      display: grid;
      grid-template-columns: 1fr 1fr minmax(260px, 1.35fr);
      gap: 14px;
      padding: 16px;
      background: var(--surface);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
    }}
    .field-label {{ display: block; margin-bottom: 8px; font-size: 13px; font-weight: 700; }}
    .hint {{ margin: 8px 0 0; min-height: 34px; color: var(--muted); font-size: 12px; line-height: 1.4; }}
    .score-group {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }}
    .score-button {{
      height: 42px;
      border: 1px solid #aebcc1;
      border-radius: 5px;
      background: #f8faf9;
      color: var(--ink);
      cursor: pointer;
      font-weight: 750;
    }}
    .score-button:hover {{ border-color: var(--accent); }}
    .score-button.selected {{ border-color: var(--accent); background: var(--accent-soft); color: #075f57; }}
    .score-button:focus-visible, .command:focus-visible, textarea:focus-visible {{ outline: 3px solid #91d5ce; outline-offset: 2px; }}
    textarea {{
      width: 100%;
      min-height: 84px;
      resize: vertical;
      padding: 9px 10px;
      border: 1px solid #aebcc1;
      border-radius: 5px;
      color: var(--ink);
      background: #fbfcfc;
    }}
    footer {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 28px;
      background: var(--surface);
      border-top: 1px solid var(--line);
      position: sticky;
      bottom: 0;
    }}
    .nav, .exports {{ display: flex; gap: 8px; align-items: center; }}
    .command {{
      min-height: 40px;
      padding: 0 14px;
      border: 1px solid #aebcc1;
      border-radius: 5px;
      background: var(--surface);
      color: var(--ink);
      cursor: pointer;
      font-weight: 650;
    }}
    .command.primary {{ background: var(--accent); border-color: var(--accent); color: white; }}
    .command:disabled {{ cursor: not-allowed; opacity: 0.45; }}
    .save-status {{ color: var(--muted); font-size: 12px; }}
    .save-status.complete {{ color: var(--accent); font-weight: 700; }}
    @media (max-width: 900px) {{
      header, footer {{ padding-left: 16px; padding-right: 16px; }}
      .workspace {{ padding: 16px; }}
      .images {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .review {{ grid-template-columns: 1fr; }}
      footer {{ align-items: stretch; flex-direction: column; }}
      .nav, .exports {{ display: grid; grid-template-columns: 1fr 1fr; }}
      .save-status {{ grid-column: 1 / -1; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <h1>Oracle GT-mask manual review</h1>
      <div class="progress" id="progress"></div>
    </header>

    <main class="workspace">
      <section class="case-meta">
        <div>
          <div class="identity">
            <span class="case-id" id="caseUid"></span>
            <span class="tag" id="partSize"></span>
            <span class="tag" id="partEdit"></span>
          </div>
          <p class="prompt" id="targetPrompt"></p>
        </div>
        <div class="case-count" id="caseCount"></div>
      </section>

      <section class="images" aria-label="Case images">
        <figure><figcaption>Source</figcaption><div class="image-frame"><img id="sourceImage" alt="Source image"></div></figure>
        <figure><figcaption>Pixel-level GT mask</figcaption><div class="image-frame"><img id="gtMask" alt="Pixel-level ground-truth part mask"></div></figure>
        <figure><figcaption>Oracle edited result</figcaption><div class="image-frame"><img id="oracleImage" alt="Oracle edited result"></div></figure>
        <figure><figcaption>Projected injection mask</figcaption><div class="image-frame"><img id="actualMask" alt="Oracle mask projected to the FLUX image-token grid"></div></figure>
      </section>

      <section class="review">
        <div>
          <span class="field-label">Local edit success</span>
          <div class="score-group" id="localEditScores"></div>
          <p class="hint">0 absent or wrong; 1 partial or weak; 2 clear and correct.</p>
        </div>
        <div>
          <span class="field-label">Non-target preservation</span>
          <div class="score-group" id="preservationScores"></div>
          <p class="hint">0 major drift; 1 moderate drift; 2 mostly preserved outside the GT part.</p>
        </div>
        <label>
          <span class="field-label">Short note</span>
          <textarea id="shortNote" placeholder="Describe edit success and preservation separately."></textarea>
        </label>
      </section>
    </main>

    <footer>
      <div class="nav">
        <button class="command" id="previousButton" type="button">Previous</button>
        <button class="command" id="nextButton" type="button">Next</button>
      </div>
      <div class="exports">
        <span class="save-status" id="saveStatus">Saved in this browser</span>
        <button class="command" id="copyButton" type="button">Copy CSV</button>
        <button class="command primary" id="downloadButton" type="button">Download CSV</button>
      </div>
    </footer>
  </div>

  <script>
    const records = {records_json};
    const csvColumns = {columns_json};
    const storageKey = "oracle-gt-mask-review-v1";
    let currentIndex = 0;

    function loadSavedRatings() {{
      try {{
        const saved = JSON.parse(localStorage.getItem(storageKey) || "{{}}");
        records.forEach((record) => {{
          if (saved[record.case_uid]) Object.assign(record, saved[record.case_uid]);
        }});
      }} catch (error) {{
        console.warn("Could not restore saved ratings", error);
      }}
    }}

    function saveRatings() {{
      const saved = Object.fromEntries(records.map((record) => [record.case_uid, {{
        oracle_local_edit_0_2: record.oracle_local_edit_0_2,
        oracle_preservation_0_2: record.oracle_preservation_0_2,
        short_note: record.short_note,
      }}]));
      localStorage.setItem(storageKey, JSON.stringify(saved));
      updateProgress();
    }}

    function isScored(record) {{
      return record.oracle_local_edit_0_2 !== "" && record.oracle_preservation_0_2 !== "";
    }}

    function updateProgress() {{
      const scored = records.filter(isScored).length;
      document.getElementById("progress").textContent = `${{scored}} / ${{records.length}} cases scored`;
      const status = document.getElementById("saveStatus");
      status.textContent = scored === records.length ? "All cases scored" : "Saved in this browser";
      status.classList.toggle("complete", scored === records.length);
    }}

    function makeScoreButtons(containerId, field) {{
      const container = document.getElementById(containerId);
      container.replaceChildren();
      [0, 1, 2].forEach((score) => {{
        const button = document.createElement("button");
        button.type = "button";
        button.className = "score-button";
        button.textContent = String(score);
        button.dataset.score = String(score);
        button.dataset.field = field;
        button.setAttribute("aria-pressed", records[currentIndex][field] === String(score));
        button.classList.toggle("selected", records[currentIndex][field] === String(score));
        button.addEventListener("click", () => {{
          records[currentIndex][field] = String(score);
          saveRatings();
          render();
        }});
        container.appendChild(button);
      }});
    }}

    function render() {{
      const record = records[currentIndex];
      document.getElementById("caseUid").textContent = record.case_uid;
      document.getElementById("partSize").textContent = record.part_size;
      document.getElementById("partEdit").textContent = `${{record.part}} -> ${{record.edit}}`;
      document.getElementById("targetPrompt").textContent = `Target: ${{record.target_prompt}}`;
      document.getElementById("caseCount").textContent = `Case ${{currentIndex + 1}} of ${{records.length}}`;
      document.getElementById("sourceImage").src = record.source_image;
      document.getElementById("gtMask").src = record.gt_mask;
      document.getElementById("oracleImage").src = record.oracle_image;
      document.getElementById("actualMask").src = record.actual_mask;
      document.getElementById("shortNote").value = record.short_note || "";
      makeScoreButtons("localEditScores", "oracle_local_edit_0_2");
      makeScoreButtons("preservationScores", "oracle_preservation_0_2");
      document.getElementById("previousButton").disabled = currentIndex === 0;
      document.getElementById("nextButton").disabled = currentIndex === records.length - 1;
      updateProgress();
    }}

    function csvCell(value) {{
      const text = String(value ?? "");
      return `"${{text.replaceAll('"', '""')}}"`;
    }}

    function buildCsv() {{
      const lines = [csvColumns.map(csvCell).join(",")];
      records.forEach((record) => lines.push(csvColumns.map((column) => csvCell(record[column])).join(",")));
      return lines.join("\\r\\n") + "\\r\\n";
    }}

    function downloadCsv() {{
      const blob = new Blob(["\\ufeff", buildCsv()], {{ type: "text/csv;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "oracle_local_edit_review.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }}

    async function copyCsv() {{
      await navigator.clipboard.writeText(buildCsv());
      const button = document.getElementById("copyButton");
      button.textContent = "Copied";
      setTimeout(() => {{ button.textContent = "Copy CSV"; }}, 1200);
    }}

    document.getElementById("previousButton").addEventListener("click", () => {{
      currentIndex = Math.max(0, currentIndex - 1);
      render();
    }});
    document.getElementById("nextButton").addEventListener("click", () => {{
      currentIndex = Math.min(records.length - 1, currentIndex + 1);
      render();
    }});
    document.getElementById("shortNote").addEventListener("input", (event) => {{
      records[currentIndex].short_note = event.target.value;
      saveRatings();
    }});
    document.getElementById("downloadButton").addEventListener("click", downloadCsv);
    document.getElementById("copyButton").addEventListener("click", () => copyCsv().catch((error) => {{
      console.error("Copy failed", error);
      window.prompt("Copy the CSV below:", buildCsv());
    }}));

    loadSavedRatings();
    render();
  </script>
</body>
</html>
"""


def build_review_page(repo_root: Path, output_path: Path) -> list[dict[str, str]]:
    records = load_review_records(repo_root)
    browser_rows = _browser_records(records, repo_root, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(browser_rows), encoding="utf-8")
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = find_repo_root(Path.cwd())
    parser.add_argument("--repo-root", type=Path, default=default_root)
    parser.add_argument(
        "--output",
        type=Path,
        default=default_root / "core/results/oracle_mask_eval/oracle_local_edit_review.html",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = build_review_page(args.repo_root.resolve(), args.output.resolve())
    print(f"saved: {args.output.resolve()}")
    print(f"cases: {len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
