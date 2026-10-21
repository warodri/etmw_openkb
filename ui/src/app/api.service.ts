import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Task {
  id: string;
  title: string;
  status: string;
  created_at?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  text: string;
  sources?: string[];
  not_found?: boolean;
  ts?: string;
}

export interface TaskList {
  active: Task[];
  archived: Task[];
}

export interface TaskDetail {
  task: Task;
  messages: ChatMessage[];
}

export interface AskResponse {
  answer: string;
  sources: string[];
  not_found: boolean;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);

  authMe() { return this.http.get<{ email: string | null }>('/api/auth/me'); }
  authChallenge() { return this.http.get<{ id: string; q: string }>('/api/auth/challenge'); }
  authRequestCode(email: string, cid: string, ans: string) {
    return this.http.post<{ sent: boolean }>('/api/auth/request-code', { email, cid, ans });
  }
  authVerify(email: string, code: string) {
    return this.http.post<{ ok: boolean; email: string }>('/api/auth/verify', { email, code });
  }
  authLogout() { return this.http.post<{ ok: boolean }>('/api/auth/logout', {}); }

  listTasks(): Observable<TaskList> {
    return this.http.get<TaskList>('/api/tasks');
  }

  getTask(id: string): Observable<TaskDetail> {
    return this.http.get<TaskDetail>(`/api/tasks/${id}`);
  }

  createTask(title: string): Observable<{ id: string; title: string }> {
    return this.http.post<{ id: string; title: string }>('/api/tasks', { title });
  }

  toggleDone(id: string): Observable<{ id: string; status: string }> {
    return this.http.post<{ id: string; status: string }>(`/api/tasks/${id}/done`, {});
  }

  ask(q: string, taskId: string): Observable<AskResponse> {
    return this.http.post<AskResponse>('/ask', { q, task_id: taskId });
  }
}
