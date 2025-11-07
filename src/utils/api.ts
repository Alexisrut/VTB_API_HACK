import axios from "axios";
import { getCookie, setCookie } from "./cookies";


export interface RegisterData {
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
}


const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
});

// для автоматического добавления Access Token
api.interceptors.request.use((config) => {
  const token = getCookie("access_token");
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// для автоматического обновления токена
api.interceptors.response.use(
  (response: any) => response,
  async (error: { config: any; response: { status: number; }; }) => {
    const originalRequest = error.config;
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      const refreshToken = getCookie("refresh_token");

      if (refreshToken) {
        try {
          const { data } = await axios.post<TokenResponse>(
            `${API_URL}/auth/refresh`,
            { refresh_token: refreshToken }
          );
          setCookie("access_token", data.access_token, 15 / (24 * 60)); // 15 минут
          setCookie("refresh_token", data.refresh_token, 7); // 7 дней
          axios.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          console.error("Refresh token failed", refreshError);
          // TODO: Очистить куки и сделать редирект на логин
          return Promise.reject(refreshError);
        }
      }
    }
    return Promise.reject(error);
  }
);



export const register = (data: RegisterData) => {
  console.log("api: send register request: ", data)
  return api.post<UserResponse>("/auth/register", data);
};


export const verifySms = (phone_number: string, code: string) => {
  return api.post("/auth/verify-sms", { phone_number, code });
};

export const login = (email: string, password: string) => {
  return api.post<TokenResponse>("/auth/login", { email, password });
};

export const getMe = () => {
  return api.get<UserResponse>("/users/me");
};

export const startBankOAuth = () => {
  // Просто перенаправляем пользователя на эндпоинт нашего бэкенда
  window.location.href = `${API_URL}/auth/oauth/authorize`;
};