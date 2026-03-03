export interface UserInfo {
    id: string;
    username: string;
    email?: string;
  }
  
  export interface LoginRequest {
    username: string;
    password: string;
  }
  
  export interface RegisterRequest {
    username: string;
    password: string;
    confirmPassword: string;
  }
  
  export interface LoginResponse {
    token: string;
    user: UserInfo;
  }