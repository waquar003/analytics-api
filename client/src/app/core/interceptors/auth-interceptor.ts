import { HttpInterceptorFn } from '@angular/common/http';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const email = localStorage.getItem('x-user-email');
  const password = localStorage.getItem('x-user-password');

  let authReq = req;

  if (email && password) {
    authReq = req.clone({
      setHeaders: {
        'X-User-Email': email,
        'X-User-Password': password
      }
    })
  }
  return next(authReq);
};
