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
import { getDashboardSummary, getAllBankAccounts, getAccountBalances, extractBalanceFromResponse, getAccountId, type DashboardSummary } from "../../utils/api";

export default function Index() {
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const navigate = useNavigate();
  const { isAuthenticated, isLoading } = useAuth();
  const [dashboardData, setDashboardData] = useState<DashboardSummary["summary"] | null>(null);
  const [isLoadingDashboard, setIsLoadingDashboard] = useState(false);
  const [totalBalance, setTotalBalance] = useState<number | null>(null);
  const [accountsCount, setAccountsCount] = useState<number>(0);

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

  useEffect(() => {
    if (!isAuthenticated) {
      return;
    }

    const fetchBalances = async () => {
      try {
        console.log("[Dashboard] Fetching accounts and balances...");
        const accountsResponse = await getAllBankAccounts();
        const accountsData = accountsResponse.data;
        
        if (!accountsData.success) {
          console.warn("[Dashboard] Failed to get accounts");
          return;
        }

        let count = 0;
        const balancePromises: Promise<number>[] = [];

        Object.entries(accountsData.banks || {}).forEach(([bankCode, bankData]) => {
          if (bankData.success && bankData.accounts && bankData.accounts.length > 0) {
            count += bankData.accounts.length;
            
            bankData.accounts.forEach((account) => {
              const accountId = getAccountId(account);
              if (!accountId) {
                console.warn(`[Dashboard] Skipping account without account_id:`, account);
                return;
              }
              
              const balancePromise = getAccountBalances(
                accountId,
                bankCode,
                bankData.consent_id
              )
                .then((response) => {
                  console.log(`[Dashboard] Balance for account ${accountId}:`, response.data);
                  
                  // Извлекаем баланс из ответа
                  const balance = extractBalanceFromResponse(response);
                  console.log(`[Dashboard] Extracted balance for ${accountId}:`, balance);
                  return balance;
                })
                .catch((err) => {
                  console.error(`[Dashboard] Error fetching balance for account ${accountId}:`, err);
                  return 0;
                });
              
              balancePromises.push(balancePromise);
            });
          }
        });

        setAccountsCount(count);
        
        // Ждем все запросы и суммируем балансы
        const balances = await Promise.all(balancePromises);
        const total = balances.reduce((sum, balance) => sum + balance, 0);
        setTotalBalance(total);
        console.log(`[Dashboard] Total balance calculated: ${total}`);
      } catch (err: any) {
        console.error("[Dashboard] Error fetching balances:", err);
      }
    };

    fetchBalances();
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
            value={totalBalance !== null ? `₽${totalBalance.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : (dashboardData ? `₽${(dashboardData.total_balance || 0).toLocaleString()}` : "—")}
            subtitle={accountsCount > 0 ? `${accountsCount} счет${accountsCount === 1 ? "" : accountsCount < 5 ? "а" : "ов"}` : (dashboardData ? `${dashboardData.accounts_count || 0} счетов` : "Загрузка...")}
            icon={Wallet}
            variant="default"
          />
          <StatCard
            title="Доходы"
            value={dashboardData ? `₽${(dashboardData.total_revenue || 0).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
            subtitle={dashboardData ? "За последние 30 дней" : "Загрузка..."}
            icon={TrendingUp}
            variant="success"
          />
          <StatCard
            title="Дебиторская задолженность"
            value={dashboardData ? `₽${(dashboardData.total_ar || 0).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
            subtitle={dashboardData ? `Просрочено: ₽${(dashboardData.overdue_ar || 0).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "Загрузка..."}
            icon={AlertCircle}
            variant="danger"
          />
          <StatCard
            title="Чистая прибыль"
            value={dashboardData ? `₽${(dashboardData.net_income || 0).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "—"}
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