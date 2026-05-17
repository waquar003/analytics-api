import { Component, inject } from '@angular/core';
import { AuthService } from '../../../core/services/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-logout',
  imports: [],
  templateUrl: './logout.html',
  styleUrl: './logout.scss',
})
export class Logout {
  private auth = inject(AuthService);
  private router = inject(Router)

  ngOnInit() {
    this.auth.logout();
    this.router.navigate(['/'])
  }
}
