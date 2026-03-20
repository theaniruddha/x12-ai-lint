from flask import Flask, jsonify, request, render_template_string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>X12 Claim Validator</title>
  <style>
    body { font-family: monospace; max-width: 760px; margin: 60px auto; padding: 0 20px; background: #f9f9f9; color: #111; }
    h1 { font-size: 1.2rem; margin-bottom: 24px; }
    label { display: block; margin-bottom: 4px; font-size: 0.85rem; font-weight: bold; }
    input { width: 100%; padding: 8px; margin-bottom: 16px; border: 1px solid #ccc; border-radius: 4px; font-family: monospace; font-size: 0.95rem; box-sizing: border-box; }
    button { padding: 10px 24px; background: #111; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-family: monospace; font-size: 0.95rem; }
    button:disabled { background: #888; cursor: default; }
    #spinner { margin-top: 12px; font-size: 0.82rem; color: #555; display: none; }

    #result { margin-top: 28px; display: none; }

    .verdict-banner { padding: 14px 18px; border-radius: 6px; font-size: 1.1rem; font-weight: bold; letter-spacing: 0.04em; margin-bottom: 20px; }
    .APPROVED { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .REVIEW   { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
    .DENIED   { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }

    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 20px; }
    .card { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 14px; }
    .card-title { font-size: 0.72rem; text-transform: uppercase; color: #777; margin-bottom: 4px; }
    .card-code { font-size: 1.05rem; font-weight: bold; margin-bottom: 4px; }
    .card-desc { font-size: 0.85rem; color: #333; }

    .section-label { font-size: 0.72rem; text-transform: uppercase; color: #777; margin-bottom: 6px; }
    .rationale { background: #fff; border: 1px solid #ddd; border-radius: 6px; padding: 14px; font-size: 0.88rem; line-height: 1.6; margin-bottom: 14px; }

    .flags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }
    .flag { background: #fee; color: #900; border: 1px solid #fcc; border-radius: 4px; padding: 3px 10px; font-size: 0.78rem; }

    .suggestion { background: #fff8e1; border: 1px solid #ffe082; border-radius: 6px; padding: 12px 14px; font-size: 0.85rem; margin-bottom: 14px; }
    .suggestion strong { display: block; margin-bottom: 2px; }

    .confidence-bar-wrap { margin-bottom: 20px; }
    .confidence-label { font-size: 0.78rem; color: #555; margin-bottom: 4px; }
    .bar-bg { background: #e0e0e0; border-radius: 4px; height: 10px; }
    .bar-fill { height: 10px; border-radius: 4px; background: #4caf50; transition: width 0.4s; }
    .bar-fill.REVIEW { background: #ff9800; }
    .bar-fill.DENIED { background: #e53935; }
  </style>
</head>
<body>
  <h1>X12 Claim Validator</h1>

  <label for="dx">Diagnosis Code (ICD-10)</label>
  <input id="dx" type="text" placeholder="e.g. E11.9" />
  <label for="cpt">Procedure Code (CPT)</label>
  <input id="cpt" type="text" placeholder="e.g. 99214" />
  <button id="btn" onclick="runValidation()">Validate Claim</button>
  <div id="spinner">Running agents, please wait...</div>

  <div id="result">
    <div id="verdict-banner" class="verdict-banner"></div>

    <div class="grid">
      <div class="card">
        <div class="card-title">Diagnosis (ICD-10)</div>
        <div class="card-code" id="r-dx-code"></div>
        <div class="card-desc" id="r-dx-desc"></div>
      </div>
      <div class="card">
        <div class="card-title">Procedure (CPT)</div>
        <div class="card-code" id="r-cpt-code"></div>
        <div class="card-desc" id="r-cpt-desc"></div>
      </div>
    </div>

    <div class="confidence-bar-wrap">
      <div class="confidence-label" id="conf-label"></div>
      <div class="bar-bg"><div class="bar-fill" id="conf-bar"></div></div>
    </div>

    <div class="section-label">Rationale</div>
    <div class="rationale" id="r-rationale"></div>

    <div id="flags-wrap">
      <div class="section-label">Flags</div>
      <div class="flags" id="r-flags"></div>
    </div>

    <div id="suggestion-wrap" class="suggestion" style="display:none">
      <strong>Suggested alternative</strong>
      <span id="r-suggestion"></span>
    </div>
  </div>

  <script>
    async function runValidation() {
      const dx = document.getElementById('dx').value.trim();
      const cpt = document.getElementById('cpt').value.trim();
      if (!dx || !cpt) { alert('Enter both codes.'); return; }

      const btn = document.getElementById('btn');
      const spinner = document.getElementById('spinner');
      const result = document.getElementById('result');

      btn.disabled = true;
      spinner.style.display = 'block';
      result.style.display = 'none';

      try {
        const res = await fetch('/resolve', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ dx_code: dx, cpt_code: cpt })
        });
        const d = await res.json();
        if (d.error) { alert('Error: ' + d.error); return; }

        const v = d.verdict;
        const banner = document.getElementById('verdict-banner');
        banner.textContent = v.status;
        banner.className = 'verdict-banner ' + v.status;

        document.getElementById('r-dx-code').textContent = v.dx_code;
        document.getElementById('r-dx-desc').textContent = v.dx_description;
        document.getElementById('r-cpt-code').textContent = v.cpt_code;
        document.getElementById('r-cpt-desc').textContent = v.cpt_description;

        const pct = Math.round(v.confidence * 100);
        document.getElementById('conf-label').textContent = `Confidence: ${pct}%`;
        const bar = document.getElementById('conf-bar');
        bar.style.width = pct + '%';
        bar.className = 'bar-fill ' + v.status;

        document.getElementById('r-rationale').textContent = v.rationale;

        const flagsEl = document.getElementById('r-flags');
        flagsEl.innerHTML = '';
        if (v.flags && v.flags.length > 0) {
          v.flags.forEach(f => {
            const span = document.createElement('span');
            span.className = 'flag';
            span.textContent = f;
            flagsEl.appendChild(span);
          });
          document.getElementById('flags-wrap').style.display = 'block';
        } else {
          document.getElementById('flags-wrap').style.display = 'none';
        }

        const sw = document.getElementById('suggestion-wrap');
        if (v.suggested_code) {
          document.getElementById('r-suggestion').textContent =
            v.suggested_code + (v.suggested_description ? ' — ' + v.suggested_description : '');
          sw.style.display = 'block';
        } else {
          sw.style.display = 'none';
        }

        result.style.display = 'block';
      } catch (e) {
        alert('Request failed: ' + e.message);
      } finally {
        btn.disabled = false;
        spinner.style.display = 'none';
      }
    }
  </script>
</body>
</html>"""


@app.get("/")
def index():
    return render_template_string(_PAGE)


@app.post("/resolve")
def resolve():
    body = request.get_json(force=True)
    dx = body.get("dx_code", "").strip()
    cpt = body.get("cpt_code", "").strip()
    if not dx or not cpt:
        return jsonify({"error": "dx_code and cpt_code are required"}), 400

    from pipeline import pipeline
    state = pipeline.invoke({"dx_code": dx, "cpt_code": cpt})
    verdict = state["verdict"]
    return jsonify({"verdict": verdict.model_dump()})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})
