import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { eraseCookie } from "../../utils/cookies";
import { logout } from "../../utils/api";
import Layout from "../../components/Layout";
import { Button } from "../../ui/button";
import { CircleUser, Mail, Phone, User } from "lucide-react";
import styles from "./index.module.scss";

export default function Profile() {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    eraseCookie("access_token");
    eraseCookie("refresh_token");
    logout();
    navigate("/");
    window.location.reload();
  };

  if (isLoading) {
    return (
      <Layout>
        <div className={styles.profileContainer}>
          <div className={styles.loading}>Загрузка...</div>
        </div>
      </Layout>
    );
  }

  if (!user) {
    return (
      <Layout>
        <div className={styles.profileContainer}>
          <div className={styles.error}>Пользователь не найден</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className={styles.profileContainer}>
        <div className={styles.profileCard}>
          <div className={styles.profileHeader}>
            <div className={styles.avatar}>
              <CircleUser size={64} />
            </div>
            <h1 className={styles.profileName}>
              {user.first_name} {user.last_name}
            </h1>
          </div>

          <div className={styles.profileInfo}>
            <div className={styles.infoItem}>
              <div className={styles.infoIcon}>
                <Mail size={20} />
              </div>
              <div className={styles.infoContent}>
                <div className={styles.infoLabel}>Email</div>
                <div className={styles.infoValue}>{user.email}</div>
              </div>
            </div>

            <div className={styles.infoItem}>
              <div className={styles.infoIcon}>
                <Phone size={20} />
              </div>
              <div className={styles.infoContent}>
                <div className={styles.infoLabel}>Телефон</div>
                <div className={styles.infoValue}>{user.phone_number}</div>
              </div>
            </div>

            <div className={styles.infoItem}>
              <div className={styles.infoIcon}>
                <User size={20} />
              </div>
              <div className={styles.infoContent}>
                <div className={styles.infoLabel}>Статус</div>
                <div className={styles.infoValue}>
                  {user.is_active ? "Активен" : "Неактивен"}
                </div>
              </div>
            </div>
          </div>

          <div className={styles.profileActions}>
            <Button
              variant="destructive"
              size="lg"
              onClick={handleLogout}
              className={styles.logoutButton}
            >
              Выйти
            </Button>
          </div>
        </div>
      </div>
    </Layout>
  );
}

