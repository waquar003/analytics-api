import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { Router, RouterLink } from '@angular/router';

@Component({
  selector: 'app-signup',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './signup.html',
  styleUrl: './signup.scss',
})
export class Signup {
  private fb = inject(FormBuilder)
  private auth = inject(AuthService)
  private router = inject(Router)

  form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    full_name: [''],
    password: ['', [Validators.required, Validators.minLength(6)]]
  });

  onSubmit() {
  if (this.form.valid) {
    this.auth.signup(this.form.value as any).subscribe({
      next: (response) => {
        console.log('User created:', response);
        alert('Account created successfully! Redirecting to login...');
        this.router.navigate(['/login']);
      },
      error: (err) => {
        // Log the full error to the console to see what the server actually sent
        console.error('Signup Error:', err);

        // Safely extract the error message from FastAPI
        // FastAPI typically returns { "detail": "message" }
        const errorMessage = err.error?.detail || 'Server unreachable or connection refused.';
        
        // If 'detail' is an array (FastAPI validation error), handle that too
        const finalMessage = Array.isArray(errorMessage) 
          ? errorMessage[0].msg 
          : errorMessage;

        alert(finalMessage);
      }
    });
  }
}
}
