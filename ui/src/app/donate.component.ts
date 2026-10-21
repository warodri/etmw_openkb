import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from './theme.service';

@Component({
  selector: 'app-donate',
  imports: [RouterLink],
  templateUrl: './donate.component.html',
  styleUrl: './host.component.css',
})
export class DonateComponent {
  protected theme = inject(ThemeService);
}
