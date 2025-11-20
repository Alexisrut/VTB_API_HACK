import Layout from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { useEffect, useState } from "react";
import { getAllBankAccounts, getAccountTransactions, getAccountId, type BankTransaction } from "../../utils/api";
import styles from "./index.module.scss";
import { toast } from "sonner";
import { useMe } from "../../hooks/context";
import TransactionsTable from "../../components/TransactionsTable";

const bankNames: { [key: string]: string } = {
  vbank: "Virtual Bank",
  abank: "Awesome Bank",
  sbank: "Smart Bank",
};

export default function Payments() {
  const me = useMe();
  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "income" | "expense">("all");

  useEffect(() => {
    if (!me) {
      setIsLoading(false);
      return;
    }

    const fetchTransactions = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const accountsRes = await getAllBankAccounts();
        if (!accountsRes.data.success) {
          throw new Error("Не удалось получить счета");
        }

        const allTransactions: BankTransaction[] = [];
        const now = new Date();
        const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        const fromDate = thirtyDaysAgo.toISOString().split("T")[0];
        const toDate = now.toISOString().split("T")[0];

        const bankNames: { [key: string]: string } = {
          vbank: "Virtual Bank",
          abank: "Awesome Bank",
          sbank: "Smart Bank",
        };

        const transactionPromises: Promise<void>[] = [];

        Object.entries(accountsRes.data.banks || {}).forEach(([bankCode, bankData]) => {
          if (bankData.success && bankData.accounts) {
            bankData.accounts.forEach((account) => {
              // Получаем account_id используя унифицированную функцию
              const accountId = getAccountId(account);
              
              if (!accountId) {
                console.warn(`[Payments] Skipping account without account_id:`, account);
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
                  const txs = response.data.transactions || [];
                  // Добавляем название банка к каждой транзакции
                  const txsWithBank = txs.map((tx: BankTransaction) => ({
                    ...tx,
                    bankName: bankNames[bankCode] || bankCode,
                    bankCode: bankCode,
                  }));
                  allTransactions.push(...txsWithBank);
                })
                .catch((err) => {
                  console.error(`Error fetching transactions for account ${accountId}:`, err);
                });

              transactionPromises.push(promise);
            });
          }
        });

        await Promise.all(transactionPromises);

        // Sort by date (newest first)
        allTransactions.sort((a, b) => {
          const dateA = new Date(a.booking_date || a.bookingDateTime || a.value_date || a.valueDateTime || 0).getTime();
          const dateB = new Date(b.booking_date || b.bookingDateTime || b.value_date || b.valueDateTime || 0).getTime();
          return dateB - dateA;
        });

        setTransactions(allTransactions);
      } catch (err: any) {
        console.error("Error fetching payments:", err);
        setError(err.response?.data?.detail || err.message || "Ошибка загрузки данных");
        toast.error("Не удалось загрузить транзакции");
      } finally {
        setIsLoading(false);
      }
    };

    fetchTransactions();
  }, [me]);

  const filteredTransactions = transactions.filter((tx) => {
    if (filter === "all") return true;
    const indicator = (tx.transaction_type || tx.creditDebitIndicator || "").toString().toLowerCase();
    if (filter === "income") return indicator === "credit";
    if (filter === "expense") return indicator === "debit";
    return true;
  });

  if (!me) {
    return (
      <Layout>
        <Card>
          <CardHeader>
            <CardTitle>Платежи</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Войдите, чтобы увидеть транзакции</p>
          </CardContent>
        </Card>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className={styles.container}>
        <div className={styles.header}>
          <h1>Платежи</h1>
          <p>История транзакций за последние 30 дней</p>
        </div>

        <Card>
          <CardHeader>
            <div className={styles.cardHeaderRow}>
              <CardTitle>Транзакции</CardTitle>
              <div className={styles.filters}>
                <button
                  className={filter === "all" ? styles.filterActive : styles.filterButton}
                  onClick={() => setFilter("all")}
                >
                  Все
                </button>
                <button
                  className={filter === "income" ? styles.filterActive : styles.filterButton}
                  onClick={() => setFilter("income")}
                >
                  Доходы
                </button>
                <button
                  className={filter === "expense" ? styles.filterActive : styles.filterButton}
                  onClick={() => setFilter("expense")}
                >
                  Расходы
                </button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <TransactionsTable
              transactions={filteredTransactions}
              isLoading={isLoading}
              error={error}
              emptyMessage="Нет транзакций за выбранный период"
            />
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}

