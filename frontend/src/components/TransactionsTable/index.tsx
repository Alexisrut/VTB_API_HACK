import { ArrowDownCircle, ArrowUpCircle } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { type BankTransaction } from "../../utils/api";
import styles from "./index.module.scss";

type TransactionWithMeta = BankTransaction & {
  bankName?: string;
  bankCode?: string;
};

interface TransactionsTableProps {
  transactions: TransactionWithMeta[];
  isLoading: boolean;
  error?: string | null;
  loadingMessage?: string;
  emptyMessage?: string;
  limit?: number;
}

const fallbackBankNames: Record<string, string> = {
  vbank: "Virtual Bank",
  abank: "Awesome Bank",
  sbank: "Smart Bank",
};

const normalizeDate = (dateString?: string) => {
  if (!dateString) return null;
  const hasTimezone = dateString.includes("Z") || /[+-]\d{2}:?\d{2}$/.test(dateString);
  const normalized = hasTimezone ? dateString : `${dateString}Z`;
  const parsed = new Date(normalized);
  return isNaN(parsed.getTime()) ? null : parsed;
};

const formatDate = (dateString?: string) => {
  const date = normalizeDate(dateString);
  if (!date) return "—";
  return date.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
};

const extractAmount = (amount: unknown) => {
  if (amount === null || amount === undefined) {
    return 0;
  }

  if (typeof amount === "number") {
    return amount;
  }

  if (typeof amount === "string") {
    const parsed = parseFloat(amount);
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  if (typeof amount === "object" && amount !== null && "amount" in amount) {
    const raw = (amount as { amount?: string }).amount;
    return raw ? parseFloat(raw) || 0 : 0;
  }

  return 0;
};

const formatAmount = (amount: number) => {
  return amount.toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
};

const extractDescription = (tx: TransactionWithMeta) => {
  if (tx.transactionInformation) return tx.transactionInformation;
  if (typeof tx.remittance_information === "string") return tx.remittance_information;
  if (tx.remittanceInformation) {
    if (typeof tx.remittanceInformation === "string") return tx.remittanceInformation;
    if (typeof tx.remittanceInformation === "object") {
      return tx.remittanceInformation.unstructured ?? "Без описания";
    }
  }
  return "Без описания";
};

export default function TransactionsTable({
  transactions,
  isLoading,
  error,
  loadingMessage = "Загрузка данных...",
  emptyMessage = "Нет транзакций",
  limit,
}: TransactionsTableProps) {
  const visibleTransactions = limit ? transactions.slice(0, limit) : transactions;

  if (isLoading) {
    return (
      <div className={styles.message}>
        <p>{loadingMessage}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.error}>
        <p>{error}</p>
      </div>
    );
  }

  if (!visibleTransactions.length) {
    return (
      <div className={styles.message}>
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
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
          {visibleTransactions.map((tx) => {
            const indicatorRaw = tx.transaction_type || tx.creditDebitIndicator;
            const indicator = indicatorRaw ? indicatorRaw.toString().toLowerCase() : "";
            const isCredit = indicator === "credit";
            const txAmount = extractAmount(tx.amount);
            const txDate = tx.booking_date || tx.bookingDateTime || tx.value_date || tx.valueDateTime;
            const bankName = tx.bankName || (tx.bankCode ? fallbackBankNames[tx.bankCode] || tx.bankCode : "—");
            const txId = tx.transaction_id || tx.transactionId || tx.transactionReference || `${txDate}-${txAmount}`;

            return (
              <TableRow key={txId}>
                <TableCell>{formatDate(txDate)}</TableCell>
                <TableCell className={styles.description}>{extractDescription(tx)}</TableCell>
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
                <TableCell className={isCredit ? styles.amountIncome : styles.amountExpense}>
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
  );
}

