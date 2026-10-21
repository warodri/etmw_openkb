# OpenKB desktop clients - spec draft (v2, not approved for build)

OpenKB as a real app: Windows .exe and Mac .app, like ChatGPT's desktop apps -
but local-first, open source, and able to act on the computer through opencode
when the user explicitly allows it.

## What the bundle includes

- The Angular UI (same app as the web demo), shown in a native window
- The local server (app/server.py) + library index
- Ollama setup: installer pulls the reader + embedding models on first run
- opencode with the read-only "openkb" agent profile + MCP bridge (agent mode)
- Desktop-only extra: the trust-profile permission layer for acting on the
  computer (below)

## Packaging: all native (Walter's decision, 21 Oct - no Electron, no Tauri)

Two native shells sharing the Angular UI, following the pattern Walter already
built for Amelia (CLIENT/MAC + CLIENT/WINDOWS).

### Reuse analysis - Amelia Mac client (Swift, ~2,650 lines)

- **Reusable nearly as-is**: build.sh (universal arm64+x86_64 swiftc build,
  Developer ID signing with ad-hoc fallback, dist .app + zip) and notarize.sh
  (Apple ID / Team ID / app-specific password flow, staple + re-zip). The
  menu-bar app shell (AmeliaApp: AppState, SetupView, LaunchAgent autostart,
  ServerClient) is the window/system-integration pattern to copy.
- **Reusable with changes**: AmeliaCore/MacTools.swift (~1,200 lines) - the
  computer-capability layer (screen capture, mouse/keyboard, accessibility).
  Keep the capabilities; wrap them in the trust-profile permission model below
  instead of remote-command dispatch.
- **Must be replaced**: the control direction. Amelia's agent is a remote
  worker (WebSocket to the ETMW orchestrator, tasks pushed from the server).
  OpenKB's client is local-first: reasoning is the local Qwen via opencode,
  tasks come from the user in the Angular UI, and nothing is driven from a
  server. AgentCore's server protocol goes; the local opencode/MCP loop takes
  its place.

### Reuse analysis - Amelia Windows client (C#/.NET, ~6,800 lines)

- **Reusable nearly as-is**: tray app shell (TrayApplicationContext, SetupForm,
  StatusForm) and the project/solution scaffolding.
- **Reusable with changes**: UIAutomationTools.cs (~320 lines) and
  ScreenStreamer.cs - same capability-layer treatment as MacTools.
  ExecutionJournal.cs (~275 lines) maps directly onto the audit-trail need
  (the Telegram notice stream is its outward face).
- **Must be replaced**: AgentWebSocketClient/Protocol (server-driven tasks) for
  the local opencode loop, as on Mac.
