import { useNavigate } from "react-router-dom";
import { eraseCookie, setCookie } from "../../utils/cookies";
import { logout, getUserBankUsers, saveBankUser, deleteBankUser, createAccountConsent, getUserConsents, getConsentDetails, type BankConsent } from "../../utils/api";
import Layout from "../../components/Layout";
import { Button } from "../../ui/button";
import { Input } from "../../ui/input";
import { Label } from "../../ui/label";
import { CircleUser, Mail, Phone, Building2, Save, Trash2, Shield, CheckCircle2, RefreshCw } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import styles from "./index.module.scss";
import { useMe } from "../../hooks/context";
import { useBankData } from "../../hooks/BankDataContext";

const bankNames: { [key: string]: string } = {
  vbank: "Virtual Bank",
  abank: "Awesome Bank",
  sbank: "Smart Bank",
};

export default function Profile() {
  const me = useMe();
  const { refreshData: refreshBankData } = useBankData();
  const navigate = useNavigate();
  const [bankUsers, setBankUsers] = useState<Record<string, string>>({});
  const [bankUserInputs, setBankUserInputs] = useState<Record<string, string>>({});
  const [isLoadingBankUsers, setIsLoadingBankUsers] = useState(true);
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [consents, setConsents] = useState<Record<string, BankConsent>>({});
  const [isLoadingConsents, setIsLoadingConsents] = useState(true);
  const [creatingConsent, setCreatingConsent] = useState<Record<string, boolean>>({});
  const [pollingConsent, setPollingConsent] = useState<Record<string, boolean>>({});

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

  const loadConsents = useCallback(async () => {
    try {
      setIsLoadingConsents(true);
      const response = await getUserConsents();
      const consentsMap: Record<string, BankConsent> = {};
      (response.data.consents || []).forEach((consent: BankConsent) => {
        consentsMap[consent.bank_code] = consent;
        // Сохраняем согласие в куки для использования в других запросах
        setCookie(`consent_${consent.bank_code}`, consent.consent_id, 365);
      });
      setConsents(consentsMap);
    } catch (error) {
      console.error("Error loading consents:", error);
    } finally {
      setIsLoadingConsents(false);
    }
  }, []);

  useEffect(() => {
    if (me) {
      loadBankUsers();
      loadConsents();
    }
  }, [me, loadBankUsers, loadConsents]);

  const handleSaveBankUser = async (bankCode: string) => {
    const bankUserId = bankUserInputs[bankCode]?.trim();
    if (!bankUserId) {
      toast.error("Введите ID пользователя", {
        description: "Поле не может быть пустым",
        duration: 1500,
      });
      return;
    }

    try {
      setSaving((prev) => ({ ...prev, [bankCode]: true }));
      await saveBankUser({ bank_code: bankCode, bank_user_id: bankUserId });
      setBankUsers((prev) => ({ ...prev, [bankCode]: bankUserId }));
      toast.success(`ID пользователя для ${bankNames[bankCode]} сохранен`, {
        description: "Банковская интеграция настроена",
        duration: 1500,
      });
    } catch (error: any) {
      console.error("Error saving bank me:", error);
      
      // Handle different error response formats
      let errorMessage = "Ошибка при сохранении ID пользователя";
      const errorDetail = error.response?.data?.detail;
      
      if (errorDetail) {
        if (typeof errorDetail === "string") {
          errorMessage = errorDetail;
        } else if (typeof errorDetail === "object") {
          // Handle object format: {error, message, bank_code}
          errorMessage = errorDetail.message || errorDetail.error || JSON.stringify(errorDetail);
        } else if (Array.isArray(errorDetail)) {
          // Handle validation errors array
          errorMessage = errorDetail.map((err: any) => 
            err.msg || err.message || JSON.stringify(err)
          ).join(", ");
        }
      } else if (error.response?.data?.message) {
        errorMessage = error.response.data.message;
      }
      
      toast.error("Не удалось сохранить ID пользователя", {
        description: errorMessage,
        duration: 3000,
      });
    } finally {
      setSaving((prev) => ({ ...prev, [bankCode]: false }));
    }
  };

  const handleDeleteBankUser = async (bankCode: string) => {
    // Use toast.promise for confirmation-like behavior
    const confirmed = window.confirm(`Удалить ID пользователя для ${bankNames[bankCode]}?`);
    if (!confirmed) {
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
      toast.success(`ID пользователя для ${bankNames[bankCode]} удален`, {
        description: "Банковская интеграция отключена",
        duration: 1500,
      });
    } catch (error: any) {
      console.error("Error deleting bank me:", error);
      const errorMessage = error.response?.data?.detail || "Ошибка при удалении ID пользователя";
      toast.error("Не удалось удалить ID пользователя", {
        description: errorMessage,
        duration: 1500,
      });
    }
  };

  const handleCreateConsent = async (bankCode: string) => {
    if (!bankUsers[bankCode]) {
      toast.error("Сначала укажите ID пользователя в банке", {
        description: `Для ${bankNames[bankCode]} необходимо указать ID пользователя`,
        duration: 2000,
      });
      return;
    }

    try {
      setCreatingConsent((prev) => ({ ...prev, [bankCode]: true }));
      const response = await createAccountConsent(bankCode);
      
      // Сохраняем согласие в куки
      setCookie(`consent_${bankCode}`, response.data.consent_id, 365);
      
      // Обновляем список согласий
      const newConsent: BankConsent = {
        consent_id: response.data.consent_id,
        bank_code: bankCode,
        status: response.data.status,
        auto_approved: response.data.auto_approved,
        expires_at: response.data.expires_at,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      
      setConsents((prev) => ({
        ...prev,
        [bankCode]: newConsent,
      }));
      
      // Показываем сообщение в зависимости от статуса
      if (response.data.status === "pending" || response.data.is_request) {
        toast.info(`Согласие для ${bankNames[bankCode]} создано`, {
          description: response.data.is_request 
            ? "Ожидание одобрения... Используйте кнопку 'Обновить' для проверки статуса"
            : "Ожидание одобрения... Используйте кнопку 'Обновить' для проверки статуса",
          duration: 4000,
        });
      } else {
        toast.success(`Согласие для ${bankNames[bankCode]} создано`, {
          description: response.data.message || `ID: ${response.data.consent_id}`,
          duration: 2000,
        });
      }
    } catch (error: any) {
      console.error("Error creating consent:", error);
      const errorMessage = error.response?.data?.detail || "Ошибка при создании согласия";
      toast.error("Не удалось создать согласие", {
        description: errorMessage,
        duration: 2000,
      });
    } finally {
      setCreatingConsent((prev) => ({ ...prev, [bankCode]: false }));
    }
  };

  const handleRefreshConsent = async (bankCode: string) => {
    const consent = consents[bankCode];
    if (!consent) {
      toast.error("Согласие не найдено", {
        description: "Сначала создайте согласие",
        duration: 2000,
      });
      return;
    }

    try {
      setPollingConsent((prev) => ({ ...prev, [bankCode]: true }));
      
      // Отправляем запрос на проверку статуса согласия
      const response = await getConsentDetails(consent.consent_id, bankCode);
      
      // Сохраняем consent_id в куки (может быть обновлен, если был request_id)
      const updatedConsentId = response.data.consent_id || consent.consent_id;
      setCookie(`consent_${bankCode}`, updatedConsentId, 365);
      
      // Перезагружаем список согласий для получения актуального статуса
      await loadConsents();
      
      // Если статус approved или active, обновляем банковские данные
      const newStatus = response.data.db_status || consent.status;
      if (["approved", "active", "valid", "authorized", "given"].includes(newStatus)) {
        // Фоново обновляем данные
        refreshBankData();
      }
      
      toast.success(`Статус согласия для ${bankNames[bankCode]} обновлен`, {
        description: `Текущий статус: ${newStatus}`,
        duration: 2000,
      });
    } catch (error: any) {
      console.error("Error refreshing consent:", error);
      const errorMessage = error.response?.data?.detail || error.message || "Попробуйте позже";
      toast.error("Не удалось обновить статус согласия", {
        description: errorMessage,
        duration: 2000,
      });
    } finally {
      setPollingConsent((prev) => {
        const newPolling = { ...prev };
        delete newPolling[bankCode];
        return newPolling;
      });
    }
  };

  const handleLogout = () => {
    logout();
    eraseCookie("access_token");
    eraseCookie("refresh_token");
    toast.success("Вы успешно вышли из аккаунта", {
      description: "До свидания!",
      duration: 1500,
    });
    navigate("/");
    setTimeout(() => {
      window.location.reload();
    }, 500);
  };


  if (!me) {
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
              {me.first_name} {me.last_name}
            </h1>
          </div>

          <div className={styles.profileInfo}>
            <div className={styles.infoItem}>
              <div className={styles.infoIcon}>
                <Mail size={20} />
              </div>
              <div className={styles.infoContent}>
                <div className={styles.infoLabel}>Email</div>
                <div className={styles.infoValue}>{me.email}</div>
              </div>
            </div>

            <div className={styles.infoItem}>
              <div className={styles.infoIcon}>
                <Phone size={20} />
              </div>
              <div className={styles.infoContent}>
                <div className={styles.infoLabel}>Телефон</div>
                <div className={styles.infoValue}>{me.phone_number}</div>
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
                      <Label htmlFor={`bank-me-${bankCode}`} className={styles.consentLabel}>
                        {bankNames[bankCode]}
                      </Label>
                    </div>
                    <div className={styles.consentInputGroup}>
                      <Input
                        id={`bank-me-${bankCode}`}
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

          {/* Consents Section */}
          <div className={styles.consentsSection}>
            <h2 className={styles.sectionTitle}>Согласия на доступ к данным</h2>
            <p className={styles.sectionDescription}>
              Создайте согласие для каждого банка, чтобы получать данные о счетах, балансах и транзакциях.
            </p>
            
            {isLoadingConsents ? (
              <div className={styles.loading}>Загрузка...</div>
            ) : (
              <div className={styles.consentsList}>
                {(["vbank", "abank", "sbank"] as const).map((bankCode) => {
                  const consent = consents[bankCode];
                  const hasBankUser = !!bankUsers[bankCode];
                  
                  return (
                    <div key={bankCode} className={styles.consentItem}>
                      <div className={styles.consentHeader}>
                        <div className={styles.consentIcon}>
                          <Shield size={20} />
                        </div>
                        <Label className={styles.consentLabel}>
                          {bankNames[bankCode]}
                        </Label>
                        {consent && (
                          <div className={styles.consentStatus}>
                            {consent.status === "approved" && (
                              <>
                                <CheckCircle2 size={16} className={styles.consentStatusIcon} />
                                <span>Активно</span>
                              </>
                            )}
                            {consent.status === "pending" && (
                              <>
                                <div className={styles.spinner} />
                                <span>Ожидание одобрения...</span>
                              </>
                            )}
                            {(consent.status === "revoked" || consent.status === "rejected") && (
                              <>
                                <span style={{ color: "#ef4444" }}>●</span>
                                <span style={{ color: "#ef4444" }}>
                                  {consent.status === "revoked" ? "Отозвано" : "Отклонено"}
                                </span>
                              </>
                            )}
                          </div>
                        )}
                      </div>
                      
                      {consent ? (
                        <div className={styles.consentInfo}>
                          <div className={styles.consentDetails}>
                            <div className={styles.consentDetail}>
                              <span className={styles.consentDetailLabel}>ID согласия:</span>
                              <span className={styles.consentDetailValue}>{consent.consent_id}</span>
                            </div>
                            {consent.expires_at && (
                              <div className={styles.consentDetail}>
                                <span className={styles.consentDetailLabel}>Истекает:</span>
                                <span className={styles.consentDetailValue}>
                                  {new Date(consent.expires_at).toLocaleDateString("ru-RU")}
                                </span>
                              </div>
                            )}
                            <div className={styles.consentDetail}>
                              <span className={styles.consentDetailLabel}>Статус:</span>
                              <span className={styles.consentDetailValue}>
                                {consent.status === "approved" && "Одобрено"}
                                {consent.status === "pending" && "Ожидание одобрения"}
                                {consent.status === "revoked" && "Отозвано"}
                                {consent.status === "rejected" && "Отклонено"}
                                {!["approved", "pending", "revoked", "rejected"].includes(consent.status) && consent.status}
                              </span>
                            </div>
                          </div>
                          {pollingConsent[bankCode] && (
                            <div className={styles.consentPolling}>
                              <div className={styles.spinner} />
                              <span>Проверяю статус согласия...</span>
                            </div>
                          )}
                          <div className={styles.consentActions}>
                            <Button
                              size="sm"
                              onClick={() => handleRefreshConsent(bankCode)}
                              disabled={pollingConsent[bankCode] || !consent}
                              className={styles.createConsentButton}
                            >
                              <RefreshCw size={16} />
                              {pollingConsent[bankCode] ? "Обновление..." : "Обновить"}
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => handleCreateConsent(bankCode)}
                              disabled={creatingConsent[bankCode] || !hasBankUser || pollingConsent[bankCode]}
                              className={styles.createConsentButton}
                              variant="outline"
                            >
                              <Shield size={16} />
                              {creatingConsent[bankCode] ? "Создание..." : "Создать новое"}
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div className={styles.consentInfo}>
                          <div className={styles.consentEmpty}>
                            {hasBankUser ? (
                              <p>Согласие не создано. Нажмите кнопку ниже для создания.</p>
                            ) : (
                              <p>Сначала укажите ID пользователя в банке выше.</p>
                            )}
                          </div>
                          <Button
                            size="sm"
                            onClick={() => handleCreateConsent(bankCode)}
                            disabled={creatingConsent[bankCode] || !hasBankUser}
                            className={styles.createConsentButton}
                          >
                            <Shield size={16} />
                            {creatingConsent[bankCode] ? "Создание..." : "Создать согласие"}
                          </Button>
                        </div>
                      )}
                    </div>
                  );
                })}
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


