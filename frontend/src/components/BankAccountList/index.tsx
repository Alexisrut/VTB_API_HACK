import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Building2 } from "lucide-react";
import { useEffect, useState } from "react";
import { type BankAccount } from "../../utils/api";
import styles from "./index.module.scss";
import { useMe } from "../../hooks/context";
import { useBankData } from "../../hooks/BankDataContext";

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

function formatTimeAgo(date: number | null): string {
  if (!date) return "—";
  
  const now = new Date();
  const diffMs = now.getTime() - date;
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
  
  // Поддерживаем структуру из BankDataContext, где amount это строка
  const amount = balance.balanceAmount?.amount || (balance as any).amount?.amount || (balance as any).amount || "0";
  return parseFloat(amount) || 0;
}

export default function BankAccountsList() {
  const me = useMe();
  const { accounts: contextAccounts, isLoading, lastUpdated } = useBankData();
  const [accounts, setAccounts] = useState<AccountDisplay[]>([]);

  useEffect(() => {
    if (!me) return;
    
    const accountsList: AccountDisplay[] = contextAccounts.map(account => {
      const balance = getAccountBalance(account);
      const currency = account.currency || account.balances?.[0]?.balanceAmount?.currency || "RUB";
      // Получаем bank_code из расширенного объекта (см. BankDataContext)
      const bankCode = (account as any).bank_code || "vbank";
      const accountId = account.account_id || account.accountId || account.id || "";
      
      return {
        bank: bankNames[bankCode] || bankCode,
        balance: balance,
        currency: currency === "RUB" ? "₽" : currency,
        lastSync: formatTimeAgo(lastUpdated),
        status: "active",
        accountId: accountId,
      };
    });
    
    setAccounts(accountsList);
  }, [me, contextAccounts, lastUpdated]);

  if (!me) {
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
        {isLoading && accounts.length === 0 ? (
          <div className={styles.loadingState}>
            <p>Загрузка счетов...</p>
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