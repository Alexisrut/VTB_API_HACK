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

const data = [
  { date: "01 Oct", actual: 450000, predicted: 450000 },
  { date: "05 Oct", actual: 380000, predicted: 385000 },
  { date: "10 Oct", actual: 520000, predicted: 530000 },
  { date: "15 Oct", actual: 480000, predicted: 490000 },
  { date: "20 Oct", actual: null, predicted: 420000 },
  { date: "25 Oct", actual: null, predicted: 560000 },
  { date: "30 Oct", actual: null, predicted: 510000 },
  { date: "05 Nov", actual: null, predicted: 490000 },
];

// Утилита для создания HSL-цвета для Recharts (требуется для градиентов)
const getHslColor = (h: string, s: string, l: string) => `hsl(${h}, ${s}, ${l})`;

export default function CashFlowChart() {
  const primaryHslString = getHslColor(primaryHslParts[0], primaryHslParts[1], primaryHslParts[2]);
  const accentHslString = getHslColor(accentHslParts[0], accentHslParts[1], accentHslParts[2]);
  const RefLine: any = ReferenceLine;
  
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
              Наши предсказания баланса на следующие 4 недели
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className={styles.chartCardContent}>
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
        <div className={styles.legend}>
          <div className={styles.legendItem}>
            <div className={`${styles.legendDot} ${styles.dotActual}`} />
            <span className={styles.legendLabel}>Баланс</span>
          </div>
          <div className={styles.legendItem}>
            <div className={`${styles.legendDot} ${styles.dotPredicted}`} />
            <span className={styles.legendLabel}>Наш прогноз</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}