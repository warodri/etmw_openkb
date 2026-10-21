import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ThemeService } from './theme.service';

@Component({
  selector: 'app-agent',
  imports: [RouterLink],
  templateUrl: './agent.component.html',
  styleUrl: './host.component.css',
})
export class AgentComponent {
  protected theme = inject(ThemeService);
}
