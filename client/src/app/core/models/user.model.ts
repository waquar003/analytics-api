export interface UserRead {
  id: string; 
  email: string;
  full_name?: string;
  created_at: string;
}

export interface UserCreate {
  email: string;
  password?: string;
  full_name?: string;
}