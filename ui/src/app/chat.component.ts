import { Component, ElementRef, OnInit, ViewChild, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ThemeService } from './theme.service';
import { ApiService, ChatMessage, Task } from './api.service';

@Component({
  selector: 'app-chat',
  imports: [FormsModule, RouterLink],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css',
})
export class ChatComponent implements OnInit {
  private api = inject(ApiService);
  protected theme = inject(ThemeService);

  active = signal<Task[]>([]);
  archived = signal<Task[]>([]);
  task = signal<Task | null>(null);
  messages = signal<ChatMessage[]>([]);
  busy = signal(false);
  waiting = signal(false);
  showJump = signal(false);
  hasNew = signal(false);
  private atBottom = true;
  micState = signal<'idle' | 'recording' | 'transcribing'>('idle');
  micError = signal<string | null>(null);
  micSupported = typeof navigator !== 'undefined' && !!navigator.mediaDevices?.getUserMedia && typeof MediaRecorder !== 'undefined';
  private rec?: MediaRecorder;
  private recChunks: Blob[] = [];
  private recStream?: MediaStream;
  private recTimer?: ReturnType<typeof setTimeout>;
  @ViewChild('scroller') scroller?: ElementRef<HTMLElement>;
  @ViewChild('box') box?: ElementRef<HTMLTextAreaElement>;

  constructor() {
    // Follow new text only while the reader is at the bottom; otherwise flag it.
    effect(() => {
      this.messages(); this.waiting();
      requestAnimationFrame(() => {
        if (this.atBottom) this.scrollToBottom(false);
        else if (this.showJump()) this.hasNew.set(true);
      });
    });
  }

  onScroll(): void {
    const el = this.scroller?.nativeElement; if (!el) return;
    this.atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    this.showJump.set(!this.atBottom);
    if (this.atBottom) this.hasNew.set(false);
  }

  scrollToBottom(smooth: boolean): void {
    const el = this.scroller?.nativeElement; if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  }

  jumpToBottom(): void { this.atBottom = true; this.hasNew.set(false); this.showJump.set(false); this.scrollToBottom(true); }

  async toggleMic(): Promise<void> {
    if (this.micState() === 'recording') { this.stopMic(); return; }
    if (this.micState() !== 'idle' || this.busy()) return;
    this.micError.set(null);
    try {
      this.recStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      this.micError.set('Microphone is blocked. Allow it in your browser settings to dictate.');
      return;
    }
    const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
    const mime = types.find((m) => MediaRecorder.isTypeSupported(m));
    this.recChunks = [];
    this.rec = new MediaRecorder(this.recStream, mime ? { mimeType: mime } : undefined);
    this.rec.ondataavailable = (e) => { if (e.data.size) this.recChunks.push(e.data); };
    this.rec.onstop = () => this.sendClip(this.rec?.mimeType || mime || 'audio/webm');
    this.rec.start();
    this.micState.set('recording');
    this.recTimer = setTimeout(() => this.stopMic(), 29000);
  }

  private stopMic(): void {
    clearTimeout(this.recTimer);
    if (this.rec && this.rec.state !== 'inactive') this.rec.stop();
    this.recStream?.getTracks().forEach((tr) => tr.stop());
  }

  private sendClip(mime: string): void {
    const blob = new Blob(this.recChunks, { type: mime });
    this.recChunks = [];
    if (blob.size < 1500) { this.micState.set('idle'); this.micError.set('That was too short. Tap the mic and try again.'); return; }
    this.micState.set('transcribing');
    this.api.transcribe(blob).subscribe({
      next: (r) => {
        const text = (r.text || '').trim();
        if (text) { this.input = (this.input ? this.input.trimEnd() + ' ' : '') + text; setTimeout(() => this.resizeBox()); this.box?.nativeElement.focus(); }
        else this.micError.set('I could not hear anything. Try again.');
        this.micState.set('idle');
      },
      error: (e) => { this.micState.set('idle'); this.micError.set(e?.error?.error || 'Dictation failed. Try again.'); },
    });
  }

