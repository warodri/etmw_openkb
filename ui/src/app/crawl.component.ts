import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from './theme.service';
import { ApiService, CrawlAccount } from './api.service';

@Component({
  selector: 'app-crawl',
  imports: [RouterLink],
  templateUrl: './crawl.component.html',
  styleUrl: './host.component.css',
})
export class CrawlComponent implements OnInit {
  protected theme = inject(ThemeService);
  private api = inject(ApiService);

  state = signal<'loading' | 'signin' | 'closed' | 'ready'>('loading');
  acct = signal<CrawlAccount | null>(null);
  licence = signal('CC BY-SA');
  terms = signal(false);
  label = signal('');
  msg = signal('');
  newKey = signal('');
  copied = signal(false);
  readonly licences = ['CC BY-SA', 'CC BY', 'CC0', 'Public domain', 'MIT', 'Apache-2.0', 'BSD'];

  ngOnInit(): void { this.load(); }

  load(): void {
    this.api.crawlAccount().subscribe({
      next: (a) => { this.acct.set(a); if (a.default_licence) this.licence.set(a.default_licence); this.state.set(a.allowed ? 'ready' : 'closed'); },
      error: (e) => this.state.set(e?.status === 401 ? 'signin' : 'closed'),
    });
  }

  activeKeys(): number { return (this.acct()?.keys || []).filter((k) => !k.revoked_at).length; }

  save(): void {
    this.msg.set('');
    this.api.crawlSetAccount(this.licence(), this.terms()).subscribe({
      next: () => { this.msg.set('Saved.'); this.load(); },
      error: (e) => this.msg.set((e?.error?.reasons || [e?.error?.error || 'Could not save.']).join(' ')),
    });
  }

  create(): void {
    this.msg.set(''); this.newKey.set(''); this.copied.set(false);
    this.api.crawlCreateKey(this.label()).subscribe({
      next: (r) => { this.newKey.set(r.key || ''); this.label.set(''); this.load(); },
      error: (e) => this.msg.set((e?.error?.reasons || [e?.error?.error || 'Could not create a key.']).join(' ')),
    });
  }

  revoke(id: string): void { this.api.crawlRevoke(id).subscribe({ next: () => this.load(), error: () => this.msg.set('Could not revoke the key.') }); }

  copy(): void { navigator.clipboard?.writeText(this.newKey()).then(() => this.copied.set(true)).catch(() => {}); }

  when(iso: string | null | undefined): string { return iso ? iso.slice(0, 16).replace('T', ' ') + ' UTC' : 'never'; }
}
