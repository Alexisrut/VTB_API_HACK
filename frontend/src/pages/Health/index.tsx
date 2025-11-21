import Layout from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { TrendingUp, TrendingDown, AlertCircle, DollarSign } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { getHealthMetrics, type HealthMetricsResponse } from "../../utils/api";
import StatCard from "../../components/StatCard";
import CashFlowChart from "../../components/CashFlowChart";
import styles from "./index.module.scss";
import { toast } from "sonner";
import { useMe } from "../../hooks/context";
import cn from "classnames";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../../ui/tooltip";

type ValueVariant = "positive" | "warning" | "danger" | "neutral";

type Insight = {
  id: string;
  label: string;
  value: string;
  variant: ValueVariant;
  tooltip: string;
  description: string;
};

const formatCurrency = (value?: number | null, fallback = "—") => {
  if (value === undefined || value === null || Number.isNaN(value)) {
    return fallback;
  }
  return `₽${value.toLocaleString("ru-RU")}`;
};

const formatDateShort = (value?: string | null) => {
  if (!value) return null;
  return new Date(value).toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "short",
  });
};

const getTrendText = (trend?: string | null) => {
  switch (trend) {
    case "increasing":
      return "Рост";
    case "decreasing":
      return "Снижение";
    case "stable":
      return "Стабильно";
    default:
      return "Нет данных";
  }
};

const getTrendTooltip = (trend?: string | null) => {
  switch (trend) {
    case "increasing":
      return "Притоки растут быстрее оттоков. Можно планировать инвестиции.";
    case "decreasing":
      return "Баланс снижается. Проверьте расходы и ожидаемые поступления.";
    case "stable":
      return "Денежный поток стабильный без резких изменений.";
    default:
      return "Недостаточно данных для анализа тренда.";
  }
};

const getHealthStatusColor = (status?: string | null) => {
  switch (status?.toLowerCase()) {
    case "excellent":
      return "#10b981";
    case "good":
      return "#3b82f6";
    case "fair":
      return "#f59e0b";
    case "poor":
      return "#ef4444";
    case "critical":
      return "#dc2626";
    default:
      return "#6b7280";
  }
};

const getHealthStatusText = (status?: string | null) => {
  switch (status?.toLowerCase()) {
    case "excellent":
      return "Отлично";
    case "good":
      return "Хорошо";
    case "fair":
      return "Удовлетворительно";
    case "poor":
      return "Плохо";
    case "critical":
      return "Критично";
    default:
      return "Не определено";
  }
};

