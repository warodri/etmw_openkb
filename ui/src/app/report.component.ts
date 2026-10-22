import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from './theme.service';
import { ApiService } from './api.service';

@Component({
  selector: 'app-report',
  imports: [RouterLink],
  templateUrl: './report.component.html',
  styleUrl: './host.component.css',
})
export class ReportComponent {
  protected theme = inject(ThemeService);
  private api = inject(ApiService);
  what = signal('');
  reason = signal('copyright');
  details = signal('');
  email = signal('');
  state = signal<'idle' | 'sending' | 'done' | 'error'>('idle');
  msg = signal('');
  readonly reasons = [
    { v: 'copyright', t: 'It is copyrighted and should not be here' },
    { v: 'personal-data', t: 'It has personal or private information' },
    { v: 'harmful', t: 'It is harmful or illegal' },
    { v: 'quality', t: 'It is wrong or low quality' },
    { v: 'other', t: 'Something else' },
  ];
  send(): void {
    if (this.state() === 'sending') return;
    this.state.set('sending'); this.msg.set('');
    const d = ('Document or link: ' + this.what() + '\n' + this.details()).slice(0, 1900);
    this.api.report('general', this.reason(), d, this.email()).subscribe({
      next: (r) => { this.state.set('done'); this.msg.set(r.id); },
      error: (e) => { this.state.set('error'); this.msg.set(e?.error?.error || 'Could not send the report. Try again in a moment.'); },
    });
  }
}
