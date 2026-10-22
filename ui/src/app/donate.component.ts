import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from './theme.service';
import { ApiService } from './api.service';

@Component({
  selector: 'app-donate',
  imports: [RouterLink],
  templateUrl: './donate.component.html',
  styleUrl: './host.component.css',
})
export class DonateComponent implements OnInit {
  protected theme = inject(ThemeService);
  private api = inject(ApiService);

  tester = signal(false);
  stage = signal<'form' | 'converting' | 'preview' | 'submitting' | 'published' | 'rejected' | 'error'>('form');
  fileName = signal('');
  title = signal('');
  credit = signal('');
  licence = signal('CC BY-SA 4.0');
  sourceUrl = signal('');
  text = signal('');
  d1 = signal(false); d2 = signal(false); d3 = signal(false);
  reasons = signal<string[]>([]);
  note = signal('');
  readonly licences = ['CC BY-SA 4.0', 'CC BY 4.0', 'CC0', 'Public domain', 'MIT', 'Apache-2.0', 'BSD'];
  private timer: ReturnType<typeof setInterval> | null = null;

  ngOnInit(): void {
    this.api.canUpload().subscribe({ next: (r) => this.tester.set(!!r.open), error: () => this.tester.set(false) });
  }

  pick(ev: Event): void {
    const f = (ev.target as HTMLInputElement).files?.[0];
    if (!f) return;
    this.fileName.set(f.name);
    if (!this.title()) this.title.set(f.name.replace(/\.[^.]+$/, ''));
    this.stage.set('converting'); this.note.set('Converting the file. Books can take a few minutes.');
    this.api.convertFile(f).subscribe({
      next: (r) => this.poll(r.job, 'convert'),
      error: (e) => { this.stage.set('error'); this.reasons.set([e?.error?.error || 'Could not upload the file.']); },
    });
  }

  private poll(job: string, kind: 'convert' | 'submit'): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = setInterval(() => {
      this.api.job(job).subscribe({
        next: (j) => {
          if (j.status === 'converting' || j.status === 'processing') return;
          clearInterval(this.timer!); this.timer = null;
          if (kind === 'convert') {
            if (j.status === 'ready') { this.text.set(j.text || ''); this.stage.set('preview'); }
            else { this.stage.set('error'); this.reasons.set(j.reasons || ['Conversion failed.']); }
          } else {
            this.reasons.set(j.reasons || []);
            this.stage.set(j.status === 'published' ? 'published' : j.status === 'rejected' ? 'rejected' : 'error');
          }
        },
        error: () => { clearInterval(this.timer!); this.timer = null; this.stage.set('error'); this.reasons.set(['Lost the connection. Check the library before trying again.']); },
      });
    }, 2500);
  }

  get ready(): boolean { return !!this.title().trim() && this.text().trim().length > 0 && this.d1() && this.d2() && this.d3(); }

  submit(): void {
    if (!this.ready) return;
    this.stage.set('submitting'); this.note.set('Checking and adding to the library.');
    this.api.uploadDoc({
      title: this.title(), text: this.text(), licence: this.licence(), source_url: this.sourceUrl(), credit: this.credit(),
      declarations: { own_or_licensed: this.d1(), ok_with_cc_by_sa: this.d2(), may_be_edited: this.d3() },
    }).subscribe({
      next: (r) => this.poll(r.job, 'submit'),
      error: (e) => { this.stage.set('error'); this.reasons.set([e?.error?.error || 'Could not submit.']); },
    });
  }

  reset(): void {
    this.stage.set('form'); this.fileName.set(''); this.title.set(''); this.text.set(''); this.credit.set('');
    this.sourceUrl.set(''); this.d1.set(false); this.d2.set(false); this.d3.set(false); this.reasons.set([]);
  }
}