  resizeBox(): void {
    const el = this.box?.nativeElement; if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
  }
  error = signal<string | null>(null);
  panel = signal<'how' | 'donate' | null>(null);
  showArchived = signal(false);
  sidebarOpen = signal(false);
  reportOpen = signal(false);
  reportChoices = signal<{ id: string; name: string }[]>([]);
  reportDoc = signal('');
  reportReason = signal('copyright');
  reportDetails = signal('');
  reportEmail = signal('');
  reportState = signal<'idle' | 'sending' | 'done' | 'error'>('idle');
  reportResult = signal('');
  reportMsg = signal('');
  reportClaimant = signal('');
  reportUrl = signal('');
  reportStatement = signal(false);
  reportHolderContact = signal('');
  reportOutcome = signal('');
  readonly reasons = [
    { v: 'copyright', t: 'It is copyrighted and should not be here' },
    { v: 'personal-data', t: 'It has personal or private information' },
    { v: 'harmful', t: 'It is harmful or illegal' },
    { v: 'quality', t: 'It is wrong or low quality' },
    { v: 'other', t: 'Something else' },
  ];

  /** Unique (id, name) pairs for the sources of one answer. */
  sourceChoices(m: { sources?: string[]; source_ids?: string[] }): { id: string; name: string }[] {
    const seen = new Set<string>(); const out: { id: string; name: string }[] = [];
    (m.sources || []).forEach((name, i) => { const id = (m.source_ids || [])[i] || ''; if (id && !seen.has(id)) { seen.add(id); out.push({ id, name }); } });
    return out;
  }

  sourceLine(m: { sources?: string[]; licences?: string[] }): string {
    return [...new Set((m.sources || []).map((s, i) => { const l = (m.licences || [])[i]; return l ? s + ' (' + l + ')' : s; }))].join(', ');
  }

  openReport(m: { sources?: string[]; source_ids?: string[] }): void {
    const ch = this.sourceChoices(m);
    this.reportChoices.set(ch); this.reportDoc.set(ch[0]?.id || '');
    this.reportReason.set('copyright'); this.reportDetails.set(''); this.reportEmail.set('');
    this.reportState.set('idle'); this.reportMsg.set(''); this.reportResult.set(''); this.reportClaimant.set(''); this.reportHolderContact.set(''); this.reportUrl.set(''); this.reportStatement.set(false); this.reportOutcome.set(''); this.reportOpen.set(true);
  }

  sendReport(): void {
    if (this.reportState() === 'sending') return;
    this.reportState.set('sending'); this.reportMsg.set('');
    this.api.report({ doc_id: this.reportDoc(), reason: this.reportReason(), details: this.reportDetails(), email: this.reportEmail(),
      claimant: this.reportClaimant(), holder_contact: this.reportHolderContact(), evidence_url: this.reportUrl(), statement: this.reportStatement() }).subscribe({
      next: (r) => {
        this.reportOutcome.set(r.outcome); this.reportMsg.set(r.message); this.reportResult.set(r.id);
        this.reportState.set(r.outcome === 'needs-evidence' ? 'error' : 'done');
      },
      error: (e) => { this.reportState.set('error'); this.reportMsg.set(e?.error?.error || 'Could not send the report. Try again in a moment.'); },
    });
  }
  desktopOpen = signal(typeof localStorage === 'undefined' || localStorage.getItem('okb-sidebar') !== 'closed');
  searching = signal(false);
  query = signal('');
  filteredActive = computed(() => this.filterTasks(this.active()));
  filteredArchived = computed(() => this.filterTasks(this.archived()));

  private filterTasks(list: Task[]): Task[] {
    const q = this.query().trim().toLowerCase();
    return q ? list.filter((x) => x.title.toLowerCase().includes(q)) : list;
  }

