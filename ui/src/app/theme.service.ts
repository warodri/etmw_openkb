import { Injectable, signal } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly dark = signal(false);

  toggle(): void {
    const next = !this.dark();
    this.dark.set(next);
    document.documentElement.classList.toggle('dark', next);
  }
}
