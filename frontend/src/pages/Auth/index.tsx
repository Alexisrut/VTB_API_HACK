import React from "react";
import styles from "./index.module.scss";
import { AuthForm } from "./AuthForm";
import cn from "classnames";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className={cn(styles.authOverlay, "auth-modal-overlay")}>
      <div className={styles.authBlur} onClick={onClose}></div>

      <div className={styles.authModal}>
        <AuthForm onClose={onClose} />
      </div>
    </div>
  );
};