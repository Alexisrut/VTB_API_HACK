import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Building2 } from "lucide-react";
import { useEffect, useState } from "react";
import { getAllBankAccounts, type BankAccount } from "../../utils/api";
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

        // Обрабатываем счета из всех банков
        Object.entries(data.banks || {}).forEach(([bankCode, bankData]) => {
          console.log(`[BankAccountList] Processing bank ${bankCode}:`, bankData);
          
          if (bankData.success && bankData.accounts) {
            console.log(`[BankAccountList] Bank ${bankCode} has ${bankData.accounts.length} accounts`);
            bankData.accounts.forEach((account) => {
              const balance = getAccountBalance(account);
              const currency = account.currency || account.balances?.[0]?.balanceAmount?.currency || "₽";
              
              accountsList.push({
                bank: bankNames[bankCode] || bankCode,
                balance,
                currency: currency === "RUB" ? "₽" : currency,
                lastSync: formatTimeAgo(lastSyncTime),
                status: "active",
                accountId: account.account_id,
              });
            });
          } else {
            console.warn(`[BankAccountList] Bank ${bankCode} failed or has no accounts:`, bankData.error || "No accounts");
          }
        });

        console.log(`[BankAccountList] Total accounts found: ${accountsList.length}`);
        setAccounts(accountsList);
        setLastSyncTime(new Date());
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