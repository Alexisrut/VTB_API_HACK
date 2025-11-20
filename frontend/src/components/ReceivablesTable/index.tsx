import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Button } from "../../ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../ui/table";
import { useEffect, useState } from "react";
import { getAllBankAccounts, getAccountTransactions, getAccountBalances, getAccountId, type BankAccount, type BankTransaction } from "../../utils/api";
import styles from "./index.module.scss";
import { Phone } from "lucide-react";
import { useMe } from "../../hooks/context";

interface Receivable {
  id: string;
  counterparty: string;
  amount: number;
  dueDate: string;
  status: "pending" | "overdue" | "received";
  transactionId?: string;
}

const bankNames: { [key: string]: string } = {
  vbank: "Virtual Bank",
  abank: "Awesome Bank",
  sbank: "Smart Bank",
};

function formatDate(dateString?: string): string {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    const day = date.getDate().toString().padStart(2, "0");
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    return `${day}.${month}`;
  } catch {
    return "—";
  }
}

function isOverdue(dateString?: string): boolean {
  if (!dateString) return false;
  try {
    const date = new Date(dateString);
    const now = new Date();
    return date < now;
  } catch {
    return false;
  }
}

export default function ReceivablesTable() {
  const me = useMe();
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) {
      setIsLoading(false);
      return;
    }

    // Используем захардкоженные данные для демонстрации
    const mockReceivables: Receivable[] = [
      {
        id: "rec-1",
        counterparty: "Vbank",
        amount: 450000,
        dueDate: "15.11",
        status: "received",
      },
      {
        id: "rec-2",
        counterparty: "Sbank",
        amount: 320000,
        dueDate: "14.11",
        status: "received",
      },
      {
        id: "rec-3",
        counterparty: "Abank",
        amount: 180000,
        dueDate: "13.11",
        status: "pending",
      },
      {
        id: "rec-4",
        counterparty: "Vbank",
        amount: 275000,
        dueDate: "12.11",
        status: "received",
      },
      {
        id: "rec-5",
        counterparty: "Sbank",
        amount: 95000,
        dueDate: "11.11",
        status: "pending",
      },
      {
        id: "rec-6",
        counterparty: "Abank",
        amount: 520000,
        dueDate: "10.11",
        status: "received",
      },
      {
        id: "rec-7",
        counterparty: "Vbank",
        amount: 68000,
        dueDate: "09.11",
        status: "overdue",
      },
    ];

    setTimeout(() => {
      setReceivables(mockReceivables);
      setIsLoading(false);
    }, 500);

    /* Закомментирован реальный API вызов
    const fetchReceivables = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Сначала получаем все счета
        console.log("[ReceivablesTable] Fetching accounts...");
        const accountsResponse = await getAllBankAccounts();
        const accountsData = accountsResponse.data;
        
        console.log("[ReceivablesTable] Accounts response:", accountsData);

        if (!accountsData.success) {
          throw new Error("Не удалось получить счета");
        }

        const receivablesList: Receivable[] = [];
        const now = new Date();
        const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        const fromDate = thirtyDaysAgo.toISOString().split("T")[0];
        const toDate = now.toISOString().split("T")[0];

        // Получаем транзакции и балансы из всех счетов
        const transactionPromises: Promise<void>[] = [];

        Object.entries(accountsData.banks || {}).forEach(([bankCode, bankData]) => {
          console.log(`[ReceivablesTable] Processing bank ${bankCode}:`, bankData);
          
          if (bankData.success && bankData.accounts && bankData.accounts.length > 0) {
            console.log(`[ReceivablesTable] Bank ${bankCode} has ${bankData.accounts.length} accounts`);
            bankData.accounts.forEach((account) => {
              // Получаем account_id используя унифицированную функцию
              const accountId = getAccountId(account);
              
              if (!accountId) {
                console.warn(`[ReceivablesTable] Skipping account without account_id:`, account);
                return;
              }
              
              console.log(`[ReceivablesTable] Fetching transactions for account ${accountId} from ${bankCode}`);
              
              // Получаем баланс счета (сервер автоматически использует сохраненный consent_id)
              const balancePromise = getAccountBalances(
                accountId,
                bankCode,
                bankData.consent_id // опционально, сервер получит из БД если не указано
              )
                .then((response) => {
                  console.log(`[ReceivablesTable] Balance for account ${accountId}:`, response.data);
                  // Здесь можно обработать баланс, например, сохранить в состояние или отобразить
                })
                .catch((err) => {
                  console.error(`[ReceivablesTable] Error fetching balance for account ${accountId}:`, err);
                  console.error(`[ReceivablesTable] Error details:`, {
                    message: err.message,
                    response: err.response?.data,
                    status: err.response?.status,
                  });
                });
              
              transactionPromises.push(balancePromise);
              
              // Сервер автоматически использует сохраненный consent_id
              const promise = getAccountTransactions(
                accountId,
                bankCode,
                undefined, // consent_id не передаем - сервер использует сохраненный
                fromDate,
                toDate
              )
                .then((response) => {
                  const transactions = response.data.transactions || [];
                  console.log(`[ReceivablesTable] Received ${transactions.length} transactions for account ${accountId}`);
                  
                  // Фильтруем входящие транзакции (Credit)
                  // Берем только первые 5 с каждого банка
                  const creditTransactions = transactions
                    .filter((tx) => {
                      const indicator = tx.transaction_type || tx.creditDebitIndicator;
                      return indicator === "Credit";
                    })
                    .slice(0, 5); // Ограничиваем до 5 транзакций с каждого банка
                  
                  creditTransactions.forEach((tx) => {
                    // Извлекаем сумму из нового формата
                    const amount = tx.amount || 0;
                    
                    // Используем название банка вместо контрагента
                    const counterparty = bankNames[bankCode] || bankCode;
                    
                    // Извлекаем дату
                    const bookingDate = tx.booking_date || tx.bookingDateTime || tx.value_date || tx.valueDateTime;
                    const status = bookingDate && isOverdue(bookingDate) 
                      ? "overdue" 
                      : bookingDate 
                      ? "pending" 
                      : "received";

                    receivablesList.push({
                      id: tx.transaction_id || tx.transactionId || `${accountId}-${tx.transactionReference || Date.now()}`,
                      counterparty,
                      amount,
                      dueDate: formatDate(bookingDate),
                      status: status as "pending" | "overdue" | "received",
                      transactionId: tx.transaction_id || tx.transactionId,
                    });
                  });
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
          } else {
            console.warn(`[ReceivablesTable] Bank ${bankCode} has no accounts or failed:`, bankData.error || "No accounts");
          }
        });

        console.log(`[ReceivablesTable] Waiting for ${transactionPromises.length} transaction requests...`);
        await Promise.all(transactionPromises);
        console.log(`[ReceivablesTable] Found ${receivablesList.length} receivables`);

        // Сортируем по дате (новые сначала)
        receivablesList.sort((a, b) => {
          if (a.dueDate === "—" && b.dueDate === "—") return 0;
          if (a.dueDate === "—") return 1;
          if (b.dueDate === "—") return -1;
          return b.dueDate.localeCompare(a.dueDate);
        });

        setReceivables(receivablesList);
      } catch (err: any) {
        console.error("Error fetching receivables:", err);
        setError(err.response?.data?.detail || err.message || "Ошибка загрузки данных");
      } finally {
        setIsLoading(false);
      }
    };

    fetchReceivables();
    */
  }, [me]);

  const getStatusBadge = (status: string) => {
    if (status === "overdue") {
      return (
        <Badge className={styles.badgeOverdue}>
          Overdue
        </Badge>
      );
    }
    if (status === "received") {
      return (
        <Badge className={styles.badgePending} style={{ backgroundColor: "#10b981" }}>
          Received
        </Badge>
      );
    }
    return (
      <Badge className={styles.badgePending}>
        Pending
      </Badge>
    );
  };

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
        {isLoading ? (
          <div style={{ padding: "2rem", textAlign: "center" }}>
            <p>Загрузка данных...</p>
          </div>
        ) : error ? (
          <div style={{ padding: "2rem", textAlign: "center", color: "#ef4444" }}>
            <p>{error}</p>
          </div>
        ) : receivables.length === 0 ? (
          <div style={{ padding: "2rem", textAlign: "center" }}>
            <p>Нет входящих платежей за последние 30 дней</p>
          </div>
        ) : (
          <div className={styles.tableWrap}>
            <Table>
              <TableHeader>
                <TableRow className={styles.tableRow}>
                  <TableHead className={styles.counterparty}>Банк</TableHead>
                  <TableHead className={styles.amount}>Сумма</TableHead>
                  <TableHead className={styles.dueDate}>Дата</TableHead>
                  <TableHead>Статус</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {receivables.map((item) => (
                  <TableRow key={item.id} className={`${styles.tableRow} ${styles.tableRowHover}`}>
                    <TableCell className={styles.counterparty}>{item.counterparty}</TableCell>
                    <TableCell className={styles.amount}>
                      ₽{item.amount.toLocaleString("ru-RU", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}
                    </TableCell>
                    <TableCell className={styles.dueDate}>{item.dueDate}</TableCell>
                    <TableCell>{getStatusBadge(item.status)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
