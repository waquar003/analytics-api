import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { Observable } from 'rxjs';

export interface Project {
  id: string;
  name: string;
  public_api_key: string;
  secret_api_key: string;
  allowed_origins: string[] | null;
}

@Injectable({
  providedIn: 'root',
})
export class ProjectService {
  private http = inject(HttpClient);
  private readonly API_URL = `${environment.apiUrl}/projects`;

  getProjects(): Observable<Project[]> {
    return this.http.get<Project[]>(`${this.API_URL}/all`);
  }

  createProject(name: string): Observable<Project> {
    return this.http.post<Project>(this.API_URL, { name })
  }

  regenerateKey(projectId: string): Observable<Project> {
    return this.http.post<Project>(`${this.API_URL}/${projectId}/regenerate-key`, {});
  }

  registerEvent(projectId: string, eventName: string): Observable<any> {
    return this.http.post(`${this.API_URL}/${projectId}/events`, { event_name: eventName })
  }

  updateWhitelist(projectId: string, domains: string[]): Observable<Project> {
    return this.http.patch<Project>(`${this.API_URL}/${projectId}/whitelist`, domains)
  }

  getRegisteredEvents(projectId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.API_URL}/${projectId}/events`);
  }

  deleteEvent(projectId: string, eventId: string): Observable<void> {
    return this.http.delete<void>(`${this.API_URL}/${projectId}/events/${eventId}`)
  }
}
