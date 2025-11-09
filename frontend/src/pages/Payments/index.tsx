import Layout from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { Calendar, ArrowUpCircle, ArrowDownCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { getAllBankAccounts, getAccountTransactions, type BankTransaction } from "../../utils/api";
import styles from "./index.module.scss";
import { toast } from "sonner";

export default function Payments() {
  const { isAuthenticated } = useAuth();
  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "income" | "expense">("all");

  useEffect(() => {
    if (!isAuthenticated) {
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

        const transactionPromises: Promise<void>[] = [];

        Object.entries(accountsRes.data.banks || {}).forEach(([bankCode, bankData]) => {
          if (bankData.success && bankData.accounts) {
            bankData.accounts.forEach((account) => {
              // Извлекаем account_id из разных возможных мест
              const accountId = account.account_id || account.id || account.accountId || 
                               (account.account?.identification) || 
                               (account.account?.account_id);
              
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
                  allTransactions.push(...txs);
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
          const dateA = new Date(a.bookingDateTime || a.valueDateTime || 0).getTime();
          const dateB = new Date(b.bookingDateTime || b.valueDateTime || 0).getTime();
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
  }, [isAuthenticated]);

  const filteredTransactions = transactions.filter((tx) => {
    if (filter === "all") return true;
    if (filter === "income") return tx.creditDebitIndicator === "Credit";
    if (filter === "expense") return tx.creditDebitIndicator === "Debit";
    return true;
  });

  const formatDate = (dateString?: string) => {
    if (!dateString) return "—";
    return new Date(dateString).toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };

  const formatAmount = (amount: string) => {
    return parseFloat(amount).toLocaleString("ru-RU", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  if (!isAuthenticated) {
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
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
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
            {isLoading ? (
              <div style={{ padding: "2rem", textAlign: "center" }}>
                <p>Загрузка данных...</p>
              </div>
            ) : error ? (
              <div style={{ padding: "2rem", textAlign: "center", color: "#ef4444" }}>
                <p>{error}</p>
              </div>
            ) : filteredTransactions.length === 0 ? (
              <div style={{ padding: "2rem", textAlign: "center" }}>
                <p>Нет транзакций за выбранный период</p>
              </div>
            ) : (
              <div className={styles.tableWrap}>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Дата</TableHead>
                      <TableHead>Описание</TableHead>
                      <TableHead>Контрагент</TableHead>
                      <TableHead>Тип</TableHead>
                      <TableHead>Сумма</TableHead>
                      <TableHead>Статус</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTransactions.map((tx) => (
                      <TableRow key={tx.transactionId || `${tx.bookingDateTime}-${tx.amount.amount}`}>
                        <TableCell>{formatDate(tx.bookingDateTime || tx.valueDateTime)}</TableCell>
                        <TableCell className={styles.description}>
                          {tx.transactionInformation ||
                            tx.remittanceInformation?.unstructured ||
                            "Без описания"}
                        </TableCell>
                        <TableCell>
                          {tx.creditDebitIndicator === "Credit"
                            ? tx.creditorName || "—"
                            : tx.debtorName || "—"}
                        </TableCell>
                        <TableCell>
                          {tx.creditDebitIndicator === "Credit" ? (
                            <div className={styles.typeIncome}>
                              <ArrowUpCircle size={16} />
                              <span>Доход</span>
                            </div>
                          ) : (
                            <div className={styles.typeExpense}>
                              <ArrowDownCircle size={16} />
                              <span>Расход</span>
                            </div>
                          )}
                        </TableCell>
                        <TableCell
                          className={
                            tx.creditDebitIndicator === "Credit" ? styles.amountIncome : styles.amountExpense
                          }
                        >
                          {tx.creditDebitIndicator === "Credit" ? "+" : "-"}₽
                          {formatAmount(tx.amount.amount)}
                        </TableCell>
                        <TableCell>
                          <span className={styles.status}>{tx.status}</span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}