- **Windows signing: later** (Walter's decision). Ship unsigned/ad-hoc first;
  users accept the SmartScreen prompt or self-build.

## Permission model: trust profiles, not prompt fatigue (v2)

Users hate constant "Allow" prompts, so grants are durable where they can be
and loud only where they must be.

- **Trust profiles**: the user grants a capability once, scoped - e.g. "the
  Work folder", "my browser", "this one app". A profile names the scope and the
  capabilities inside it. Creating a profile is an explicit, explained act.
- **Session-level grants**: within a session the user can approve an action
  class once ("yes, organize files in Work this afternoon") instead of per
  click. Sessions expire when the app closes.
- **Confirmation only for destructive or irreversible actions**: delete,
  overwrite, send, spend, shell commands outside the profile's scope. These
  ask every time, in the moment, no matter the profile.
- **Telegram remains the audit trail**: every acting session sends a short
  "I'm starting to work on your computer now" when it starts and an "All done"
  when it finishes (plus the opt-out-able email notice), so even quiet,
  pre-approved actions leave a visible record. No task detail by default -
  people don't read much (Walter, 21 Oct).
- Every active profile is visible in the UI and revocable in one click; the
  opencode agent profile enforces the same boundary in software (edit/shell
  denied outside granted scopes).

## Distribution and safety model (Walter's decisions, 21 Oct)

- **Source is open.** Anyone can build and self-sign the client for free.
- **The ETMW-signed, ready-made download is part of the $3/month plan.** What
  the $3 buys is the polished path: one small signed download, guided first-run
  model pull, no toolchain, no warnings - versus building from source with
  Xcode/.NET and accepting OS warnings.
- **The Telegram condition**: a client that acts on the computer must be
  connected to the user's Telegram. Notices go out only at task start and task
  end, kept very brief and friendly, with no task detail by default. An email
  notice is also sent; email can be opted out, Telegram cannot.

### Honest analysis of the Telegram condition

**(a) Enforceability.** This can only be enforced in the ETMW-signed build. The
source is open; a fork can delete the check in an afternoon. So the condition
should be understood - and described to users - as a property of the official
build and the paid plan, not a property of the software. That is still valuable:
the people who need the safety net are exactly the people who will use the
official signed app.

**(b) Tension with "nothing leaves your machine."** A Telegram message and an
email leave the machine by definition. The honest fix is to make the content
minimal and say so: by default the notice carries no task detail at all, only
that work started and that it finished ("people don't read much" - Walter, 21
Oct). The user can opt into including the task title; the task content itself
is never included. The README and the panel should state plainly that
act-notifications leave the machine, and that everything else does not.

**(c) Infra and cost.** Telegram: the Bot API is free; a small bot service
(registration + message relay) runs on ETMW's existing server - marginal cost
near zero. Email: ETMW already runs SMTP for alerts, so per-user notice email
reuses that. Real costs are the signing identities (below), not the messaging.

Sample notice wording (very brief, friendly, no task detail by default -
Walter, 21 Oct):

- Start: "Hi! I'm starting to work on your computer now. I'll message you
  right here when I'm done."
- Finish: "All done! If anything looks off, just reply to this message."
- Blocked (Telegram unreachable): "I couldn't reach you here, so I paused
  instead of working unsupervised. I'll pick things up as soon as the
  connection is back."

Notices fire only at task start and task end - never mid-task chatter. The
task title is opt-in detail the user can switch on; the default is no task
text at all.

**(d) Failure behaviour.** If Telegram is unreachable when the client wants to
act, the client does not act. No silent proceed, no queue-and-go: the action is
refused, the UI says why ("couldn't reach Telegram - acting is paused until the
connection is back"), and it retries the connection, not the action. The
notification is the safety property; acting without it defeats the point.

## Signing and notarization (money items - listed, not incurred)

- **Apple Developer Program**: ~$99/year - required for the Developer ID
  signature + notarization that lets Gatekeeper open the app without warnings.
  Walter's notarize.sh already implements the flow.
- **Windows code-signing**: deferred (Walter, 21 Oct). When it comes: OV
  ~$100-300/year, EV ~$300-500/year. Until then: ad-hoc/unsigned with a
  documented SmartScreen click-through, free.
- Self-builders pay nothing and accept the OS warnings.

## Install size (this is the end user's product - it is what the $3 buys)

- App download: ~10-40 MB native - a small, signed, one-click installer
- Models via Ollama on first run: ~20-25 GB (reader + embeddings), pulled once
  by the guided setup, reused by everything local
- Library index: a few MB
- For comparison, an Electron bundle alone would be 150-250 MB before any model

## Staged plan (approved by Walter, 21 Oct)

1. **Stage 1 - wrap what exists.** Package the current UI + server + installer
   as a Mac .app using the Amelia Swift shell pattern; Ollama as a documented
   prerequisite. Internal use only.
2. **Stage 2 - Windows.** The same via the Amelia .NET agent pattern -> .exe.
3. **Stage 3 - acting.** Trust profiles + destructive-action confirmations,
   Telegram notices, email notices with opt-out. Dogfood on Walter's machines.
4. **Stage 4 - distribution.** ETMW-signed Mac build (notarized) and Windows
   build behind the $3/month plan; self-build instructions stay free and
   first-class in the docs.

Public-copy framing (decided by Walter, 21 Oct 13:40): public copy must say
plainly that the paid, ETMW-signed build enforces Telegram notifications, and
that self-built/private use is the user's own choice. The fork loophole is
acknowledged openly, not hidden.

Open problems for Walter:
- Redacted-notice default: minimal task title only, or fully redacted by
  default? Current draft: title only, redaction as a setting.
