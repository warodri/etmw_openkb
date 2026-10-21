# Email-code login - spec draft (not approved for build)

Sign-in for OpenKB: an email address and a one-time code. No passwords, no
accounts to manage. Tasks tie to the email identity instead of the anonymous
browser cookie; the cookie remains as the pre-login state and for local-only use.

## Flow

1. User enters their email address.
2. Server sends a 6-digit one-time code. The address is stored hashed
   (SHA-256, salted) until the code verifies.
3. User enters the code. On success the server issues a session cookie
   (HttpOnly, SameSite=Lax, 30 days, rolling). Tasks created while anonymous
   are offered for claiming into the account on first login.
4. Signing out drops the session; tasks stay with the account.

## Rules

- **Code expiry**: 10 minutes. One active code per email; requesting a new
  code invalidates the previous one.
- **Attempt limits**: 5 wrong attempts burn the code (a new one must be
  requested). 10 burned codes per email per day locks sign-in for that
  address for 24h.
- **Send rate-limits** (the login mail must never become a spam relay):
  max 3 codes per email per hour, 5 per day; max 20 code emails per IP per
  hour; global daily cap shared with the demo guards. Codes are requested
  only through a bot-checked form (minimal JS challenge); no CC/BCC, no
  user-supplied subject or body - the server renders the whole message.
- **No password storage**: there are no passwords. Sessions are opaque
  tokens; only their hashes are stored.
- **Data retention/deletion**: unverified addresses (hashed) expire after
  24h. Verified accounts keep email + tasks until the user deletes the
  account: one click in the UI deletes the email, all tasks, all messages,
  and sessions, confirmed by a final email to the same address. Request logs
  keep IPs for 30 days, then drop them.
- **Privacy notice** (shown at sign-in, plain language): we store your email
  address to sign you in and your tasks to show them back to you; we do not
  read your tasks, sell anything, or mail you anything except sign-in codes
  and the deletion confirmation.

## Hosting split

- **Self-hosters**: configure their own SMTP via env (`SMTP_HOST`,
  `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` in
  `OPENKB_ENV_FILE`); the installer prompts for it. Without SMTP, email
  login is unavailable and the app stays in anonymous-cookie mode - say so
  plainly in the UI. The /host page documents this.
- **Hosted $3/month plan**: mail included, sent through ETMW's existing
  mailbox and SMTP - no new spend, no per-user mail config.
- **Live demo**: uses the same ETMW mailbox as the owner alerts
  (warodri@gmail.com SMTP credentials already in env), owner-only guard on
  outbound templates unchanged.

## What stays untouched

Per-IP and global rate limits, the daily cap, input/output caps, the request
log, and owner-only alerting are unchanged. Login emails are counted in the
same global caps so auth traffic can never crowd out answers.
