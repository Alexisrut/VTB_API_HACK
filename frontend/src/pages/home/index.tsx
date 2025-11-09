import Layout from "../../components/Layout";
import StatCard from "../../components/StatCard";
import CashFlowChart from "../../components/CashFlowChart";
import BankAccountsList from "../../components/BankAccountList";
import ReceivablesTable from "../../components/ReceivablesTable";
import Landing from "../Landing";
import { Wallet, TrendingUp, TrendingDown, AlertCircle, CircleUser } from "lucide-react";
import styles from "./index.module.scss";
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AuthModal } from "../Auth";
import { useAuth } from "../../hooks/useAuth";
import { getDashboardSummary, getAllBankAccounts, type DashboardSummary } from "../../utils/api";

export default function Index() {
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const navigate = useNavigate();
  const { isAuthenticated, isLoading } = useAuth();
  const [dashboardData, setDashboardData] = useState<DashboardSummary["summary"] | null>(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    const fetchDashboardData = async () => {
      try {
        setIsLoadingDashboard(true);
        const response = await getDashboardSummary();
        if (response.data.success && response.data.summary) {
          setDashboardData(response.data.summary);
        }
      } catch (err: any) {
        console.error("Error fetching dashboard summary:", err);
        // Don't show error toast - dashboard can work without summary
      } finally {
        setIsLoadingDashboard(false);
      }
    };

    fetchDashboardData();
  }, [isAuthenticated]);

  const handleUserClick = () => {
    if (isAuthenticated) {
      navigate("/profile");
    } else {
      setIsAuthOpen(true);
    }
  };

  // Show landing page if not authenticated
  if (!isAuthenticated && !isLoading) {
    return <Landing />;
  }

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <Layout>
        <div className={styles.dashboardContainer}>
          <div style={{ padding: "2rem", textAlign: "center" }}>
            <p>Загрузка...</p>
          </div>
        </div>
      </Layout>
    );
  }

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
              aria-label="Профиль"
              title="Профиль"
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
            value={dashboardData ? `₽${(dashboardData.total_balance || 0).toLocaleString()}` : "—"}
            subtitle={dashboardData ? `${dashboardData.accounts_count || 0} счетов` : "Загрузка..."}
            icon={Wallet}
            variant="default"
          />
          <StatCard
            title="Доходы"
            value={dashboardData ? `₽${(dashboardData.total_revenue || 0).toLocaleString()}` : "—"}
            subtitle={dashboardData ? "За период" : "Загрузка..."}
            icon={TrendingUp}
            variant="success"
          />
          <StatCard
            title="Дебиторская задолженность"
            value={dashboardData ? `₽${(dashboardData.total_ar || 0).toLocaleString()}` : "—"}
            subtitle={dashboardData ? `Просрочено: ₽${(dashboardData.overdue_ar || 0).toLocaleString()}` : "Загрузка..."}
            icon={AlertCircle}
            variant="danger"
          />
          <StatCard
            title="Чистая прибыль"
            value={dashboardData ? `₽${(dashboardData.net_income || 0).toLocaleString()}` : "—"}
            subtitle={dashboardData ? (dashboardData.net_income && dashboardData.net_income >= 0 ? "Положительная" : "Отрицательная") : "Загрузка..."}
            icon={TrendingDown}
            variant={dashboardData && dashboardData.net_income && dashboardData.net_income >= 0 ? "success" : "warning"}
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