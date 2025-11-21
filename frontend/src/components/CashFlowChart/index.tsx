import { Card, CardContent, CardHeader, CardTitle } from "../../ui/card";
import { TrendingUp } from "lucide-react";
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
import { useEffect, useMemo, useState } from "react";
import { getCashFlowPredictions } from "../../utils/api";
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
import { useMe } from "../../hooks/context";

// Утилита для создания HSL-цвета для Recharts (требуется для градиентов)
const getHslColor = (h: string, s: string, l: string) => `hsl(${h}, ${s}, ${l})`;

type ChartPoint = {
  date: string;
  balance: number;
  inflow: number;
  gapProbability?: number | null;
  gapAmount?: number | null;
};

export default function CashFlowChart() {
  const me = useMe();
  const [data, setData] = useState<ChartPoint[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentBalance, setCurrentBalance] = useState<number | null>(null);

  useEffect(() => {
    if (!me) {
      setData([]);
      setCurrentBalance(null);
      return;
    }

    const fetchPredictions = async () => {
      try {
        setIsLoading(true);
        setError(null);

        const response = await getCashFlowPredictions(4);

        if (response.data.success && response.data.predictions?.length) {
          const chartData: ChartPoint[] = response.data.predictions.map((p) => {
            const dateSource = p.date || (p as any).prediction_date;
            const dateLabel = dateSource
              ? new Date(dateSource).toLocaleDateString("ru-RU", {
                  day: "2-digit",
                  month: "short",
                })
              : `Неделя ${p.week}`;

            return {
              date: dateLabel,
              balance: p.predicted_balance,
              inflow: p.predicted_inflow,
              gapProbability: p.gap_probability,
              gapAmount: p.gap_amount,
            };
          });

          setData(chartData);
          setCurrentBalance(response.data.current_balance ?? null);
        } else {
          setData([]);
          setError(
            response.data.error ||
              "Нет данных прогноза. Попробуйте обновить позже."
          );
        }
      } catch (err: any) {
        console.error("Error fetching cash flow predictions:", err);
        const detail =
          err.response?.data?.detail ||
          err.response?.data?.error ||
          "Не удалось загрузить прогноз денежных потоков";
        setError(detail);
        setData([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPredictions();
  }, [me]);

  const primaryHslString = getHslColor(primaryHslParts[0], primaryHslParts[1], primaryHslParts[2]);
  const accentHslString = getHslColor(accentHslParts[0], accentHslParts[1], accentHslParts[2]);
  const RefLine = ReferenceLine;

  const hasData = data.length > 0;
  const highestRisk = useMemo(() => {
    if (!data.length) return null;
    return data.reduce((prev, curr) => {
      if (!curr.gapProbability) return prev;
      if (!prev || (curr.gapProbability || 0) > (prev.gapProbability || 0)) {
        return curr;
      }
      return prev;
    }, null as ChartPoint | null);
  }, [data]);

  return (
    <Card className={styles.chartCard}>
      <CardHeader className={styles.chartCardHeader}>
        <div className={styles.headerGroup}>
          <div className={styles.headerIconBg}>
            <TrendingUp className={styles.headerIcon} />
          </div>
          <div>
            <CardTitle className={styles.chartCardTitle}>Прогноз денежного потока</CardTitle>
            <p className={styles.chartCardSubtitle}>
              {hasData
                ? "Прогноз баланса и притока на следующие недели"
                : "Подключите счета для просмотра прогноза"}
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className={styles.chartCardContent}>
        {isLoading ? (
          <div style={{ padding: "2rem", textAlign: "center" }}>
            <p>Загрузка прогноза...</p>
          </div>
        ) : !hasData ? (
          <div style={{ padding: "2rem", textAlign: "center", color: muted_foreground }}>
            <p>{error || "Нет данных для отображения"}</p>
            <p style={{ fontSize: "0.875rem", marginTop: "0.5rem" }}>
              Попробуйте обновить страницу или подключить банковские счета
            </p>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                {/* Используем SCSS-переменные в SVG-градиентах */}
                <linearGradient id="colorBalance" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={primaryHslString} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={primaryHslString} stopOpacity={0.05} />
                </linearGradient>
                <linearGradient id="colorInflow" x1="0" y1="0" x2="0" y2="1">
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
                  backdropFilter: "blur(12px)",
                }}
                formatter={(value: number, name: string) => [
                  `₽${value.toLocaleString("ru-RU")}`,
                  name === "balance" ? "Баланс" : "Приток",
                ]}
              />
              <RefLine y={0} stroke={danger} strokeDasharray="5 5" strokeWidth={2} />
              <Area
                type="monotone"
                dataKey="balance"
                stroke={primary}
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#colorBalance)"
                name="Баланс"
                dot={{ fill: primary, r: 4 }}
              />
              <Area
                type="monotone"
                dataKey="inflow"
                stroke={accent}
                strokeWidth={3}
                strokeDasharray="8 4"
                fillOpacity={1}
                fill="url(#colorInflow)"
                name="Приток"
                dot={{ fill: accent, r: 4 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
        {hasData && (
          <>
            <div className={styles.legend}>
              <div className={styles.legendItem}>
                <div className={`${styles.legendDot} ${styles.dotActual}`} />
                <span className={styles.legendLabel}>Баланс</span>
              </div>
              <div className={styles.legendItem}>
                <div className={`${styles.legendDot} ${styles.dotPredicted}`} />
                <span className={styles.legendLabel}>Приток</span>
              </div>
            </div>
            <div className={styles.chartMeta}>
              {currentBalance !== null && (
                <p>
                  Текущий баланс:{" "}
                  <strong>₽{currentBalance.toLocaleString("ru-RU")}</strong>
                </p>
              )}
              {highestRisk?.gapProbability && (
                <p>
                  Максимальный риск кассового разрыва:{" "}
                  <strong>{highestRisk.gapProbability.toFixed(0)}%</strong>
                  {highestRisk.gapAmount && (
                    <>
                      {" "}
                      (≈₽{Math.abs(highestRisk.gapAmount).toLocaleString("ru-RU")})
                    </>
                  )}
                </p>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}