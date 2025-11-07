import { useState, useEffect } from "react";
import { getCookie } from "../utils/cookies";
import { getMe, type UserResponse } from "../utils/api";

export const useAuth = () => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

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
      } catch (error) {
        console.error("Failed to get user:", error);
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
      return;
    }

    try {
      const { data } = await getMe();
      setUser(data);
      setIsAuthenticated(true);
    } catch (error) {
      console.error("Failed to refetch user:", error);
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  return { user, isLoading, isAuthenticated, refetch };
};

