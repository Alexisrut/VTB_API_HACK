import * as React from "react";
import cn from "classnames";
import styles from "./index.module.scss";

export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {}

const Label = React.forwardRef<HTMLLabelElement, LabelProps>(
  ({ className, ...props }, ref) => {
    return (
      <label
        className={cn(styles.label, className)}
        ref={ref}
        {...props}
      />
    );
  },
);
Label.displayName = "Label";

export { Label };