export default function FinancialAnalytics() {
  const me = useMe();
  const [metrics, setMetrics] = useState<HealthMetricsResponse["metrics"] | null>(null);
  const [period, setPeriod] = useState<HealthMetricsResponse["period"] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMonths, setSelectedMonths] = useState<number>(1);

  useEffect(() => {
    if (!me) {
      setIsLoading(false);
      setMetrics(null);
      return;
    }

    const today = new Date();
    const periodEndStr = today.toISOString().split("T")[0];
    const startDate = new Date(today);
    startDate.setMonth(startDate.getMonth() - selectedMonths);
    const periodStartStr = startDate.toISOString().split("T")[0];

    const fetchMetrics = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await getHealthMetrics(periodStartStr, periodEndStr);
        if (response.data.success && response.data.metrics) {
          setMetrics(response.data.metrics);
          setPeriod(response.data.period ?? null);
        } else {
          let errorMessage = "Не удалось загрузить метрики";
          if (response.data.error) {
            errorMessage =
              typeof response.data.error === "string"
                ? response.data.error
                : JSON.stringify(response.data.error);
          }
          setError(errorMessage);
        }
      } catch (err: any) {
        console.error("Error fetching health metrics:", err);
        let errorMessage = "Ошибка загрузки данных";
        const data = err.response?.data;
        if (data) {
          if (typeof data.detail === "string") errorMessage = data.detail;
          else if (data.detail) errorMessage = JSON.stringify(data.detail);
          else if (typeof data.error === "string") errorMessage = data.error;
          else if (data.error) errorMessage = JSON.stringify(data.error);
        }
        setError(errorMessage);
        toast.error("Не удалось загрузить финансовые метрики");
      } finally {
        setIsLoading(false);
      }
    };

    fetchMetrics();
  }, [me, selectedMonths]);
  const periodOptions = useMemo(
    () => [1, 2, 3, 4, 5, 6],
    []
  );

  const renderValueWithTooltip = (
    value: string,
    tooltipText: string,
    variant: ValueVariant = "neutral"
  ) => (
    <Tooltip>
      <TooltipTrigger asChild>
        <strong className={cn(styles.metricValue, styles[variant])}>{value}</strong>
      </TooltipTrigger>
      <TooltipContent>{tooltipText}</TooltipContent>
    </Tooltip>
  );

  const revenue = metrics?.revenue;
  const balance = metrics?.balance;
  const liquidity = metrics?.liquidity;
  const receivables = metrics?.accounts_receivable;
  const cashFlow = metrics?.cash_flow;
  const health = metrics?.health;

  const netIncome = revenue?.net_income ?? null;
  const currentRatio = liquidity?.current_ratio ?? null;
  const quickRatio = liquidity?.quick_ratio ?? null;
  const totalAR = receivables?.total ?? null;
  const overdueAR = receivables?.overdue ?? null;
  const overdueRatio =
    receivables && receivables.total > 0 ? receivables.overdue / receivables.total : null;
  const ocf = cashFlow?.operating_cash_flow ?? null;

  const netIncomeVariant: ValueVariant =
    netIncome === null ? "neutral" : netIncome > 0 ? "positive" : netIncome < 0 ? "danger" : "warning";
  const ratioVariant: ValueVariant =
    currentRatio === null
      ? "neutral"
      : currentRatio >= 2
      ? "positive"
      : currentRatio >= 1
      ? "warning"
      : "danger";
  const overdueVariant: ValueVariant =
    overdueRatio === null
      ? "neutral"
      : overdueRatio > 0.5
      ? "danger"
      : overdueRatio > 0.2
      ? "warning"
      : "positive";
  const ocfVariant: ValueVariant =
    ocf === null ? "neutral" : ocf > 0 ? "positive" : ocf < 0 ? "danger" : "warning";
  const cashTrendVariant: ValueVariant =
    cashFlow?.trend === "increasing"
      ? "positive"
      : cashFlow?.trend === "decreasing"
      ? "danger"
      : cashFlow?.trend === "stable"
      ? "warning"
      : "neutral";

  const periodText = useMemo(() => {
    if (!period) return null;
    const start = formatDateShort(period.start);
    const end = formatDateShort(period.end);
    if (!start || !end) return null;
    return `${start} — ${end}`;
  }, [period]);

  const insights = useMemo<Insight[]>(() => {
    const result: Insight[] = [];

    if (revenue) {
      result.push({
        id: "net_income",
        label: "Чистая прибыль",
        value: formatCurrency(netIncome),
        variant: netIncomeVariant,
        tooltip: "Доходы минус расходы за выбранный период.",
        description:
          netIncomeVariant === "positive"
            ? "Компания зарабатывает больше, чем тратит."
            : netIncomeVariant === "danger"
            ? "Расходы превышают доходы — пересмотрите бюджет."
            : "Баланс по прибыли около нуля.",
      });
    }

    if (receivables) {
      result.push({
        id: "overdue_ar",
        label: "Просроченная ДЗ",
        value: formatCurrency(overdueAR),
        variant: overdueVariant,
        tooltip: "Сумма счетов, по которым нарушен срок оплаты.",
        description:
          overdueRatio === null
            ? "Нет данных о дебиторке."
            : overdueRatio === 0
            ? "Просрочки нет — платят вовремя."
            : `Просрочено ${(overdueRatio * 100).toFixed(0)}% от общей суммы.`,
      });
    }

    if (liquidity) {
      result.push({
        id: "liquidity",
        label: "Коэф. текущей ликвидности",
        value: currentRatio !== null ? currentRatio.toFixed(2) : "—",
        variant: ratioVariant,
        tooltip: "Способность погасить краткосрочные обязательства.",
        description:
          ratioVariant === "positive"
            ? "Запас ликвидности комфортный."
            : ratioVariant === "warning"
            ? "Пограничное значение — держите под контролем."
            : "Недостаточная ликвидность, нужна подушка.",
      });
    }

    if (cashFlow) {
      result.push({
        id: "cash_flow",
        label: "Операционный поток",
        value: formatCurrency(ocf),
        variant: ocfVariant,
        tooltip: "Разница между поступлениями и выплатами в операционной деятельности.",
        description:
          ocfVariant === "positive"
            ? "Денежный поток устойчиво положительный."
            : ocfVariant === "danger"
            ? "Операционный поток отрицательный — проверьте поступления."
            : "Нейтральный поток, рост не наблюдается.",
      });
    }

    return result;
  }, [
    revenue,
    receivables,
    liquidity,
    cashFlow,
    netIncomeVariant,
    overdueVariant,
    ratioVariant,
    ocfVariant,
    overdueRatio,
    ocf,
    overdueAR,
    netIncome,
    currentRatio,
  ]);

  const insightVariantClassMap: Record<ValueVariant, string> = {
    positive: styles.insightPositive,
    warning: styles.insightWarning,
    danger: styles.insightDanger,
    neutral: styles.insightNeutral,
  };

  if (!me) {
    return (
      <TooltipProvider delayDuration={150}>
        <Layout>
          <Card>
            <CardHeader>
              <CardTitle>Финансовая аналитика</CardTitle>
            </CardHeader>
            <CardContent>
              <p>Войдите, чтобы увидеть актуальные метрики по вашим счетам.</p>
            </CardContent>
          </Card>
        </Layout>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider delayDuration={150}>
      <Layout>
        <div className={styles.container}>
          <div className={styles.header}>
            <h1>Финансовая аналитика</h1>
            <p>Ключевые показатели компании на основе реальных банковских данных</p>
            <div className={styles.periodSelector}>
              <label htmlFor="periodSelect">Период анализа (месяцы)</label>
              <div className={styles.selectWrapper}>
                <select
                  id="periodSelect"
                  value={selectedMonths}
                  onChange={(event) => setSelectedMonths(parseInt(event.target.value, 10))}
                >
                  {periodOptions.map((months) => (
                    <option key={months} value={months}>
                      {months}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {periodText || health?.status ? (
            <div className={styles.contextBar}>
              {periodText && <span>Период анализа: {periodText}</span>}
              {health?.status && (
                <span
                  className={styles.statusPill}
                  style={{
                    backgroundColor: `${getHealthStatusColor(health.status)}1a`,
                    color: getHealthStatusColor(health.status),
                  }}
                >
                  Статус: {getHealthStatusText(health.status)}
                </span>
              )}
            </div>
          ) : null}

          {isLoading ? (
            <Card>
              <CardContent style={{ padding: "2rem", textAlign: "center" }}>
                <p>Загрузка данных...</p>
              </CardContent>
            </Card>
          ) : error ? (
            <Card>
              <CardContent style={{ padding: "2rem", textAlign: "center", color: "#ef4444" }}>
                <p>{error}</p>
              </CardContent>
            </Card>
          ) : !metrics ? (
            <Card>
              <CardContent style={{ padding: "2rem", textAlign: "center" }}>
                <p>Нет данных для отображения</p>
                <p style={{ fontSize: "0.875rem", marginTop: "0.5rem" }}>
                  Подключите банковские счета для расчета метрик
                </p>
              </CardContent>
            </Card>
          ) : (
            <>
              {insights.length > 0 && (
                <div className={styles.insightsGrid}>
                  {insights.map((insight) => (
                    <div
                      key={insight.id}
                      className={cn(styles.insightCard, insightVariantClassMap[insight.variant])}
                    >
                      <div className={styles.insightHeader}>
                        <span>{insight.label}</span>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className={styles.insightValue}>{insight.value}</span>
                          </TooltipTrigger>
                          <TooltipContent>{insight.tooltip}</TooltipContent>
                        </Tooltip>
                      </div>
                      <p className={styles.insightDescription}>{insight.description}</p>
                    </div>
                  ))}
                </div>
              )}

              <div className={styles.metricsGrid}>
                <StatCard
                  title="Доходы"
                  value={formatCurrency(revenue?.total)}
                  subtitle="Сумма входящих платежей"
                  icon={TrendingUp}
                  variant="success"
                  tooltip="Все кредитовые обороты по счетам за период."
                />
                <StatCard
                  title="Расходы"
                  value={formatCurrency(revenue?.expenses)}
                  subtitle="Сумма исходящих платежей"
                  icon={TrendingDown}
                  variant="danger"
                  tooltip="Все дебетовые обороты по счетам за период."
                />
                <StatCard
                  title="Чистая прибыль"
                  value={formatCurrency(netIncome)}
                  subtitle={
                    netIncomeVariant === "positive"
                      ? "Положительное сальдо"
                      : netIncomeVariant === "danger"
                      ? "Расходы выше доходов"
                      : "Баланс около нуля"
                  }
                  icon={DollarSign}
                  variant={
                    netIncomeVariant === "danger"
                      ? "danger"
                      : netIncomeVariant === "warning"
                      ? "warning"
                      : "success"
                  }
                  tooltip="Доходы минус расходы без учета налогов."
                />
                <StatCard
                  title="Дебиторская задолженность"
                  value={formatCurrency(totalAR)}
                  subtitle={`Просрочено: ${formatCurrency(overdueAR)}`}
                  icon={AlertCircle}
                  variant="warning"
                  tooltip="Счета к получению, ожидаемые от клиентов."
                />
              </div>

              <div className={styles.detailsGrid}>
                <Card>
                  <CardHeader>
                    <CardTitle>Ликвидность</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className={styles.metricRow}>
                      <span>Коэффициент текущей ликвидности</span>
                      {renderValueWithTooltip(
                        currentRatio !== null ? currentRatio.toFixed(2) : "—",
                        "Отношение оборотных активов к краткосрочным обязательствам.",
                        ratioVariant
                      )}
                    </div>
                    <div className={styles.metricRow}>
                      <span>Коэффициент быстрой ликвидности</span>
                      {renderValueWithTooltip(
                        quickRatio !== null ? quickRatio.toFixed(2) : "—",
                        "Материальные запасы исключены. Показывает мгновенную платежеспособность.",
                        quickRatio !== null && quickRatio >= 1
                          ? "positive"
                          : quickRatio !== null && quickRatio >= 0.7
                          ? "warning"
                          : quickRatio !== null
                          ? "danger"
                          : "neutral"
                      )}
                    </div>
                    {receivables && (
                      <div className={styles.metricRow}>
                        <span>Оборачиваемость ДЗ</span>
                        {renderValueWithTooltip(
                          receivables.turnover_days ? `${receivables.turnover_days.toFixed(0)} дн.` : "—",
                          "Сколько дней в среднем требуется для оплаты счетов.",
                          receivables.turnover_days && receivables.turnover_days <= 30
                            ? "positive"
                            : receivables.turnover_days && receivables.turnover_days <= 45
                            ? "warning"
                            : receivables.turnover_days
                            ? "danger"
                            : "neutral"
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Денежный поток</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className={styles.metricRow}>
                      <span>Операционный денежный поток</span>
                      {renderValueWithTooltip(
                        formatCurrency(ocf),
                        "Основные поступления минус выплаты по операционной деятельности.",
                        ocfVariant
                      )}
                    </div>
                    <div className={styles.metricRow}>
                      <span>Тренд</span>
                      {renderValueWithTooltip(
                        getTrendText(cashFlow?.trend),
                        getTrendTooltip(cashFlow?.trend),
                        cashTrendVariant
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Активы и обязательства</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className={styles.metricRow}>
                      <span>Общие активы</span>
                      {renderValueWithTooltip(
                        formatCurrency(balance?.total_assets),
                        "Сумма средств на всех активных счетах.",
                        "neutral"
                      )}
                    </div>
                    <div className={styles.metricRow}>
                      <span>Обязательства</span>
                      {renderValueWithTooltip(
                        formatCurrency(balance?.total_liabilities),
                        "Краткосрочные обязательства, учтённые при расчёте.",
                        "neutral"
                      )}
                    </div>
                    <div className={styles.metricRow}>
                      <span>Чистая стоимость</span>
                      {renderValueWithTooltip(
                        formatCurrency(balance?.net_worth),
                        "Разница между активами и обязательствами.",
                        balance && balance.net_worth > 0 ? "positive" : "warning"
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className={styles.cashFlowSection}>
                <CashFlowChart />
              </div>
            </>
          )}
        </div>
      </Layout>
    </TooltipProvider>
  );
}
