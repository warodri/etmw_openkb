import { Routes } from '@angular/router';
import { ChatComponent } from './chat.component';
import { HostComponent } from './host.component';
import { HowComponent } from './how.component';
import { DonateComponent } from './donate.component';
import { AgentComponent } from './agent.component';
import { ReportComponent } from './report.component';

export const routes: Routes = [
  { path: '', component: ChatComponent, pathMatch: 'full' },
  { path: 'host', component: HostComponent },
  { path: 'how', component: HowComponent },
  { path: 'donate', component: DonateComponent },
  { path: 'agent', component: AgentComponent },
  { path: 'report', component: ReportComponent },
];
