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
import { useEffect, useState } from "react";
import { useAuth } from "../../hooks/useAuth";
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

// Утилита для создания HSL-цвета для Recharts (требуется для градиентов)
const getHslColor = (h: string, s: string, l: string) => `hsl(${h}, ${s}, ${l})`;

export default function CashFlowChart() {
  const { isAuthenticated } = useAuth();
  const [data, setData] = useState<Array<{ date: string; actual: number | null; predicted: number | null }>>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      setData([]);
      return;
    }

    // Используем захардкоженные данные для демонстрации
    const today = new Date();
    const mockChartData = [
      {
        date: new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000).toLocaleDateString("ru-RU", {
          day: "2-digit",
          month: "short",
        }),
        actual: null,
        predicted: 1250000,
      },
      {
        date: new Date(today.getTime() + 14 * 24 * 60 * 60 * 1000).toLocaleDateString("ru-RU", {
          day: "2-digit",
          month: "short",
        }),
        actual: null,
        predicted: 980000,
      },
      {
        date: new Date(today.getTime() + 21 * 24 * 60 * 60 * 1000).toLocaleDateString("ru-RU", {
          day: "2-digit",
          month: "short",
        }),
        actual: null,
        predicted: -120000,
      },
      {
        date: new Date(today.getTime() + 28 * 24 * 60 * 60 * 1000).toLocaleDateString("ru-RU", {
          day: "2-digit",
          month: "short",
        }),
        actual: null,
        predicted: 340000,
      },
    ];

    setTimeout(() => {
      setData(mockChartData);
      setIsLoading(false);
    }, 300);

    /* Закомментирован реальный API вызов
    const fetchPredictions = async () => {
      try {
        setIsLoading(true);
        const response = await getCashFlowPredictions(4);
        if (response.data.success && response.data.predictions) {
          const chartData = response.data.predictions.map((p) => ({
            date: new Date(p.prediction_date).toLocaleDateString("ru-RU", {
              day: "2-digit",
              month: "short",
            }),
            actual: null,
            predicted: p.predicted_balance,
          }));
          setData(chartData);
        }
      } catch (err) {
        console.error("Error fetching cash flow predictions:", err);
        setData([]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchPredictions();
    */
  }, [isAuthenticated]);

  const primaryHslString = getHslColor(primaryHslParts[0], primaryHslParts[1], primaryHslParts[2]);
  const accentHslString = getHslColor(accentHslParts[0], accentHslParts[1], accentHslParts[2]);
  const RefLine = ReferenceLine;
  
  const hasData = data.length > 0;
  
  return (
    <Card className={styles.chartCard}>
      <CardHeader className={styles.chartCardHeader}>
        <div className={styles.headerGroup}>
          <div className={styles.headerIconBg}>
            <TrendingUp className={styles.headerIcon} />
          </div>
          <div>
            <CardTitle className={styles.chartCardTitle}>Cash Flow прогноз</CardTitle>
            <p className={styles.chartCardSubtitle}>
              {hasData ? "Наши предсказания баланса на следующие 4 недели" : "Подключите счета для просмотра прогноза"}
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
            <p>Нет данных для отображения</p>
            <p style={{ fontSize: "0.875rem", marginTop: "0.5rem" }}>
              Подключите банковские счета, чтобы увидеть прогноз денежного потока
            </p>
          </div>
        ) : (
        <ResponsiveContainer width="100%" height={320}>
          <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              {/* Используем SCSS-переменные в SVG-градиентах */}
              <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={primaryHslString} stopOpacity={0.4} />
                <stop offset="95%" stopColor={primaryHslString} stopOpacity={0.05} />
              </linearGradient>
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
                backdropFilter: "blur(12px)",
              }}
              formatter={(value: number) => [`₽${value.toLocaleString()}`, ""]}
            />
            <RefLine y={0} stroke={danger} strokeDasharray="5 5" strokeWidth={2} />
            <Area
              type="monotone"
              dataKey="actual"
              stroke={primary}
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#colorActual)"
              name="Actual"
              dot={{ fill: primary, r: 4 }}
              />
            <Area
              type="monotone"
              dataKey="predicted"
              stroke={accent}
              strokeWidth={3}
              strokeDasharray="8 4"
              fillOpacity={1}
              fill="url(#colorPredicted)"
              name="Predicted"
              dot={{ fill: accent, r: 4 }}
            />
          </AreaChart>
        </ResponsiveContainer>
        )}
        {hasData && <div className={styles.legend}>
          <div className={styles.legendItem}>
            <div className={`${styles.legendDot} ${styles.dotActual}`} />
            <span className={styles.legendLabel}>Баланс</span>
          </div>
          <div className={styles.legendItem}>
            <div className={`${styles.legendDot} ${styles.dotPredicted}`} />
            <span className={styles.legendLabel}>Наш прогноз</span>
          </div>
        </div>}
      </CardContent>
    </Card>
  );
}