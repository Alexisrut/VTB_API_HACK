import * as React from "react";
import cn from "classnames";
import styles from "./index.module.scss";

type BadgeVariant = "default" | "secondary" | "destructive" | "outline";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: BadgeVariant;
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return <div className={cn(styles.badge, styles[variant], className)} {...props} />;
}

export { Badge };