  toggleSidebar(): void {
    if (typeof window !== 'undefined' && window.innerWidth >= 768) {
      this.desktopOpen.update((v) => !v);
      try { localStorage.setItem('okb-sidebar', this.desktopOpen() ? 'open' : 'closed'); } catch {}
    } else {
      this.sidebarOpen.update((v) => !v);
    }
  }

  toggleSearch(): void {
    this.searching.update((v) => !v);
    if (!this.searching()) this.query.set('');
    else setTimeout(() => (document.querySelector('aside input[type=search]') as HTMLInputElement | null)?.focus());
  }
  userEmail = signal<string | null>(null);
  authOpen = signal(false);
  authStep = signal<'email' | 'code'>('email');
  authBusy = signal(false);
  authError = signal<string | null>(null);
  authEmail = '';
  authAns = '';
  authCode = '';
  authQ = signal('');
  private authCid = '';
  input = '';

  stats = signal<{ active_crawlers: number; documents: number; added_24h: number; last_active: string | null } | null>(null);
  ago(ts: string | null | undefined): string {
    if (!ts) return '';
    const m = Math.max(0, Math.round((Date.now() - new Date(ts).getTime()) / 60000));
    return m < 2 ? 'just now' : m < 60 ? m + ' min ago' : m < 1440 ? Math.round(m / 60) + ' h ago' : Math.round(m / 1440) + ' d ago';
  }
  ngOnInit(): void {
    this.api.publicStats().subscribe({ next: (s) => this.stats.set(s.enabled ? (s as any) : null), error: () => this.stats.set(null) });
    this.refresh();
    this.api.authMe().subscribe({ next: (r) => this.userEmail.set(r.email), error: () => {} });
  }

  openAuth(): void {
    this.authError.set(null);
    this.authStep.set('email');
    this.authOpen.set(true);
    this.sidebarOpen.set(false);
    this.api.authChallenge().subscribe({
      next: (r) => { this.authCid = r.id; this.authQ.set(r.q); },
      error: () => this.authError.set('Could not start sign-in. Try again.'),
    });
  }

  requestCode(): void {
    const email = this.authEmail.trim();
    if (!email || this.authBusy()) return;
    this.authBusy.set(true);
    this.authError.set(null);
    this.api.authRequestCode(email, this.authCid, this.authAns.trim()).subscribe({
      next: () => { this.authBusy.set(false); this.authStep.set('code'); },
      error: (e) => {
        this.authBusy.set(false);
        this.authError.set(e?.error?.error || 'Could not send the code. Try again.');
        this.api.authChallenge().subscribe({ next: (r) => { this.authCid = r.id; this.authQ.set(r.q); }, error: () => {} });
      },
    });
  }

  verifyCode(): void {
    const code = this.authCode.trim();
    if (!code || this.authBusy()) return;
    this.authBusy.set(true);
    this.authError.set(null);
    this.api.authVerify(this.authEmail.trim(), code).subscribe({
      next: (r) => {
        this.authBusy.set(false);
        this.userEmail.set(r.email);
        this.authOpen.set(false);
        this.authEmail = ''; this.authAns = ''; this.authCode = '';
        this.refresh();
      },
      error: (e) => {
        this.authBusy.set(false);
        this.authError.set(e?.error?.error || 'Could not verify the code.');
      },
    });
  }

  logout(): void {
    this.api.authLogout().subscribe({ next: () => { this.userEmail.set(null); this.refresh(); }, error: () => {} });
  }


  openPanel(p: 'how' | 'donate'): void {
    this.panel.set(p);
    this.sidebarOpen.set(false);
  }

  refresh(): void {
    this.api.listTasks().subscribe({
      next: (r) => {
        this.active.set(r.active || []);
        this.archived.set(r.archived || []);
      },
      error: () => {},
    });
  }

