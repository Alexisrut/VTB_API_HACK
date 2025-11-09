import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Building2 } from "lucide-react";
import { useEffect, useState } from "react";
import { getAllBankAccounts, getAccountBalances, extractBalanceFromResponse, getAccountId, type BankAccount } from "../../utils/api";
import { useAuth } from "../../hooks/useAuth";
import styles from "./index.module.scss";

interface AccountDisplay {
  bank: string;
  balance: number;
  currency: string;
  lastSync: string;
  status: string;
  accountId: string;
}

const bankNames: { [key: string]: string } = {
  vbank: "Virtual Bank",
  abank: "Awesome Bank",
  sbank: "Smart Bank",
};

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "только что";
  if (diffMins < 60) return `${diffMins} мин назад`;
  if (diffHours < 24) return `${diffHours} час${diffHours > 1 ? "а" : ""} назад`;
  return `${diffDays} дн${diffDays > 1 ? "ей" : "ь"} назад`;
}

function getAccountBalance(account: BankAccount): number {
  if (!account.balances || account.balances.length === 0) return 0;
  
  // Ищем баланс типа "InterimAvailable" или "InterimBooked"
  const balance = account.balances.find(
    (b) => b.balanceType === "InterimAvailable" || b.balanceType === "InterimBooked"
  ) || account.balances[0];
  
  return parseFloat(balance.balanceAmount.amount) || 0;
}

export default function BankAccountsList() {
  const { isAuthenticated } = useAuth();
  const [accounts, setAccounts] = useState<AccountDisplay[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastSyncTime, setLastSyncTime] = useState<Date>(new Date());

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    const fetchAccounts = async () => {
      try {
        setIsLoading(true);
        setError(null);
        console.log("[BankAccountList] Fetching accounts...");
        const response = await getAllBankAccounts();
        const data = response.data;
        
        console.log("[BankAccountList] Accounts response:", data);

        if (!data.success) {
          throw new Error("Не удалось получить счета");
        }

        const accountsList: AccountDisplay[] = [];
        const balancePromises: Promise<void>[] = [];

        // Обрабатываем счета из всех банков
        Object.entries(data.banks || {}).forEach(([bankCode, bankData]) => {
          console.log(`[BankAccountList] Processing bank ${bankCode}:`, bankData);
          
          if (bankData.success && bankData.accounts) {
            console.log(`[BankAccountList] Bank ${bankCode} has ${bankData.accounts.length} accounts`);
            bankData.accounts.forEach((account) => {
              // Получаем account_id используя унифицированную функцию
              const accountId = getAccountId(account);
              if (!accountId) {
                console.warn(`[BankAccountList] Skipping account without account_id:`, account);
                return;
              }
              
              // Используем баланс из данных счета как начальное значение
              const initialBalance = getAccountBalance(account);
              const currency = account.currency || account.balances?.[0]?.balanceAmount?.currency || "RUB";
              
              const accountDisplay: AccountDisplay = {
                bank: bankNames[bankCode] || bankCode,
                balance: initialBalance,
                currency: currency === "RUB" ? "₽" : currency,
                lastSync: formatTimeAgo(lastSyncTime),
                status: "active",
                accountId: accountId,
              };
              
              accountsList.push(accountDisplay);
              
              // Запрашиваем актуальный баланс через API
              const balancePromise = getAccountBalances(
                accountId,
                bankCode,
                bankData.consent_id
              )
                .then((response) => {
                  console.log(`[BankAccountList] Balance for account ${accountId}:`, response.data);
                  
                  // Извлекаем баланс из ответа
                  const newBalance = extractBalanceFromResponse(response);
                  console.log(`[BankAccountList] Extracted balance for ${accountId}:`, newBalance);
                  
                  // Обновляем баланс в списке (может быть отрицательным для овердрафта)
                  setAccounts((prev) =>
                    prev.map((acc) =>
                      acc.accountId === accountId
                        ? { ...acc, balance: newBalance }
                        : acc
                    )
                  );
                })
                .catch((err) => {
                  console.error(`[BankAccountList] Error fetching balance for account ${accountId}:`, err);
                  // Не показываем ошибку пользователю, просто используем начальный баланс
                });
              
              balancePromises.push(balancePromise);
            });
          } else {
            const errorMsg = bankData.error || "No accounts";
            console.warn(`[BankAccountList] Bank ${bankCode} failed or has no accounts:`, errorMsg);
            
            // Show helpful message if bank_user_id is missing
            if (errorMsg.includes("bank_user_id") || errorMsg.includes("Please set")) {
              setError(`Для банка ${bankNames[bankCode] || bankCode} необходимо установить ID пользователя в профиле. ${errorMsg}`);
            }
          }
        });

        console.log(`[BankAccountList] Total accounts found: ${accountsList.length}`);
        setAccounts(accountsList);
        setLastSyncTime(new Date());
        
        // Ждем завершения всех запросов балансов (в фоне, не блокируя UI)
        Promise.all(balancePromises).then(() => {
          console.log(`[BankAccountList] All balance requests completed`);
        });
      } catch (err: any) {
        console.error("[BankAccountList] Error fetching bank accounts:", err);
        console.error("[BankAccountList] Error details:", {
          message: err.message,
          response: err.response?.data,
          status: err.response?.status,
        });
        setError(err.response?.data?.detail || err.message || "Ошибка загрузки счетов");
      } finally {
        setIsLoading(false);
      }
    };

    fetchAccounts();
  }, [isAuthenticated]);

  if (!isAuthenticated) {
    return (
      <Card className={styles.bankCard}>
        <CardHeader className={styles.bankCardHeader}>
          <div className={styles.headerGroup}>
            <div className={styles.headerIconBg}>
              <Building2 className={styles.headerIcon} />
            </div>
            <div>
              <CardTitle className={styles.bankCardTitle}>Банковские счета</CardTitle>
              <p className={styles.bankCardSubtitle}>
                Войдите, чтобы увидеть свои счета
              </p>
            </div>
          </div>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className={styles.bankCard}>
      <CardHeader className={styles.bankCardHeader}>
        <div className={styles.headerGroup}>
          <div className={styles.headerIconBg}>
            <Building2 className={styles.headerIcon} />
          </div>
          <div>
            <CardTitle className={styles.bankCardTitle}>Банковские счета</CardTitle>
            <p className={styles.bankCardSubtitle}>
              Все подключенные счета в одном месте
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className={styles.bankCardContent}>
        {isLoading ? (
          <div className={styles.loadingState}>
            <p>Загрузка счетов...</p>
          </div>
        ) : error ? (
          <div className={styles.errorState}>
            <p>{error}</p>
          </div>
        ) : accounts.length === 0 ? (
          <div className={styles.emptyState}>
            <p>Нет подключенных счетов</p>
          </div>
        ) : (
          <div className={styles.accountList}>
            {accounts.map((account, index) => (
              <div
                key={`${account.accountId}-${index}`}
                className={styles.accountItem}
              >
                <div className={styles.itemDetails}>
                  <div className={styles.itemIconBg}>
                    <Building2 className={styles.itemIcon} />
                  </div>
                  <div>
                    <p className={styles.itemBank}>{account.bank}</p>
                    <p className={styles.itemSync}>
                      актуален: {account.lastSync}
                    </p>
                  </div>
                </div>
                <div className={styles.itemBalance}>
                  <p className={styles.balanceAmount}>
                    {account.currency}
                    {account.balance.toLocaleString("ru-RU", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </p>
                  <Badge className={styles.statusBadge}>активен</Badge>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}