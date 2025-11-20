import { Toaster as Sonner, toast } from "sonner";
import "./sonner.module.scss";

type ToasterProps = React.ComponentProps<typeof Sonner>;

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme="light"
      className="toaster group"
      {...props}
    />
  );
};

export { Toaster, toast };