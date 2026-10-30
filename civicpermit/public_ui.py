"""Public UI shell for Townlight Permitting.

Two parts, both honest about what they show:

* the original static ADU sample (kept, labelled as such), and
* a real project-description form that calls the cited pathway API and renders
  the returned likely permits, attachments, timeline, fee availability and
  resident explanation - including explicit "unavailable" lines when a source
  did not resolve.
"""

from __future__ import annotations


def render_public_lookup_page() -> str:
    """Render the public-facing Townlight Permitting page."""

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Townlight Permitting Pre-Application Intake</title>
<style>
  :root { --ink:#17202a; --muted:#56606a; --paper:#fffdf7; --blue:#1f5b78; --green:#2f6b50; --gold:#d8b45b; --line:#d7c8a8; }
  * { box-sizing: border-box; }
  body { margin:0; color:var(--ink); font-family:"Aptos","Segoe UI",sans-serif; background:linear-gradient(135deg,#f7f1e6,#edf6fb); }
  .skip-link { position:absolute; left:1rem; top:-4rem; background:var(--ink); color:white; padding:.7rem 1rem; border-radius:8px; }
  .skip-link:focus { top:1rem; }
  header, main, footer { width:min(1120px, calc(100% - 32px)); margin:0 auto; }
  header { padding:48px 0 24px; }
  .eyebrow { color:var(--blue); text-transform:uppercase; letter-spacing:0; font-weight:800; font-size:.78rem; }
  h1 { max-width:960px; margin:0; font-family:Georgia,"Times New Roman",serif; font-size:4.75rem; line-height:1; letter-spacing:0; }
  .lede { max-width:820px; font-size:1.35rem; line-height:1.55; color:#31404a; }
  .badge { display:inline-flex; width:fit-content; padding:.45rem .75rem; border-radius:8px; background:var(--green); color:white; font-weight:900; }
  .grid { display:grid; grid-template-columns:repeat(12,1fr); gap:18px; }
  .card { grid-column:span 6; min-width:0; padding:24px; border:1px solid var(--line); border-radius:8px; background:rgba(255,253,247,.92); box-shadow:0 18px 40px rgba(35,43,50,.10); }
  .card.large { grid-column:span 12; }
  h2,h3 { font-family:Georgia,"Times New Roman",serif; letter-spacing:0; }
  h2 { margin:0 0 14px; font-size:2.4rem; }
  p, li { line-height:1.65; }
  .sample-box { padding:18px; border:1px solid #b9c6cc; border-radius:8px; background:#f3f7f8; color:var(--ink); }
  .result { margin-top:18px; padding:18px; border-left:6px solid var(--green); border-radius:8px; background:white; }
  .warning { border-left-color:#b2603f; background:#fff8f4; }
  .kicker { color:var(--muted); font-size:.86rem; font-weight:900; letter-spacing:0; text-transform:uppercase; }
  footer { padding:38px 0 56px; color:var(--muted); }
  :focus-visible { outline:4px solid var(--gold); outline-offset:3px; }
  label { display:block; font-weight:700; margin:14px 0 6px; }
  textarea, input[type=text] { width:100%; padding:12px; border:1px solid var(--line); border-radius:8px; font:inherit; background:white; }
  button { margin-top:14px; padding:12px 20px; border:0; border-radius:8px; background:var(--blue); color:white; font:inherit; font-weight:800; cursor:pointer; }
  button[disabled] { opacity:.6; cursor:progress; }
  .cite { color:var(--muted); font-size:.88rem; }
  .unavailable { border-left-color:#b2603f; }
  @media (max-width:760px) { header,main,footer{margin:0;max-width:390px;width:100%;padding-left:24px;padding-right:24px}header{padding-top:34px}h1{font-size:2.55rem}.lede{font-size:1.08rem}h2{font-size:1.9rem}.card{grid-column:span 12;padding:20px;border-radius:8px} }
</style>
</head>
<body>
<a class="skip-link" href="#main">Skip to main content</a>
<header>
  <p class="eyebrow">Townlight / Townlight Permitting</p>
  <h1>Help applicants arrive with the right first packet.</h1>
  <p class="lede">Describe your project to see the likely permit pathway, the attachments to gather, typical review timing and a plain-language explanation. Every item shows the public source it came from.</p>
  <p><span class="badge">v0.2.2 permit pre-application + staff review queues</span></p>
</header>
<main id="main" tabindex="-1">
  <section class="grid" aria-labelledby="pathway-title">
    <article class="card large">
      <p class="kicker">Cited pre-application pathway</p>
      <h2 id="pathway-title">Describe your project</h2>
      <form id="pathway-form" novalidate>
        <label for="project-type">Project type</label>
        <input type="text" id="project-type" name="project_type" value="adu" autocomplete="off">
        <label for="proposal">Project description</label>
        <textarea id="proposal" name="proposal" rows="5">Convert the detached garage at 100 Main Street into an ADU with a new utility connection.</textarea>
        <label for="location">Location context (optional)</label>
        <input type="text" id="location" name="location_context" placeholder="Address or parcel identifier" autocomplete="off">
        <button type="submit" id="pathway-submit">Show likely pathway</button>
      </form>
      <div class="result" id="pathway-result" role="status" aria-live="polite" hidden></div>
    </article>
    <article class="card large">
      <p class="kicker">Static sample</p>
      <h2>ADU pre-application checklist</h2>
      <div class="sample-box">Applicant proposes an ADU at 100 Main Street with a site plan and utility description.</div>
      <div class="result">
        <h3>Materials to gather</h3>
        <ul><li>Site plan showing existing and proposed structures.</li><li>Parking and access narrative.</li><li>Utility connection description.</li></ul>
      </div>
    </article>
    <article class="card"><p class="kicker">Intake readiness</p><h2>Follow-up before submittal</h2><div class="result"><p>Missing items are returned as actionable applicant follow-up and can be routed to a staff-only review queue, not as an official completeness decision.</p></div></article>
    <article class="card"><p class="kicker">Boundary</p><h2>No permit approval</h2><div class="result warning"><p>Townlight Permitting does not approve permits, calculate official fees, schedule inspections, or replace the permitting system of record.</p></div></article>
  </section>
</main>
<footer><p>Townlight Permitting is part of the AGPL-3.0 Townlight open-source municipal AI project.</p></footer>
<script>
(function () {
  var form = document.getElementById('pathway-form');
  var button = document.getElementById('pathway-submit');
  var result = document.getElementById('pathway-result');

  function list(items, render) {
    if (!items || !items.length) { return null; }
    var ul = document.createElement('ul');
    items.forEach(function (item) {
      var li = document.createElement('li');
      render(li, item);
      ul.appendChild(li);
    });
    return ul;
  }

  function heading(text) {
    var h = document.createElement('h3');
    h.textContent = text;
    return h;
  }

  function cite(text) {
    var span = document.createElement('span');
    span.className = 'cite';
    span.textContent = text ? ' — ' + text : '';
    return span;
  }

  function render(payload) {
    result.textContent = '';
    result.hidden = false;

    result.appendChild(heading(payload.title || 'Likely pathway'));

    var permits = list(payload.likely_permits, function (li, item) {
      li.textContent = item.step + ' (' + item.typical_time + ')';
      li.appendChild(cite(item.citation));
    });
    if (permits) {
      var p = document.createElement('p');
      p.textContent = 'Likely review steps';
      result.appendChild(p);
      result.appendChild(permits);
    }

    var attachments = list(payload.attachments, function (li, item) {
      li.textContent = item.material;
      li.appendChild(cite(item.citation));
    });
    if (attachments) {
      var a = document.createElement('p');
      a.textContent = 'Attachments to gather';
      result.appendChild(a);
      result.appendChild(attachments);
    }

    var timeline = list(payload.timeline, function (li, item) {
      li.textContent = item.step + ': ' + item.typical_time;
      li.appendChild(cite(item.citation));
    });
    if (timeline) {
      var t = document.createElement('p');
      t.textContent = 'Typical review timing';
      result.appendChild(t);
      result.appendChild(timeline);
    }

    var fee = document.createElement('p');
    fee.className = payload.fee && payload.fee.status === 'unavailable' ? 'unavailable' : '';
    fee.textContent = payload.fee && payload.fee.status === 'unavailable'
      ? payload.fee.reason
      : 'Published fee information: ' + (payload.fee ? payload.fee.as_published : '');
    result.appendChild(fee);

    var explanation = document.createElement('p');
    explanation.textContent = payload.resident_explanation || '';
    result.appendChild(explanation);

    if (payload.unavailable && payload.unavailable.length) {
      result.appendChild(heading('Unavailable, not assumed'));
      result.appendChild(list(payload.unavailable, function (li, item) {
        li.textContent = item.item + ': ' + item.reason;
      }));
    }

    var assistance = payload.assistance || {};
    var assist = document.createElement('p');
    assist.className = 'cite';
    assist.textContent = assistance.executed
      ? 'Model assistance executed with ' + assistance.provider + ' (' + assistance.model + '). Staff review still required.'
      : 'Model assistance not executed: ' + (assistance.reason || 'no provider configured') + '.';
    result.appendChild(assist);

    var boundary = document.createElement('p');
    boundary.className = 'cite';
    boundary.textContent = payload.boundary || '';
    result.appendChild(boundary);
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    button.disabled = true;
    result.hidden = false;
    result.textContent = 'Looking up cited sources…';
    fetch('/api/v1/civicpermit/pathway/explain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_type: document.getElementById('project-type').value || 'general',
        proposal: document.getElementById('proposal').value || '',
        location_context: document.getElementById('location').value || ''
      })
    }).then(function (response) {
      return response.json().then(function (body) {
        if (!response.ok) { throw new Error((body.detail && body.detail.message) || 'Request failed'); }
        return body;
      });
    }).then(render).catch(function (error) {
      result.textContent = '';
      var p = document.createElement('p');
      p.className = 'unavailable';
      p.textContent = 'The cited pathway could not be loaded: ' + error.message
        + '. No substitute text is shown; try again or contact staff.';
      result.appendChild(p);
    }).then(function () {
      button.disabled = false;
    });
  });
})();
</script>
</body>
</html>
"""
