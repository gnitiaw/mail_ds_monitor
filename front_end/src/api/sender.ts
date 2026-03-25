import request from './request';
import type { PaginatedData, SenderCandidate, SenderProfile } from './types';

export const senderApi = {
  getCandidates: (params?: Record<string, unknown>) => {
    return request.get<unknown, PaginatedData<SenderCandidate>>('/sender-profiles/candidates', { params });
  },

  getProfiles: (params?: Record<string, unknown>) => {
    return request.get<unknown, PaginatedData<SenderProfile>>('/sender-profiles', { params });
  },

  createProfile: (data: Partial<SenderProfile>) => {
    return request.post<unknown, SenderProfile>('/sender-profiles', data);
  },

  updateProfile: (profileId: string, data: Partial<SenderProfile>) => {
    return request.put<unknown, SenderProfile>(`/sender-profiles/${profileId}`, data);
  }
};
