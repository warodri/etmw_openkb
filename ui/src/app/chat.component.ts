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
  error = signal<string | null>(null);
  panel = signal<'how' | 'donate' | null>(null);
  showArchived = signal(false);
  sidebarOpen = signal(false);
  input = '';

  ngOnInit(): void {
    this.refresh();
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
    this.input = '';
    this.error.set(null);
    this.messages.update((m) => [...m, { role: 'user', text }]);
    this.api.ask(text, taskId).subscribe({
      next: (r) => {
        this.messages.update((m) => [
          ...m,
          { role: 'assistant', text: r.answer, sources: r.sources, not_found: r.not_found },
        ]);
        this.busy.set(false);
      },
      error: (e) => {
        this.busy.set(false);
        this.error.set(
          e?.error?.error ||
            'The assistant could not answer. It may be busy or rate-limited - try again in a moment.'
        );
      },
    });
  }

  onKeydown(ev: KeyboardEvent): void {
    if (ev.key === 'Enter' && !ev.shiftKey) {
      ev.preventDefault();
      this.send();
    }
  }
}
