import { Routes } from '@angular/router';
import { ChatComponent } from './chat.component';
import { HostComponent } from './host.component';

export const routes: Routes = [
  { path: '', component: ChatComponent, pathMatch: 'full' },
  { path: 'host', component: HostComponent },
];
