import Layout from "../../components/Layout";
import StatCard from "../../components/StatCard";
import CashFlowChart from "../../components/CashFlowChart";
import BankAccountsList from "../../components/BankAccountList";
import ReceivablesTable from "../../components/ReceivablesTable";
import { Wallet, TrendingUp, TrendingDown, AlertCircle, CircleUser } from "lucide-react";
import styles from "./index.module.scss";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AuthModal } from "../Auth";
import { useAuth } from "../../hooks/useAuth";

export default function Index() {

  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();

  const handleUserClick = () => {
    if (isAuthenticated) {
      navigate("/profile");
    } else {
      setIsAuthOpen(true);
    }
  };

  return (
    <Layout>

      <AuthModal 
        isOpen={isAuthOpen} 
        onClose={() => setIsAuthOpen(false)} 
      />

      <div className={styles.dashboardContainer}>
        
        <div className={styles.headerSection}>
          <div className={styles.headerRow}>
          <h1 className={styles.mainTitle}>Дашборд</h1>
          <button 
              className={styles.userButton}
              onClick={handleUserClick}
              aria-label={isAuthenticated ? "Профиль" : "Войти"}
            >
              <CircleUser size={24} />
          </button>
          </div>
          <p className={styles.subtitle}>
            Финансовый обзор и ключевые показатели
          </p>
        </div>

        <div className={styles.statsGrid}>
          <StatCard
            title="Общий баланс"
            value="₽480,000"
            subtitle="всех аккаунтов"
            icon={Wallet}
            variant="default"
            trend={{ value: "12.5%", isPositive: true }}
          />
          <StatCard
            title="Ожидаемый доход"
            value="₽85,000"
            subtitle="следующие 30 дней"
            icon={TrendingUp}
            variant="success"
            trend={{ value: "8.2%", isPositive: true }}
          />
          <StatCard
            title="Задолженности"
            value="₽35,000"
            subtitle="..."
            icon={AlertCircle}
            variant="danger"
          />
           <StatCard
            title="Просто карточка"
            value="₽190,000"
            subtitle="Дада"
            icon={TrendingDown}
            variant="warning"
          />
          
        </div>

        <div className={styles.chartsGrid}>
          <CashFlowChart />
          <BankAccountsList />
        </div>

        <ReceivablesTable />
      </div>
    </Layout>
  );
}