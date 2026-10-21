import { Component, OnInit, inject, signal } from '@angular/core';
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
  error = signal<string | null>(null);
  panel = signal<'how' | 'donate' | null>(null);
  showArchived = signal(false);
  sidebarOpen = signal(false);
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

  ngOnInit(): void {
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

  private ask(text: string, taskId: string): void {
    this.busy.set(true);
    this.waiting.set(true);
    this.input = '';
    this.error.set(null);
    this.messages.update((m) => [...m, { role: 'user', text }]);
    this.api.ask(text, taskId).subscribe({
      next: (r) => this.typeOut(r.answer, r.sources, r.not_found),
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
  private typeOut(full: string, sources: string[], notFound: boolean): void {
    this.waiting.set(false);
    const finish = () => {
      this.messages.update((m) => [...m.slice(0, -1), { role: 'assistant', text: full, sources, not_found: notFound }]);
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