  openTask(t: Task): void {
    this.sidebarOpen.set(false);
    this.task.set(t);
    this.error.set(null);
    this.api.getTask(t.id).subscribe({
      next: (r) => this.messages.set(r.messages || []),
      error: () => this.error.set('Could not load this task.'),
    });
  }

  newTask(): void {
    this.api.createTask('New task').subscribe({
      next: (r) => {
        this.refresh();
        this.openTask({ id: r.id, title: r.title, status: 'active' });
      },
      error: () => this.error.set('Could not create a task.'),
    });
  }

  toggleDone(): void {
    const t = this.task();
    if (!t) return;
    this.api.toggleDone(t.id).subscribe({
      next: (r) => {
        this.task.update((cur) => (cur ? { ...cur, status: r.status } : cur));
        this.refresh();
      },
      error: () => this.error.set('Could not update the task.'),
    });
  }

  send(): void {
    const text = this.input.trim();
    if (!text || this.busy()) return;
    const t = this.task();
    if (!t) {
      this.busy.set(true);
      this.api.createTask(text.slice(0, 60)).subscribe({
        next: (r) => {
          const nt: Task = { id: r.id, title: r.title, status: 'active' };
          this.task.set(nt);
          this.messages.set([]);
          this.refresh();
          this.ask(text, nt.id);
        },
        error: () => {
          this.busy.set(false);
          this.error.set('Could not create a task.');
        },
      });
      return;
    }
    this.ask(text, t.id);
  }

  queueAhead = signal(0);
  readingSource = signal(false);
  private pollQueue(): void {
    this.queueAhead.set(0);
    const t = setInterval(() => {
      if (!this.waiting()) { clearInterval(t); this.queueAhead.set(0); this.readingSource.set(false); return; }
      this.api.queue().subscribe({ next: (r) => { this.queueAhead.set(r.ahead || 0); this.readingSource.set(!!r.reading); }, error: () => {} });
    }, 2500);
  }
  private ask(text: string, taskId: string): void {
    this.busy.set(true);
    this.waiting.set(true);
    this.pollQueue();
    this.input = '';
    setTimeout(() => this.resizeBox());
    this.atBottom = true; this.showJump.set(false); this.hasNew.set(false);
    this.error.set(null);
    this.messages.update((m) => [...m, { role: 'user', text }]);
    this.api.ask(text, taskId).subscribe({
      next: (r) => this.typeOut(r.answer, r.sources, r.not_found, r.source_ids, r.licences),
      error: (e) => {
        this.busy.set(false);
        this.waiting.set(false);
        this.error.set(
          e?.error?.error ||
            'The assistant could not answer. It may be busy or rate-limited - try again in a moment.'
        );
      },
    });
  }

  /** Client-side typewriter: the full answer is already here; reveal it quickly,
   *  then show sources and the refusal box at the end. The server answer is unchanged. */
  private typeOut(full: string, sources: string[], notFound: boolean, sourceIds: string[] = [], licences: string[] = []): void {
    this.waiting.set(false);
    const finish = () => {
      this.messages.update((m) => [...m.slice(0, -1), { role: 'assistant', text: full, sources, source_ids: sourceIds, licences, not_found: notFound }]);
      this.busy.set(false);
    };
    const reduce = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduce || !full) { this.messages.update((m) => [...m, { role: 'assistant', text: '' }]); finish(); return; }
    this.messages.update((m) => [...m, { role: 'assistant', text: '' }]);
    const tickMs = 20;
    const step = Math.max(1, Math.ceil(full.length / (2500 / tickMs)));
    let i = 0;
    const timer = setInterval(() => {
      i = Math.min(full.length, i + step);
      if (i >= full.length) { clearInterval(timer); finish(); return; }
      this.messages.update((m) => [...m.slice(0, -1), { role: 'assistant', text: full.slice(0, i) }]);
    }, tickMs);
  }

  onKeydown(ev: KeyboardEvent): void {
    if (ev.key === 'Enter' && !ev.shiftKey) {
      ev.preventDefault();
      this.send();
    }
  }
}
