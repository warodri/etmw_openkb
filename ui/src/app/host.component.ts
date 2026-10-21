import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from './theme.service';

@Component({
  selector: 'app-host',
  imports: [RouterLink],
  templateUrl: './host.component.html',
  styleUrl: './host.component.css',
})
export class HostComponent {
  protected theme = inject(ThemeService);
}
