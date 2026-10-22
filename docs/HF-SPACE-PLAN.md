# Hugging Face Space plan (docs only, nothing published)

Status: PLAN. Requested by Walter 22 Oct 2026, 13:36. Nothing has been created or published. Sources: Hugging Face docs, https://huggingface.co/docs/hub/spaces-overview and https://huggingface.co/docs/hub/spaces-sdks-static (read 22 Oct 2026).

## 1. What the Space would be
Goal: visibility. People browsing Hugging Face find OpenKB, see what it is, and try it.

**Recommended: a Static Space** (sdk: static) that is a front end calling the live Mac Mini API.
- Static Spaces are free for everyone and run no compute. Gradio and Docker Spaces need a paid plan to create (PRO for a personal account), per the docs.
- The small local model (a 35B reader) cannot run on the free CPU Space (2 vCPU, 16 GB), so a self-contained demo is not possible there without paid GPU hardware. Even then it would need the library, which lives as references only.
- v1: a landing page with the OpenKB hero (text unchanged), a live status badge and counter (from /api/public-stats), three screenshots, "Open the live demo" button (opens https://openkb--warodri.entertomyworld.com/ in a new tab), links to GitHub and the docs. Donations stay closed ("Donations open soon").
- v2 (only after a test): an embedded ask box on the Space that calls /ask. Reason to wait: browsers block cookies in an embedded frame, and the app keeps the anonymous session and daily cap per browser cookie and IP. Test first whether /ask works without a cookie and whether the per-IP limits still hold.

Not recommended: copying the library or an index to a Hugging Face dataset. The library holds references only; a published index would make the vectors public (a lawyer question, see docs/VISION.md section 9).

## 2. What it needs
- Walter creates the Hugging Face account (and chooses personal vs organisation name). I do not create accounts.
- A write token for the Space repo, via a vault link only (never pasted in chat). Created by him under Settings, Access Tokens, scoped to that one Space repo if the account allows it.
- Decision: Space name and visibility (public for visibility), licence field (Apache-2.0 for the code, per the repo).
- On the Mac Mini side (small, reversible): CORS allow-list for the Space origin (https://<user>-<name>.hf.space) on /api/public-stats; later /ask for v2. Back up demo_server.py first.
- Build: static HTML from the existing Angular front end or a simple page (about 1 hour), screenshots in light and dark, mobile check. Push with git once the token exists.

## 3. Risks
- **Load.** One Mac Mini, one reader: about one answer every 5-6 s. A visibility spike would queue. Limits already live: DAILY_CAP 1000, queue of 12 with a message, per-IP rate limits. v1 sends visitors to the main app and only the status call is cross-site, so the Space itself adds almost no load.
- **Availability.** If the Mac sleeps or the tunnel drops the badge shows "demo offline" instead of a broken page.
- **Security.** Static Spaces hold no secrets: Space variables are readable by the page. So no keys in the Space, only public URLs. CORS is limited to the Space origin, not "*". No credentials, no cookies on cross-site calls. Third-party content is only our own API. Keep the HF token only in the vault and rotate it if exposed.
- **Privacy.** The Space page itself shows no visitor data to us. Calls to our API are logged like any other (IP, time); the how/privacy page already says so.
- **Content rules.** The Space page shows no library text. Quotes only on request in the app, with the licence shown.
- **Reputation.** A public Space is visible to anyone and can be reported. Keep the README honest: v0.1 beta, small library, runs on one machine.

## 4. README card (front matter and text)
```
---
title: OpenKB
emoji: 📚
colorFrom: indigo
colorTo: blue
sdk: static
pinned: false
license: apache-2.0
short_description: A small local AI model reading one shared open library
tags:
  - rag
  - open-knowledge
  - local-first
---

# OpenKB

OpenKB is the first model you can run locally... (hero text exactly as on the site, unchanged)

A small AI model that runs on your own machine reads one shared library of open-licensed documents. It looks up only the parts it needs, answers from them, and shows the source and the licence. If the answer is not in the library, it says so.

- **Try the live demo:** https://openkb--warodri.entertomyworld.com/
- **Code (Apache 2.0):** https://github.com/warodri/etmw_openkb
- **Library:** public domain, CC0, CC BY, CC BY-SA, MIT, Apache-2.0 and BSD documents, each tagged with its licence. The library keeps references, offsets and vectors, not copies; text is read from the source when you ask.
- **Status:** v0.1 beta. A small library, one machine. Donations open soon.
- **Report a problem or a copyright concern:** use the Report button in the app.
```
(Hero line: use Walter's exact hero text from the live site when the page is built; do not edit it.)

## 5. Steps once Walter says go
1. He creates the HF account and sends the vault link request; I report the link.
2. I build the static page, show screenshots to main, he approves.
3. I add the CORS allow-list (backup first) and test the status badge from the Space origin.
4. I push the Space and report the URL. Nothing is published before step 2 is approved.
