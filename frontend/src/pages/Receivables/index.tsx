import Layout from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Badge } from "../../ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../ui/table";
import { Users, AlertCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
import { getInvoices, getARSummary, type Invoice, type ARSummary } from "../../utils/api";
import StatCard from "../../components/StatCard";
import styles from "./index.module.scss";
import { toast } from "sonner";

export default function Receivables() {
  const { isAuthenticated } = useAuth();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [summary, setSummary] = useState<ARSummary["summary"] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  useEffect(() => {
    if (!isAuthenticated) {
      setIsLoading(false);
      return;
    }

    // Используем захардкоженные данные для демонстрации
    const mockSummary = {
      total_ar: 2340000,
      overdue_ar: 340000,
      overdue_count: 3,
      pending_count: 8,
      paid_count: 12,
    };

    const allMockInvoices: Invoice[] = [
      {
        id: "inv-001",
        invoice_number: "INV-2024-001",
        counterparty_name: "ООО \"Альфа\"",
        invoice_date: "2024-11-01",
        due_date: "2024-11-15",
        amount: 450000,
        paid_amount: 450000,
        status: "paid",
        days_overdue: 0,
      },
      {
        id: "inv-002",
        invoice_number: "INV-2024-002",
        counterparty_name: "ООО \"Бета\"",
        invoice_date: "2024-11-03",
        due_date: "2024-11-17",
        amount: 320000,
        paid_amount: 320000,
        status: "paid",
        days_overdue: 0,
      },
      {
        id: "inv-003",
        invoice_number: "INV-2024-003",
        counterparty_name: "ООО \"Гамма\"",
        invoice_date: "2024-11-05",
        due_date: "2024-11-19",
        amount: 180000,
        paid_amount: 0,
        status: "pending",
        days_overdue: 0,
      },
      {
        id: "inv-004",
        invoice_number: "INV-2024-004",
        counterparty_name: "ООО \"Дельта\"",
        invoice_date: "2024-11-06",
        due_date: "2024-11-20",
        amount: 275000,
        paid_amount: 275000,
        status: "paid",
        days_overdue: 0,
      },
      {
        id: "inv-005",
        invoice_number: "INV-2024-005",
        counterparty_name: "ООО \"Эпсилон\"",
        invoice_date: "2024-11-07",
        due_date: "2024-11-21",
        amount: 95000,
        paid_amount: 0,
        status: "pending",
        days_overdue: 0,
      },
      {
        id: "inv-006",
        invoice_number: "INV-2024-006",
        counterparty_name: "ООО \"Зета\"",
        invoice_date: "2024-11-08",
        due_date: "2024-11-22",
        amount: 520000,
        paid_amount: 520000,
        status: "paid",
        days_overdue: 0,
      },
      {
        id: "inv-007",
        invoice_number: "INV-2024-007",
        counterparty_name: "ООО \"Эта\"",
        invoice_date: "2024-10-25",
        due_date: "2024-11-08",
        amount: 68000,
        paid_amount: 0,
        status: "overdue",
        days_overdue: 8,
      },
      {
        id: "inv-008",
        invoice_number: "INV-2024-008",
        counterparty_name: "ООО \"Тета\"",
        invoice_date: "2024-10-28",
        due_date: "2024-11-11",
        amount: 142000,
        paid_amount: 0,
        status: "overdue",
        days_overdue: 5,
      },
      {
        id: "inv-009",
        invoice_number: "INV-2024-009",
        counterparty_name: "ООО \"Йота\"",
        invoice_date: "2024-10-30",
        due_date: "2024-11-13",
        amount: 130000,
        paid_amount: 0,
        status: "overdue",
        days_overdue: 3,
      },
      {
        id: "inv-010",
        invoice_number: "INV-2024-010",
        counterparty_name: "ООО \"Каппа\"",
        invoice_date: "2024-11-10",
        due_date: "2024-11-24",
        amount: 385000,
        paid_amount: 0,
        status: "pending",
        days_overdue: 0,
      },
      {
        id: "inv-011",
        invoice_number: "INV-2024-011",
        counterparty_name: "ООО \"Лямбда\"",
        invoice_date: "2024-11-11",
        due_date: "2024-11-25",
        amount: 225000,
        paid_amount: 0,
        status: "pending",
        days_overdue: 0,
      },
      {
        id: "inv-012",
        invoice_number: "INV-2024-012",
        counterparty_name: "ООО \"Мю\"",
        invoice_date: "2024-11-12",
        due_date: "2024-11-26",
        amount: 198000,
        paid_amount: 0,
        status: "pending",
        days_overdue: 0,
      },
      {
        id: "inv-013",
        invoice_number: "INV-2024-013",
        counterparty_name: "ООО \"Ню\"",
        invoice_date: "2024-10-20",
        due_date: "2024-11-03",
        amount: 410000,
        paid_amount: 410000,
        status: "paid",
        days_overdue: 0,
      },
      {
        id: "inv-014",
        invoice_number: "INV-2024-014",
        counterparty_name: "ООО \"Кси\"",
        invoice_date: "2024-11-13",
        due_date: "2024-11-27",
        amount: 165000,
        paid_amount: 0,
        status: "pending",
        days_overdue: 0,
      },
      {
        id: "inv-015",
        invoice_number: "INV-2024-015",
        counterparty_name: "ООО \"Омикрон\"",
        invoice_date: "2024-11-14",
        due_date: "2024-11-28",
        amount: 290000,
        paid_amount: 0,
        status: "pending",
        days_overdue: 0,
      },
    ];

    setTimeout(() => {
      setSummary(mockSummary);
      
      // Фильтруем счета по статусу
      let filteredInvoices = allMockInvoices;
      if (statusFilter) {
        filteredInvoices = allMockInvoices.filter(inv => inv.status === statusFilter);
      }
      
      setInvoices(filteredInvoices);
      setIsLoading(false);
    }, 400);

    /* Закомментирован реальный API вызов
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
    */
  }, [isAuthenticated, statusFilter]);

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

  if (!isAuthenticated) {
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
                      <TableHead>Номер счета</TableHead>
                      <TableHead>Контрагент</TableHead>
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
                        <TableCell className={styles.invoiceNumber}>{invoice.invoice_number}</TableCell>
                        <TableCell>{invoice.counterparty_name}</TableCell>
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

