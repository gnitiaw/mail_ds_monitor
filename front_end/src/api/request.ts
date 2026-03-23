import axios from 'axios';
import { message } from 'antd';
import type { BaseResponse } from './types';

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
});

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

request.interceptors.response.use(
  (response) => {
    const res = response.data as BaseResponse<any>;
    
    // 严格校验响应格式是否包含 code
    if (res && typeof res.code === 'number') {
      // code 为 0 或 200 视为业务成功
      if (res.code === 0 || res.code === 200) {
        return res.data;
      }
      
      // 业务失败
      const errorMsg = res.message || '业务处理失败';
      message.error(errorMsg);
      return Promise.reject(new Error(errorMsg));
    }

    // 不符合契约的响应结构
    const formatError = '接口响应格式错误';
    message.error(formatError);
    return Promise.reject(new Error(formatError));
  },
  (error) => {
    if (error.response?.status === 401 || error.response?.data?.code === 40101) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    
    // 统一错误处理
    const errorMsg = error.response?.data?.message || error.message || '系统异常';
    message.error(errorMsg);
    return Promise.reject(error);
  }
);

export default request;
