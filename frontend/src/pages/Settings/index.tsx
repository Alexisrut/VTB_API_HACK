import Layout from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Settings as SettingsIcon } from "lucide-react";
import styles from "./index.module.scss";
import { useMe } from "../../hooks/context";

export default function Settings() {
  const me = useMe();

  if (!me) {
    return (
      <Layout>
        <Card>
          <CardHeader>
            <CardTitle>Настройки</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Войдите, чтобы изменить настройки</p>
          </CardContent>
        </Card>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className={styles.container}>
        <div className={styles.header}>
          <h1>Настройки</h1>
          <p>Управление настройками приложения</p>
        </div>

        <Card>
          <CardHeader>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
              <SettingsIcon className={styles.icon} />
              <CardTitle>Настройки профиля</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <p style={{ color: "#6b7280" }}>
              Настройки профиля доступны на странице{" "}
              <a href="/profile" style={{ color: "var(--primary)", textDecoration: "underline" }}>
                Профиль
              </a>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Уведомления</CardTitle>
          </CardHeader>
          <CardContent>
            <p style={{ color: "#6b7280" }}>Настройки уведомлений будут доступны в будущих версиях</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Интеграции</CardTitle>
          </CardHeader>
          <CardContent>
            <p style={{ color: "#6b7280" }}>
              Управление банковскими интеграциями доступно на странице{" "}
              <a href="/profile" style={{ color: "var(--primary)", textDecoration: "underline" }}>
                Профиль
              </a>
            </p>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}

