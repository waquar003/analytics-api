import { Routes } from '@angular/router';
import { Landing } from './features/landing/landing';
import { Signup } from './features/auth/signup/signup';
import { Login } from './features/auth/login/login';
import { Logout } from './features/auth/logout/logout';
import { Dashboard } from './features/dashboard/dashboard';

export const routes: Routes = [
    { path: '', component: Landing },
    { path: 'signup', component: Signup },
    { path: 'login', component: Login },
    { path: 'logout', component: Logout },
    { path: 'dashboard', component: Dashboard },
    // { path: '**', redirectTo: '' }
];
