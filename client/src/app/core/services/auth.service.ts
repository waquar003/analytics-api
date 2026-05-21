import { HttpClient } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';
import { UserCreate, UserRead } from '../models/user.model';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  constructor(
    private http: HttpClient,
    private router: Router
  ) {}

  private readonly AUTH_URL = `${environment.adminApiUrl}/auth`

  accessToken = signal<string | null>(null)
  currentUser = signal<UserRead | null>(null)
  
  signup(data: UserCreate): Observable<UserRead> {
    return this.http.post<UserRead>(`${this.AUTH_URL}/signup`, data);
  }

  login(data: UserCreate): Observable<any> {
    return this.http.post<any>(`${this.AUTH_URL}/login`, data, { withCredentials: true }).pipe(
      tap(res => {
        this.accessToken.set(res.access_token)
        this.currentUser.set(res);
      })
    )
  }

  refreshAccessToken(): Observable<{ access_token: string }> {
    return this.http.post<{ access_token: string }>(`${this.AUTH_URL}/refresh`, {}, { withCredentials: true }).pipe(
      tap(res => this.accessToken.set(res.access_token))
    )
  }

  logout() {
    this.http.post(`${this.AUTH_URL}/logout`, {}, { withCredentials: true }).subscribe({
      next: () => this.clearSessionState(),
      error: () => this.clearSessionState()
    })
  }

  private clearSessionState() {
    this.accessToken.set(null)
    this.currentUser.set(null)
    this.router.navigate(['/login'])
  }
}