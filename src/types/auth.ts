export interface UserInfo {
  id: string;
  username: string;
  email?: string;
  roleId?: number;
  roleName?: string;
  avatarUrl?: string | null;
}
  
  export interface LoginRequest {
    username: string;
    password: string;
  }
  
  export interface RegisterRequest {
    username: string;
    password: string;
    confirmPassword: string;
    email?: string;
    emailCode?: string;
  }
  
  export interface LoginResponse {
    token: string;
    user: UserInfo;
  }