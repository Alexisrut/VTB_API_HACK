import Layout from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { Calendar, ArrowUpCircle, ArrowDownCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { getAllBankAccounts, getAccountTransactions, getAccountId, type BankTransaction } from "../../utils/api";
import styles from "./index.module.scss";
import { toast } from "sonner";
import { useMe } from "../../hooks/context";

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
    const indicator = tx.transaction_type || tx.creditDebitIndicator;
    if (filter === "income") return indicator === "Credit";
    if (filter === "expense") return indicator === "Debit";
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

  const formatAmount = (amount: number | string | undefined) => {
    if (amount === undefined || amount === null) return "0.00";
    const numAmount = typeof amount === "string" ? parseFloat(amount) : amount;
    return numAmount.toLocaleString("ru-RU", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

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
                      <TableHead>Банк</TableHead>
                      <TableHead>Тип</TableHead>
                      <TableHead>Сумма</TableHead>
                      <TableHead>Статус</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTransactions.map((tx: any) => {
                      const indicator = tx.transaction_type || tx.creditDebitIndicator;
                      const isCredit = indicator === "Credit";
                      const txAmount = tx.amount || 0;
                      const txDate = tx.booking_date || tx.bookingDateTime || tx.value_date || tx.valueDateTime;
                      const txDescription = 
                        tx.transactionInformation ||
                        (typeof tx.remittance_information === "string" ? tx.remittance_information :
                         (tx.remittanceInformation && typeof tx.remittanceInformation === "object" ? tx.remittanceInformation.unstructured :
                          typeof tx.remittanceInformation === "string" ? tx.remittanceInformation : null)) ||
                        "Без описания";
                      // Используем название банка вместо контрагента
                      const bankName = tx.bankName || (tx.bankCode ? (bankNames[tx.bankCode] || tx.bankCode) : "—");
                      const txId = tx.transaction_id || tx.transactionId || `${txDate}-${txAmount}`;
                      
                      return (
                        <TableRow key={txId}>
                          <TableCell>{formatDate(txDate)}</TableCell>
                          <TableCell className={styles.description}>
                            {txDescription}
                          </TableCell>
                          <TableCell>{bankName}</TableCell>
                          <TableCell>
                            {isCredit ? (
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
                            className={isCredit ? styles.amountIncome : styles.amountExpense}
                          >
                            {isCredit ? "+" : "-"}₽{formatAmount(txAmount)}
                          </TableCell>
                          <TableCell>
                            <span className={styles.status}>{tx.status || "Booked"}</span>
                          </TableCell>
                        </TableRow>
                      );
                    })}
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

