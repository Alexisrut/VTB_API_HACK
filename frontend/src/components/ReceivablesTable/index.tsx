import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { useEffect, useState } from "react";
import { getAllBankAccounts, getAccountTransactions, getAccountId, type BankTransaction } from "../../utils/api";
import styles from "./index.module.scss";
import { useMe } from "../../hooks/context";
import TransactionsTable from "../TransactionsTable";

type DashboardTransaction = BankTransaction & {
  bankName?: string;
  bankCode?: string;
};

const bankNames: Record<string, string> = {
  vbank: "Virtual Bank",
  abank: "Awesome Bank",
  sbank: "Smart Bank",
};

export default function ReceivablesTable() {
  const me = useMe();
  const [transactions, setTransactions] = useState<DashboardTransaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) {
      setIsLoading(false);
      return;
    }

    // // Используем захардкоженные данные для демонстрации
    // const mockReceivables: Receivable[] = [
    //   {
    //     id: "rec-1",
    //     counterparty: "Vbank",
    //     amount: 450000,
    //     dueDate: "15.11",
    //     status: "received",
    //   },
    //   {
    //     id: "rec-2",
    //     counterparty: "Sbank",
    //     amount: 320000,
    //     dueDate: "14.11",
    //     status: "received",
    //   },
    //   {
    //     id: "rec-3",
    //     counterparty: "Abank",
    //     amount: 180000,
    //     dueDate: "13.11",
    //     status: "pending",
    //   },
    //   {
    //     id: "rec-4",
    //     counterparty: "Vbank",
    //     amount: 275000,
    //     dueDate: "12.11",
    //     status: "received",
    //   },
    //   {
    //     id: "rec-5",
    //     counterparty: "Sbank",
    //     amount: 95000,
    //     dueDate: "11.11",
    //     status: "pending",
    //   },
    //   {
    //     id: "rec-6",
    //     counterparty: "Abank",
    //     amount: 520000,
    //     dueDate: "10.11",
    //     status: "received",
    //   },
    //   {
    //     id: "rec-7",
    //     counterparty: "Vbank",
    //     amount: 68000,
    //     dueDate: "09.11",
    //     status: "overdue",
    //   },
    // ];

    // setTimeout(() => {
    //   setReceivables(mockReceivables);
    //   setIsLoading(false);
    // }, 500);

    const fetchReceivables = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const accountsResponse = await getAllBankAccounts();
        const accountsData = accountsResponse.data;

        if (!accountsData.success) {
          throw new Error("Не удалось получить счета");
        }

        const now = new Date();
        const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        const fromDate = thirtyDaysAgo.toISOString().split("T")[0];
        const toDate = now.toISOString().split("T")[0];

        const collected: DashboardTransaction[] = [];
        const transactionPromises: Promise<void>[] = [];

        Object.entries(accountsData.banks || {}).forEach(([bankCode, bankData]) => {
          if (!bankData.success || !bankData.accounts?.length) {
            console.warn(`[ReceivablesTable] Bank ${bankCode} has no accounts or failed:`, bankData.error || "No accounts");
            return;
          }

          bankData.accounts.forEach((account) => {
            const accountId = getAccountId(account);

            if (!accountId) {
              console.warn(`[ReceivablesTable] Skipping account without account_id:`, account);
              return;
            }

            const promise = getAccountTransactions(
              accountId,
              bankCode,
              undefined,
              fromDate,
              toDate
            )
              .then((response) => {
                const transactionsPayload = response.data?.transactions || response.data?.transaction || [];
                const creditTransactions = (transactionsPayload as BankTransaction[])
                  .map((tx) => ({
                    ...tx,
                    bankName: bankNames[bankCode] || bankCode,
                    bankCode,
                  }))
                  .filter((tx) => {
                    const indicator = (tx.transaction_type || tx.creditDebitIndicator || "").toString().toLowerCase();
                    return indicator === "credit";
                  });

                collected.push(...creditTransactions);
              })
              .catch((err) => {
                console.error(`[ReceivablesTable] Error fetching transactions for account ${accountId}:`, err);
                console.error(`[ReceivablesTable] Error details:`, {
                  message: err.message,
                  response: err.response?.data,
                  status: err.response?.status,
                });
              });

            transactionPromises.push(promise);
          });
        });

        await Promise.all(transactionPromises);

        collected.sort((a, b) => {
          const dateA = new Date(a.booking_date || a.bookingDateTime || a.value_date || a.valueDateTime || 0).getTime();
          const dateB = new Date(b.booking_date || b.bookingDateTime || b.value_date || b.valueDateTime || 0).getTime();
          return dateB - dateA;
        });

        setTransactions(collected);
      } catch (err: any) {
        console.error("Error fetching receivables:", err);
        setError(err.response?.data?.detail || err.message || "Ошибка загрузки данных");
      } finally {
        setIsLoading(false);
      }
    };

    fetchReceivables();
  }, [me]);

  if (!me) {
    return (
      <Card className={styles.cardRoot}>
        <CardHeader className={styles.header}>
          <div className={styles.iconBox} aria-hidden>
            <svg className="h-5 w-5 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className={styles.headerText}>
            <CardTitle className={styles.title}>Выплаты</CardTitle>
            <p className={styles.subtitle}>Войдите, чтобы увидеть входящие платежи</p>
          </div>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className={styles.cardRoot}>
      <CardHeader className={styles.header}>
        <div className={styles.iconBox} aria-hidden>
          <svg className="h-5 w-5 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div className={styles.headerText}>
          <CardTitle className={styles.title}>Выплаты</CardTitle>
          <p className={styles.subtitle}>Отслеживайте входящие платежи и управляйте ими</p>
        </div>
      </CardHeader>
      <CardContent className={styles.content}>
        <TransactionsTable
          transactions={transactions}
          isLoading={isLoading}
          error={error}
          emptyMessage="Нет входящих платежей за последние 30 дней"
          limit={20}
        />
      </CardContent>
    </Card>
  );
}
