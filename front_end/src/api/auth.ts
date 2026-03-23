import request from './request';

export interface User {
  id: string;
  username: string;
  display_name: string;
  role: 'admin' | 'operator';
  mailbox_scope_ids: string[] | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export const authApi = {
  login: (data: Record<string, string>) => {
    return request.post<unknown, LoginResponse>('/auth/login', data);
  },
  getMe: () => {
    return request.get<unknown, User>('/auth/me');
  },
};
