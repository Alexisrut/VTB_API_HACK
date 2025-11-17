import Layout from "../../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { TrendingUp, AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";
import { getCashFlowPredictions, getCashFlowGaps, type CashFlowPrediction, type CashFlowGap } from "../../utils/api";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceLine,
} from "recharts";
import styles from "./index.module.scss";
import {
  primary,
  accent,
  danger,
  border,
  muted_foreground,
  popover,
  primaryHslParts,
  accentHslParts,
} from "../../styles/colors";
import { toast } from "sonner";
import { useMe } from "../../hooks/context";

const getHslColor = (h: string, s: string, l: string) => `hsl(${h}, ${s}, ${l})`;

export default function CashFlow() {
  const me = useMe();
  const [predictions, setPredictions] = useState<CashFlowPrediction["predictions"]>([]);
  const [gaps, setGaps] = useState<CashFlowGap["gaps"]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!me) {
      setIsLoading(false);
      return;
    }

    // Используем захардкоженные данные для демонстрации
    const today = new Date();
    const mockPredictions = [
      {
        prediction_date: new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        predicted_balance: 1250000,
        predicted_inflow: 850000,
        predicted_outflow: 620000,
        confidence: 0.85,
      },
      {
        prediction_date: new Date(today.getTime() + 14 * 24 * 60 * 60 * 1000).toISOString(),
        predicted_balance: 980000,
        predicted_inflow: 720000,
        predicted_outflow: 990000,
        confidence: 0.78,
      },
      {
        prediction_date: new Date(today.getTime() + 21 * 24 * 60 * 60 * 1000).toISOString(),
        predicted_balance: -120000,
        predicted_inflow: 450000,
        predicted_outflow: 1550000,
        confidence: 0.72,
      },
      {
        prediction_date: new Date(today.getTime() + 28 * 24 * 60 * 60 * 1000).toISOString(),
        predicted_balance: 340000,
        predicted_inflow: 1200000,
        predicted_outflow: 740000,
        confidence: 0.68,
      },
    ];

    const mockGaps = [
      {
        date: new Date(today.getTime() + 21 * 24 * 60 * 60 * 1000).toISOString(),
        gap_amount: -120000,
        probability: 72.5,
        severity: "Средняя",
      },
      {
        date: new Date(today.getTime() + 19 * 24 * 60 * 60 * 1000).toISOString(),
        gap_amount: -45000,
        probability: 58.3,
        severity: "Низкая",
      },
    ];

    // Имитируем задержку загрузки
    setTimeout(() => {
      setPredictions(mockPredictions);
      setGaps(mockGaps);
      setIsLoading(false);
    }, 500);

    /* Закомментирован реальный API вызов
    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const [predictionsRes, gapsRes] = await Promise.all([
          getCashFlowPredictions(4),
          getCashFlowGaps(4),
        ]);

        if (predictionsRes.data.success && predictionsRes.data.predictions) {
          setPredictions(predictionsRes.data.predictions);
        }

        if (gapsRes.data.success && gapsRes.data.gaps) {
          setGaps(gapsRes.data.gaps);
        }
      } catch (err: any) {
        console.error("Error fetching cash flow data:", err);
        setError(err.response?.data?.detail || "Ошибка загрузки данных");
        toast.error("Не удалось загрузить прогноз денежного потока");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
    */
  }, [me]);

  const primaryHslString = getHslColor(primaryHslParts[0], primaryHslParts[1], primaryHslParts[2]);
  const accentHslString = getHslColor(accentHslParts[0], accentHslParts[1], accentHslParts[2]);

  const chartData = predictions?.map((p) => ({
    date: new Date(p.prediction_date).toLocaleDateString("ru-RU", { day: "2-digit", month: "short" }),
    predicted: p.predicted_balance,
    inflow: p.predicted_inflow,
    outflow: p.predicted_outflow,
  })) || [];

  if (!me) {
    return (
      <Layout>
        <Card className={styles.card}>
          <CardHeader>
            <CardTitle>Cash Flow прогноз</CardTitle>
          </CardHeader>
          <CardContent>
            <p>Войдите, чтобы увидеть прогноз денежного потока</p>
          </CardContent>
        </Card>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className={styles.container}>
        <div className={styles.header}>
          <h1>Cash Flow прогноз</h1>
          <p>Прогнозирование денежного потока на следующие 4 недели</p>
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
        ) : chartData.length === 0 ? (
          <Card>
            <CardContent style={{ padding: "2rem", textAlign: "center" }}>
              <p>Нет данных для отображения</p>
              <p style={{ fontSize: "0.875rem", marginTop: "0.5rem", color: muted_foreground }}>
                Подключите банковские счета для получения прогноза
              </p>
            </CardContent>
          </Card>
        ) : (
          <>
            <Card className={styles.chartCard}>
              <CardHeader>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <TrendingUp className={styles.icon} />
                  <div>
                    <CardTitle>Прогноз баланса</CardTitle>
                    <p style={{ fontSize: "0.875rem", color: muted_foreground, marginTop: "0.25rem" }}>
                      Прогнозируемый баланс на следующие 4 недели
                    </p>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={320}>
                  <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={accentHslString} stopOpacity={0.4} />
                        <stop offset="95%" stopColor={accentHslString} stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={border} opacity={0.3} />
                    <XAxis
                      dataKey="date"
                      stroke={muted_foreground}
                      fontSize={12}
                      tickLine={false}
                      axisLine={{ stroke: border }}
                    />
                    <YAxis
                      stroke={muted_foreground}
                      fontSize={12}
                      tickLine={false}
                      axisLine={{ stroke: border }}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: popover,
                        border: `1px solid ${border}`,
                        borderRadius: "12px",
                      }}
                      formatter={(value: number) => [`₽${value.toLocaleString()}`, ""]}
                    />
                    <ReferenceLine y={0} stroke={danger} strokeDasharray="5 5" strokeWidth={2} />
                    <Area
                      type="monotone"
                      dataKey="predicted"
                      stroke={accent}
                      strokeWidth={3}
                      strokeDasharray="8 4"
                      fillOpacity={1}
                      fill="url(#colorPredicted)"
                      name="Прогноз"
                      dot={{ fill: accent, r: 4 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {gaps && gaps.length > 0 && (
              <Card className={styles.gapsCard}>
                <CardHeader>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <AlertTriangle className={styles.icon} style={{ color: danger }} />
                    <div>
                      <CardTitle>Потенциальные кассовые разрывы</CardTitle>
                      <p style={{ fontSize: "0.875rem", color: muted_foreground, marginTop: "0.25rem" }}>
                        Даты с высоким риском недостатка средств
                      </p>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className={styles.gapsList}>
                    {gaps.map((gap, index) => (
                      <div key={index} className={styles.gapItem}>
                        <div>
                          <p className={styles.gapDate}>{new Date(gap.date).toLocaleDateString("ru-RU")}</p>
                          <p className={styles.gapAmount}>₽{gap.gap_amount.toLocaleString()}</p>
                        </div>
                        <div className={styles.gapMeta}>
                          <span className={styles.gapProbability}>
                            Вероятность: {gap.probability.toFixed(1)}%
                          </span>
                          <span className={styles.gapSeverity}>{gap.severity}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}

