import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { eraseCookie } from "../../utils/cookies";
import { logout, getUserBankUsers, saveBankUser, deleteBankUser } from "../../utils/api";
import Layout from "../../components/Layout";
import { Button } from "../../ui/button";
import { Input } from "../../ui/input";
import { Label } from "../../ui/label";
import { CircleUser, Mail, Phone, User, Building2, Save, Trash2 } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import styles from "./index.module.scss";

const bankNames: { [key: string]: string } = {
  vbank: "Virtual Bank",
  abank: "Awesome Bank",
  sbank: "Smart Bank",
};

export default function Profile() {
  const { user, isLoading } = useAuth();
  const navigate = useNavigate();
  const [bankUsers, setBankUsers] = useState<Record<string, string>>({});
  const [bankUserInputs, setBankUserInputs] = useState<Record<string, string>>({});
  const [isLoadingBankUsers, setIsLoadingBankUsers] = useState(true);
  const [saving, setSaving] = useState<Record<string, boolean>>({});

  const loadBankUsers = useCallback(async () => {
    try {
      setIsLoadingBankUsers(true);
      const response = await getUserBankUsers();
      setBankUsers(response.data.bank_users || {});
      // Инициализируем поля ввода текущими значениями
      setBankUserInputs(response.data.bank_users || {});
    } catch (error) {
      console.error("Error loading bank users:", error);
    } finally {
      setIsLoadingBankUsers(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadBankUsers();
    }
  }, [user, loadBankUsers]);

  const handleSaveBankUser = async (bankCode: string) => {
    const bankUserId = bankUserInputs[bankCode]?.trim();
    if (!bankUserId) {
      alert("Пожалуйста, введите ID пользователя в банке");
      return;
    }

    try {
      setSaving((prev) => ({ ...prev, [bankCode]: true }));
      await saveBankUser({ bank_code: bankCode, bank_user_id: bankUserId });
      setBankUsers((prev) => ({ ...prev, [bankCode]: bankUserId }));
      alert(`ID пользователя для ${bankNames[bankCode]} успешно сохранен`);
    } catch (error: any) {
      console.error("Error saving bank user:", error);
      alert(error.response?.data?.detail || "Ошибка при сохранении ID пользователя");
    } finally {
      setSaving((prev) => ({ ...prev, [bankCode]: false }));
    }
  };

  const handleDeleteBankUser = async (bankCode: string) => {
    if (!confirm(`Удалить ID пользователя для ${bankNames[bankCode]}?`)) {
      return;
    }

    try {
      await deleteBankUser(bankCode);
      setBankUsers((prev) => {
        const newBankUsers = { ...prev };
        delete newBankUsers[bankCode];
        return newBankUsers;
      });
      setBankUserInputs((prev) => {
        const newInputs = { ...prev };
        delete newInputs[bankCode];
        return newInputs;
      });
      alert(`ID пользователя для ${bankNames[bankCode]} удален`);
    } catch (error: any) {
      console.error("Error deleting bank user:", error);
      alert(error.response?.data?.detail || "Ошибка при удалении ID пользователя");
    }
  };

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

          {/* Bank Users Section */}
          <div className={styles.consentsSection}>
            <h2 className={styles.sectionTitle}>ID пользователей в банках</h2>
            <p className={styles.sectionDescription}>
              Введите ваш ID пользователя для каждого банка. После этого вы сможете получать данные о счетах и транзакциях.
            </p>
            
            {isLoadingBankUsers ? (
              <div className={styles.loading}>Загрузка...</div>
            ) : (
              <div className={styles.consentsList}>
                {(["vbank", "abank", "sbank"] as const).map((bankCode) => (
                  <div key={bankCode} className={styles.consentItem}>
                    <div className={styles.consentHeader}>
                      <div className={styles.consentIcon}>
                        <Building2 size={20} />
                      </div>
                      <Label htmlFor={`bank-user-${bankCode}`} className={styles.consentLabel}>
                        {bankNames[bankCode]}
                      </Label>
                    </div>
                    <div className={styles.consentInputGroup}>
                      <Input
                        id={`bank-user-${bankCode}`}
                        type="text"
                        placeholder="Введите ваш ID в банке"
                        value={bankUserInputs[bankCode] || ""}
                        onChange={(e) =>
                          setBankUserInputs((prev) => ({
                            ...prev,
                            [bankCode]: e.target.value,
                          }))
                        }
                        className={styles.consentInput}
                      />
                      <div className={styles.consentActions}>
                        <Button
                          size="sm"
                          onClick={() => handleSaveBankUser(bankCode)}
                          disabled={saving[bankCode]}
                          className={styles.saveButton}
                        >
                          <Save size={16} />
                          {saving[bankCode] ? "Сохранение..." : "Сохранить"}
                        </Button>
                        {bankUsers[bankCode] && (
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => handleDeleteBankUser(bankCode)}
                            className={styles.deleteButton}
                          >
                            <Trash2 size={16} />
                          </Button>
                        )}
                      </div>
                    </div>
                    {bankUsers[bankCode] && (
                      <div className={styles.consentSaved}>
                        Сохранен: {bankUsers[bankCode]}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
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

