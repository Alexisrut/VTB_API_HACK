import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { setCookie } from "../../utils/cookies";
import { toast } from "sonner";
import Layout from "../../components/Layout";
import styles from "./OAuthSuccess.module.scss";

export default function OAuthSuccess() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (accessToken && refreshToken) {
      // Set tokens
      setCookie("access_token", accessToken, 15 / (24 * 60));
      setCookie("refresh_token", refreshToken, 7);

      toast.success("Успешный вход через банк!", {
        description: "Добро пожаловать!",
        duration: 1500,
      });

      // Redirect to home page
      setTimeout(() => {
        window.location.href = "/";
      }, 1000);
    } else {
      toast.error("Ошибка авторизации", {
        description: "Не удалось получить токены",
        duration: 1500,
      });

      setTimeout(() => {
        navigate("/");
      }, 2000);
    }
  }, [searchParams, navigate]);

  return (
    <Layout>
      <div className={styles.container}>
        <div className={styles.content}>
          <h1>Завершение входа...</h1>
          <p>Пожалуйста, подождите</p>
        </div>
      </div>
    </Layout>
  );
}

