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

    // Используем захардкоженные данные для демонстрации
    const mockTransactions: any[] = [
      {
        transaction_id: "tx-001",
        booking_date: "2024-11-15",
        transaction_type: "Credit",
        amount: 450000,
        transactionInformation: "Оплата по счету INV-2024-001 от ООО \"Альфа\"",
        bankName: "Vbank",
        bankCode: "vtb",
        status: "Booked",
      },
      {
        transaction_id: "tx-002",
        booking_date: "2024-11-14",
        transaction_type: "Credit",
        amount: 320000,
        transactionInformation: "Оплата по счету INV-2024-002 от ООО \"Бета\"",
        bankName: "Sbank",
        bankCode: "sber",
        status: "Booked",
      },
      {
        transaction_id: "tx-003",
        booking_date: "2024-11-14",
        transaction_type: "Debit",
        amount: 125000,
        transactionInformation: "Оплата поставщику ООО \"Снабжение\"",
        bankName: "Vbank",
        bankCode: "vtb",
        status: "Booked",
      },
      {
        transaction_id: "tx-004",
        booking_date: "2024-11-13",
        transaction_type: "Credit",
        amount: 180000,
        transactionInformation: "Оплата по счету INV-2024-003 от ООО \"Гамма\"",
        bankName: "Abank",
        bankCode: "alpha",
        status: "Booked",
      },
      {
        transaction_id: "tx-005",
        booking_date: "2024-11-12",
        transaction_type: "Credit",
        amount: 275000,
        transactionInformation: "Оплата по счету INV-2024-004 от ООО \"Дельта\"",
        bankName: "Vbank",
        bankCode: "vtb",
        status: "Booked",
      },
      {
        transaction_id: "tx-006",
        booking_date: "2024-11-12",
        transaction_type: "Debit",
        amount: 85000,
        transactionInformation: "Аренда офиса за ноябрь",
        bankName: "Sbank",
        bankCode: "sber",
        status: "Booked",
      },
      {
        transaction_id: "tx-007",
        booking_date: "2024-11-11",
        transaction_type: "Credit",
        amount: 95000,
        transactionInformation: "Оплата по счету INV-2024-005 от ООО \"Эпсилон\"",
        bankName: "Sbank",
        bankCode: "sber",
        status: "Booked",
      },
      {
        transaction_id: "tx-008",
        booking_date: "2024-11-11",
        transaction_type: "Debit",
        amount: 45000,
        transactionInformation: "Коммунальные услуги",
        bankName: "Abank",
        bankCode: "alpha",
        status: "Booked",
      },
      {
        transaction_id: "tx-009",
        booking_date: "2024-11-10",
        transaction_type: "Credit",
        amount: 520000,
        transactionInformation: "Оплата по счету INV-2024-006 от ООО \"Зета\"",
        bankName: "Abank",
        bankCode: "alpha",
        status: "Booked",
      },
      {
        transaction_id: "tx-010",
        booking_date: "2024-11-10",
        transaction_type: "Debit",
        amount: 220000,
        transactionInformation: "Закупка материалов",
        bankName: "Vbank",
        bankCode: "vtb",
        status: "Booked",
      },
      {
        transaction_id: "tx-011",
        booking_date: "2024-11-09",
        transaction_type: "Debit",
        amount: 68000,
        transactionInformation: "Зарплата сотрудникам",
        bankName: "Sbank",
        bankCode: "sber",
        status: "Booked",
      },
      {
        transaction_id: "tx-012",
        booking_date: "2024-11-08",
        transaction_type: "Debit",
        amount: 155000,
        transactionInformation: "Налоговые платежи",
        bankName: "Vbank",
        bankCode: "vtb",
        status: "Booked",
      },
      {
        transaction_id: "tx-013",
        booking_date: "2024-11-07",
        transaction_type: "Debit",
        amount: 92000,
        transactionInformation: "Оплата услуг связи и интернета",
        bankName: "Abank",
        bankCode: "alpha",
        status: "Booked",
      },
      {
        transaction_id: "tx-014",
        booking_date: "2024-11-06",
        transaction_type: "Credit",
        amount: 410000,
        transactionInformation: "Оплата по счету INV-2024-013 от ООО \"Ню\"",
        bankName: "Vbank",
        bankCode: "vtb",
        status: "Booked",
      },
      {
        transaction_id: "tx-015",
        booking_date: "2024-11-05",
        transaction_type: "Debit",
        amount: 175000,
        transactionInformation: "Страховые взносы",
        bankName: "Sbank",
        bankCode: "sber",
        status: "Booked",
      },
      {
        transaction_id: "tx-016",
        booking_date: "2024-11-04",
        transaction_type: "Debit",
        amount: 38000,
        transactionInformation: "Канцелярские товары",
        bankName: "Abank",
        bankCode: "alpha",
        status: "Booked",
      },
      {
        transaction_id: "tx-017",
        booking_date: "2024-11-03",
        transaction_type: "Debit",
        amount: 420000,
        transactionInformation: "Оплата подрядчикам",
        bankName: "Vbank",
        bankCode: "vtb",
        status: "Booked",
      },
      {
        transaction_id: "tx-018",
        booking_date: "2024-11-02",
        transaction_type: "Debit",
        amount: 265000,
        transactionInformation: "Лизинговый платеж",
        bankName: "Sbank",
        bankCode: "sber",
        status: "Booked",
      },
      {
        transaction_id: "tx-019",
        booking_date: "2024-11-01",
        transaction_type: "Debit",
        amount: 115000,
        transactionInformation: "Реклама и маркетинг",
        bankName: "Abank",
        bankCode: "alpha",
        status: "Booked",
      },
      {
        transaction_id: "tx-020",
        booking_date: "2024-10-31",
        transaction_type: "Debit",
        amount: 340000,
        transactionInformation: "Закупка оборудования",
        bankName: "Vbank",
        bankCode: "vtb",
        status: "Booked",
      },
    ];

    setTimeout(() => {
      setTransactions(mockTransactions);
      setIsLoading(false);
    }, 450);

    /* Закомментирован реальный API вызов
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
    */
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

