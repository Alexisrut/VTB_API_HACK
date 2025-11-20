import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { 
  getAllBankAccounts, 
  getAccountBalances, 
  extractBalanceFromResponse, 
  getAccountId,
  type BankAccount,
  type BankConsent,
  getUserConsents,
  type ConsentsResponse
} from '../utils/api';
import { useMe } from './context';

interface BankData {
  accounts: BankAccount[];
  totalBalance: number;
  accountsCount: number;
  consents: Record<string, BankConsent>;
  isLoading: boolean;
  lastUpdated: number | null;
  refreshData: () => Promise<void>;
}

const BankDataContext = createContext<BankData | undefined>(undefined);

export const BankDataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const me = useMe();
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [totalBalance, setTotalBalance] = useState<number>(0);
  const [accountsCount, setAccountsCount] = useState<number>(0);
  const [consents, setConsents] = useState<Record<string, BankConsent>>({});
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const loadingRef = React.useRef(false);

  const loadData = useCallback(async (force: boolean = false) => {
    if (!me) return;
    
    // Если данные свежие (менее 5 минут) и не принудительное обновление, не загружаем заново
    if (!force && lastUpdated && Date.now() - lastUpdated < 5 * 60 * 1000) {
      console.log("[BankData] Data is fresh, skipping load");
      return;
    }

    // Prevent double loading
    if (loadingRef.current) {
      console.log("[BankData] Already loading, skipping");
      return;
    }

    try {
      loadingRef.current = true;
      setIsLoading(true);
      
      // 1. Загружаем согласия
      const consentsResponse = await getUserConsents();
      const consentsMap: Record<string, BankConsent> = {};
      (consentsResponse.data.consents || []).forEach((consent) => {
        consentsMap[consent.bank_code] = consent;
      });
      setConsents(consentsMap);

      // 2. Загружаем счета
      console.log("[BankData] Fetching accounts and balances...");
      const accountsResponse = await getAllBankAccounts();
      const accountsData = accountsResponse.data;
      console.log("[BankData] Accounts response:", accountsData);
      
      if (!accountsData.success) {
        console.warn("[BankData] Failed to get accounts");
        setIsLoading(false);
        return;
      }

      let count = 0;
      const allAccounts: BankAccount[] = [];
      const balancePromises: Promise<number>[] = [];

      Object.entries(accountsData.banks || {}).forEach(([bankCode, bankData]) => {
        if (bankData.success && bankData.accounts && bankData.accounts.length > 0) {
          console.log(`[BankData] Found ${bankData.accounts.length} accounts for ${bankCode}`);
          count += bankData.accounts.length;
          
          bankData.accounts.forEach((account) => {
            const accountId = getAccountId(account);
            if (!accountId) return;
            
            // Добавляем инфу о банке в аккаунт для удобства
            const accountWithBank = { ...account, bank_code: bankCode };
            allAccounts.push(accountWithBank);
            
            const balancePromise = getAccountBalances(
              accountId,
              bankCode,
              bankData.consent_id
            )
              .then((response) => {
                const balance = extractBalanceFromResponse(response);
                
                // Обновляем баланс в объекте аккаунта
                if (accountWithBank.balances && accountWithBank.balances.length > 0) {
                   // Если есть балансы, обновляем первый
                   if (accountWithBank.balances[0].balanceAmount) {
                     accountWithBank.balances[0].balanceAmount.amount = balance.toString();
                   }
                } else {
                  // Если нет балансов, создаем структуру
                  accountWithBank.balances = [{
                    balanceAmount: {
                      amount: balance.toString(),
                      currency: "RUB"
                    },
                    balanceType: "InterimAvailable",
                    creditDebitIndicator: "Credit"
                  }];
                }
                
                return balance;
              })
              .catch((err) => {
                console.error(`[BankData] Error fetching balance for ${accountId}:`, err);
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
      setAccounts(allAccounts);
      setLastUpdated(Date.now());
      console.log(`[BankData] Data updated. Total balance: ${total}`);
      
    } catch (error) {
      console.error("[BankData] Error loading data:", error);
    } finally {
      setIsLoading(false);
      loadingRef.current = false;
    }
  }, [me, lastUpdated]);

  // Загружаем данные при первом маунте, если есть пользователь
  useEffect(() => {
    if (me && !lastUpdated) {
      loadData();
    }
  }, [me, loadData, lastUpdated]);

  const refreshData = async () => {
    await loadData(true);
  };

  return (
    <BankDataContext.Provider value={{ 
      accounts, 
      totalBalance, 
      accountsCount, 
      consents, 
      isLoading, 
      lastUpdated,
      refreshData 
    }}>
      {children}
    </BankDataContext.Provider>
  );
};

export const useBankData = () => {
  const context = useContext(BankDataContext);
  if (context === undefined) {
    throw new Error('useBankData must be used within a BankDataProvider');
  }
  return context;
};

