import Layout from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { Users, AlertCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { getInvoices, getARSummary, type Invoice, type ARSummary } from "../../utils/api";
import StatCard from "../../components/StatCard";
import styles from "./index.module.scss";
import { toast } from "sonner";
import { useMe } from "../../hooks/context";

export default function Receivables() {
  const me = useMe();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [summary, setSummary] = useState<ARSummary["summary"] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (!me) {
      setIsLoading(false);
      return;
    }

    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const [invoicesRes, summaryRes] = await Promise.all([
          getInvoices(statusFilter),
          getARSummary(),
        ]);

        if (invoicesRes.data.success && invoicesRes.data.invoices) {
          setInvoices(invoicesRes.data.invoices);
        }

        if (summaryRes.data.success && summaryRes.data.summary) {
          setSummary(summaryRes.data.summary);
        }
      } catch (err: any) {
        console.error("Error fetching receivables:", err);
        setError(err.response?.data?.detail || "Ошибка загрузки данных");
        toast.error("Не удалось загрузить данные о дебиторской задолженности");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [me, statusFilter]);

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { label: string; variant: string }> = {
      pending: { label: "Ожидает оплаты", variant: "warning" },
      partial: { label: "Частично оплачено", variant: "info" },
      paid: { label: "Оплачено", variant: "success" },
      overdue: { label: "Просрочено", variant: "danger" },
      cancelled: { label: "Отменено", variant: "default" },
    };

    const statusInfo = statusMap[status.toLowerCase()] || { label: status, variant: "default" };

    return (
      <Badge className={styles[`badge${statusInfo.variant.charAt(0).toUpperCase() + statusInfo.variant.slice(1)}`]}>
        {statusInfo.label}
      </Badge>
    );
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };

  if (!me) {
    return (
      <Layout>
        <Card>
          <CardHeader>
            <CardTitle>Дебиторская задолженность</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Войдите, чтобы увидеть счета к получению</p>
          </CardContent>
        </Card>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className={styles.container}>
        <div className={styles.header}>
          <h1>Дебиторская задолженность</h1>
          <p>Управление счетами к получению</p>
        </div>

        {summary && (
          <div className={styles.summaryGrid}>
            <StatCard
              title="Общая ДЗ"
              value={`₽${(summary.total_ar || 0).toLocaleString()}`}
              subtitle="Всего к получению"
              icon={Users}
              variant="default"
            />
            <StatCard
              title="Просрочено"
              value={`₽${(summary.overdue_ar || 0).toLocaleString()}`}
              subtitle={`${summary.overdue_count || 0} счетов`}
              icon={AlertCircle}
              variant="danger"
            />
            <StatCard
              title="Ожидает оплаты"
              value={`${summary.pending_count || 0}`}
              subtitle="Счетов"
              icon={Users}
              variant="warning"
            />
            <StatCard
              title="Оплачено"
              value={`${summary.paid_count || 0}`}
              subtitle="Счетов"
              icon={Users}
              variant="success"
            />
          </div>
        )}

        <Card>
          <CardHeader>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <CardTitle>Счета к получению</CardTitle>
              <div className={styles.filters}>
                <button
                  className={statusFilter === undefined ? styles.filterActive : styles.filterButton}
                  onClick={() => setStatusFilter(undefined)}
                >
                  Все
                </button>
                <button
                  className={statusFilter === "pending" ? styles.filterActive : styles.filterButton}
                  onClick={() => setStatusFilter("pending")}
                >
                  Ожидают
                </button>
                <button
                  className={statusFilter === "overdue" ? styles.filterActive : styles.filterButton}
                  onClick={() => setStatusFilter("overdue")}
                >
                  Просрочено
                </button>
                <button
                  className={statusFilter === "paid" ? styles.filterActive : styles.filterButton}
                  onClick={() => setStatusFilter("paid")}
                >
                  Оплачено
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
            ) : invoices.length === 0 ? (
              <div style={{ padding: "2rem", textAlign: "center" }}>
                <p>Нет счетов к получению</p>
              </div>
            ) : (
              <div className={styles.tableWrap}>
                <Table>
                  <TableHeader>
                    <TableRow>
                      {/* <TableHead>Номер счета</TableHead> */}
                      <TableHead>Дата</TableHead>
                      <TableHead>Срок оплаты</TableHead>
                      <TableHead>Сумма</TableHead>
                      <TableHead>Оплачено</TableHead>
                      <TableHead>Статус</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {invoices.map((invoice) => (
                      <TableRow key={invoice.id}>
                        {/* <TableCell className={styles.invoiceNumber}>{invoice.invoice_number}</TableCell> */}
                        <TableCell>{formatDate(invoice.invoice_date)}</TableCell>
                        <TableCell>
                          {formatDate(invoice.due_date)}
                          {invoice.days_overdue && invoice.days_overdue > 0 && (
                            <span className={styles.overdueDays}> ({invoice.days_overdue} дн.)</span>
                          )}
                        </TableCell>
                        <TableCell className={styles.amount}>
                          ₽{invoice.amount.toLocaleString("ru-RU", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </TableCell>
                        <TableCell className={styles.paidAmount}>
                          ₽{invoice.paid_amount.toLocaleString("ru-RU", {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2,
                          })}
                        </TableCell>
                        <TableCell>{getStatusBadge(invoice.status)}</TableCell>
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

