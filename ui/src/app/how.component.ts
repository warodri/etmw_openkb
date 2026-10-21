import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from './theme.service';

@Component({
  selector: 'app-how',
  imports: [RouterLink],
  templateUrl: './how.component.html',
  styleUrl: './host.component.css',
})
export class HowComponent {
  protected theme = inject(ThemeService);
}
