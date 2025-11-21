import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "../../ui/card";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../../ui/tooltip";
import cn from "classnames"
import styles from "./index.module.scss";

type Variant = "default" | "success" | "warning" | "danger";

interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: LucideIcon;
  variant?: Variant;
  tooltip?: string;
  trend?: {
    value: string;
    isPositive: boolean;
  };
}

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  variant = "default",
  tooltip,
  trend,
}: StatCardProps) {


  const trendClass = trend?.isPositive
    ? styles.trendPositive
    : styles.trendNegative;

  return (
    <Card className={cn(styles.statCard, styles[variant])}>
      <CardContent className={styles.cardContent}>
        <div className={styles.contentWrapper}>

          <div className={styles.textSection}>
            <p className={styles.title}>{title}</p>
            {tooltip ? (
              <TooltipProvider delayDuration={150}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <p className={styles.value}>{value}</p>
                  </TooltipTrigger>
                  <TooltipContent>{tooltip}</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            ) : (
              <p className={styles.value}>{value}</p>
            )}

            {subtitle && (
              <p className={styles.subtitle}>{subtitle}</p>
            )}

            {trend && (
              <div className={styles.trendContainer}>
                <span className={cn(styles.trendBadge, trendClass)}>
                  {trend.isPositive ? "↗" : "↘"} {trend.value}
                </span>
              </div>
            )}
          </div>

          <div className={styles.iconBg}>
            <Icon className={styles.icon} strokeWidth={2.5} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}