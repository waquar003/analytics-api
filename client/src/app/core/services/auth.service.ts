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

  private readonly AUTH_URL = `${environment.apiUrl}/auth`

  currentUser = signal<UserRead | null>(null)
  
  signup(data: UserCreate): Observable<UserRead> {
    return this.http.post<UserRead>(`${this.AUTH_URL}/signup`, data);
  }

  login(data: UserCreate): Observable<UserRead> {
    return this.http.post<UserRead>(`${this.AUTH_URL}/login`, data).pipe(
      tap(res => {
        this.currentUser.set(res);
      })
    )
  }

  logout() {
    this.currentUser.set(null);
  }
}