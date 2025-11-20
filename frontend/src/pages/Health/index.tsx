import Layout from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { Heart, TrendingUp, TrendingDown, AlertCircle, DollarSign } from "lucide-react";
import { useEffect, useState } from "react";
import { getHealthMetrics, type HealthMetrics } from "../../utils/api";
import StatCard from "../../components/StatCard";
import CashFlowChart from "../../components/CashFlowChart";
import styles from "./index.module.scss";
import { toast } from "sonner";
import { useMe } from "../../hooks/context";

export default function Health() {
  const me = useMe();
  const [metrics, setMetrics] = useState<HealthMetrics["metrics"] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) {
      setIsLoading(false);
      return;
    }

    const fetchMetrics = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await getHealthMetrics();
        if (response.data.success && response.data.metrics) {
          setMetrics(response.data.metrics);
        } else {
          setError(response.data.error || "Не удалось загрузить метрики");
        }
      } catch (err: any) {
        console.error("Error fetching health metrics:", err);
        setError(err.response?.data?.detail || "Ошибка загрузки данных");
        toast.error("Не удалось загрузить метрики финансового здоровья");
      } finally {
        setIsLoading(false);
      }
    };

    fetchMetrics();
  }, [me]);

  const getHealthStatusColor = (status?: string) => {
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

  const getHealthStatusText = (status?: string) => {
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

  if (!me) {
    return (
      <Layout>
        <Card>
          <CardHeader>
            <CardTitle>Финансовое здоровье</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Войдите, чтобы увидеть метрики финансового здоровья</p>
          </CardContent>
        </Card>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className={styles.container}>
        <div className={styles.header}>
          <h1>Финансовое здоровье</h1>
          <p>Анализ финансового состояния и ключевые метрики</p>
        </div>

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
            <div className={styles.healthScore}>
              <Card>
                <CardContent className={styles.scoreContent}>
                  <div className={styles.scoreCircle}>
                    <div
                      className={styles.scoreValue}
                      style={{ color: getHealthStatusColor(metrics.health_status) }}
                    >
                      {metrics.health_score || 0}
                    </div>
                    <div className={styles.scoreLabel}>Health Score</div>
                  </div>
                  <div className={styles.scoreStatus}>
                    <div
                      className={styles.statusBadge}
                      style={{ backgroundColor: getHealthStatusColor(metrics.health_status) }}
                    >
                      {getHealthStatusText(metrics.health_status)}
                    </div>
                    <p className={styles.statusDescription}>
                      {metrics.health_status === "excellent" && "Ваше финансовое состояние отличное"}
                      {metrics.health_status === "good" && "Ваше финансовое состояние хорошее"}
                      {metrics.health_status === "fair" && "Есть области для улучшения"}
                      {metrics.health_status === "poor" && "Требуется внимание к финансам"}
                      {metrics.health_status === "critical" && "Критическая ситуация, требуется срочное действие"}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className={styles.metricsGrid}>
              <StatCard
                title="Доходы"
                value={`₽${(metrics.total_revenue || 0).toLocaleString()}`}
                subtitle="За период"
                icon={TrendingUp}
                variant="success"
              />
              <StatCard
                title="Расходы"
                value={`₽${(metrics.total_expenses || 0).toLocaleString()}`}
                subtitle="За период"
                icon={TrendingDown}
                variant="danger"
              />
              <StatCard
                title="Чистая прибыль"
                value={`₽${(metrics.net_income || 0).toLocaleString()}`}
                subtitle={metrics.net_income && metrics.net_income >= 0 ? "Положительный" : "Отрицательный"}
                icon={DollarSign}
                variant={metrics.net_income && metrics.net_income >= 0 ? "success" : "danger"}
              />
              <StatCard
                title="Дебиторская задолженность"
                value={`₽${(metrics.total_ar || 0).toLocaleString()}`}
                subtitle={`Просрочено: ₽${(metrics.overdue_ar || 0).toLocaleString()}`}
                icon={AlertCircle}
                variant="warning"
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
                    <strong>{metrics.current_ratio?.toFixed(2) || "—"}</strong>
                  </div>
                  <div className={styles.metricRow}>
                    <span>Коэффициент быстрой ликвидности</span>
                    <strong>{metrics.quick_ratio?.toFixed(2) || "—"}</strong>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Денежный поток</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className={styles.metricRow}>
                    <span>Операционный денежный поток</span>
                    <strong>₽{(metrics.operating_cash_flow || 0).toLocaleString()}</strong>
                  </div>
                  <div className={styles.metricRow}>
                    <span>Тренд</span>
                    <strong>{metrics.cash_flow_trend || "—"}</strong>
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
                    <strong>₽{(metrics.total_assets || 0).toLocaleString()}</strong>
                  </div>
                  <div className={styles.metricRow}>
                    <span>Обязательства</span>
                    <strong>₽{(metrics.total_liabilities || 0).toLocaleString()}</strong>
                  </div>
                  <div className={styles.metricRow}>
                    <span>Чистая стоимость</span>
                    <strong>₽{(metrics.net_worth || 0).toLocaleString()}</strong>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Cash Flow Forecast Section */}
            <div className={styles.cashFlowSection}>
              <CashFlowChart />
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}

