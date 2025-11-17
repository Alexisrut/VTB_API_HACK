import { useState, useEffect } from "react";
import { getCookie, eraseCookie } from "../utils/cookies";
import { getMe, type UserResponse } from "../utils/api";
import type { AxiosError } from "axios";

export const useAuth = () => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      const token = getCookie("access_token");
      if (!token) {
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      try {
        const { data } = await getMe();
        setUser(data);
        setIsAuthenticated(true);
        setError(null);
      } catch (err) {
        const axiosErr = err as AxiosError;

        // Сохраняем ошибку
        setError(axiosErr.response?.data as string ?? axiosErr.message);

        if (axiosErr.response?.status === 401 || axiosErr.response?.status === 403) {
          console.log("Token invalid or expired, clearing auth state");
          eraseCookie("access_token");
        }

        setIsAuthenticated(false);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const refetch = async () => {
    const token = getCookie("access_token");
    if (!token) {
      setUser(null);
      setIsAuthenticated(false);
      setError("No token");
      return;
    }

    try {
      const { data } = await getMe();
      setUser(data);
      setIsAuthenticated(true);
      setError(null);
    } catch (err) {
      const axiosErr = err as AxiosError;
      setError(axiosErr.response?.data as string ?? axiosErr.message);
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  return { user, isLoading, isAuthenticated, error, refetch };
};
