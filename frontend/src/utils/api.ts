import axios from "axios";
import { getCookie, setCookie, eraseCookie } from "./cookies";

export interface RegisterData {
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  phone_number: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
}

const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
});

// Логирование запросов
api.interceptors.request.use((config) => {
  const token = getCookie("access_token");
  config.headers = config.headers || {};
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }

  // Логируем запросы (только в development)
  if (import.meta.env.DEV) {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
      params: config.params,
      data: config.data,
    });
  }

  return config;
});

// Логирование ответов
api.interceptors.response.use(
  (response) => {
    // Логируем успешные ответы (только в development)
    if (import.meta.env.DEV) {
      console.log(
        `[API Response] ${response.config.method?.toUpperCase()} ${
          response.config.url
        }`,
        {
          status: response.status,
          data: response.data,
        }
      );
    }
    return response;
  },
  (error) => {
    // Логируем ошибки
    if (error.response) {
      console.error(
        `[API Error] ${error.config?.method?.toUpperCase()} ${
          error.config?.url
        }`,
        {
          status: error.response.status,
          data: error.response.data,
          headers: error.response.headers,
        }
      );
    } else if (error.request) {
      console.error(`[API Error] No response received`, error.request);
    } else {
      console.error(`[API Error]`, error.message);
    }
    return Promise.reject(error);
  }
);

// для автоматического обновления токена (объединено с логированием выше)
api.interceptors.response.use(
  (response) => response,
  async (error: { config: any; response: { status: number } }) => {
    const originalRequest = error.config;

    // Логируем ошибки (уже делается выше, но добавляем для refresh token)
    if (error.response?.status === 401 && !originalRequest._retry) {
      console.log("[API] Token expired, attempting refresh...");
      originalRequest._retry = true;
      const refreshToken = getCookie("refresh_token");

      if (refreshToken) {
        try {
          const { data } = await axios.post<TokenResponse>(
            `${API_URL}/auth/refresh`,
            { refresh_token: refreshToken }
          );
          setCookie("access_token", data.access_token, 15 / (24 * 60));
          setCookie("refresh_token", data.refresh_token, 7);
          api.defaults.headers.common[
            "Authorization"
          ] = `Bearer ${data.access_token}`;
          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers[
            "Authorization"
          ] = `Bearer ${data.access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          console.error("[API] Refresh token failed", refreshError);
          // Очищаем токены при неудачном обновлении
          eraseCookie("access_token");
          eraseCookie("refresh_token");
          delete axios.defaults.headers.common["Authorization"];
          // Не делаем редирект автоматически - пусть компоненты решают сами
          return Promise.reject(refreshError);
        }
      } else {
        // Нет refresh токена - очищаем access токен
        eraseCookie("access_token");
        delete axios.defaults.headers.common["Authorization"];
      }
    }
    return Promise.reject(error);
  }
);

export const register = (data: RegisterData) => {
  console.log("api: send register request: ", data);
  return api.post<UserResponse>("/auth/register", data);
};

export const verifySms = (phone_number: string, code: string) => {
  return api.post("/auth/verify-sms", { phone_number, code });
};

export const login = (email: string, password: string) => {
  return api.post<TokenResponse>("/auth/login", { email, password });
};

export const getMe = () => {
  return api.get<UserResponse>("/users/me");
};

export const startBankOAuth = () => {
  // Просто перенаправляем пользователя на эндпоинт нашего бэкенда
  window.location.href = `${API_URL}/auth/oauth/authorize`;
};

export const logout = () => {
  // Очистка токенов происходит на клиенте
  eraseCookie("access_token");
  eraseCookie("refresh_token");
  delete axios.defaults.headers.common["Authorization"];
  // Можно добавить вызов API для инвалидации токена на сервере, если нужно
};

export interface BankAccount {
  account_id?: string;
  id?: string;
  accountId?: string;
  account_type?: string;
  currency?: string;
  nickname?: string;
  account?: {
    schemeName?: string;
    identification?: string;
    name?: string;
    secondaryIdentification?: string;
    account_id?: string;
  };
  balances?: Array<{
    balanceAmount: {
      amount: string;
      currency: string;
    };
    balanceType: string;
    creditDebitIndicator: string;
  }>;
}

// Вспомогательная функция для получения account_id из разных форматов
export const getAccountId = (account: BankAccount): string | null => {
  return (
    account.account_id ||
    account.id ||
    account.accountId ||
    account.account?.identification ||
    account.account?.account_id ||
    null
  );
};

export interface BankAccountsResponse {
  success: boolean;
  banks: {
    [bankCode: string]: {
      success: boolean;
      accounts: BankAccount[];
      consent_id?: string;
      count: number;
      error?: string;
    };
  };
  total_accounts: number;
}

export interface BankTransaction {
  transaction_id?: string;
  transactionId?: string;
  transactionReference?: string;
  account_id: string;
  amount?: number;
  currency?: string;
  transaction_type?: string;
  creditDebitIndicator?: string;
  status?: string;
  booking_date?: string;
  bookingDateTime?: string;
  value_date?: string;
  valueDateTime?: string;
  remittance_information?: string;
  transactionInformation?: string;
  remittanceInformation?:
    | {
        unstructured?: string;
      }
    | string;
  creditor_name?: string;
  creditorName?: string;
  creditor_account?: string;
  creditorAccount?: {
    identification?: string;
  };
  debtor_name?: string;
  debtorName?: string;
  debtor_account?: string;
  debtorAccount?: {
    identification?: string;
  };
}

export interface BankTransactionsResponse {
  success: boolean;
  account_id: string;
  transactions: BankTransaction[];
  total_count: number;
}

export interface BankBalance {
  accountId?: string;
  amount?:
    | {
        amount: string;
        currency: string;
      }
    | string;
  balanceAmount?: {
    amount: string;
    currency: string;
  };
  type?: string;
  balanceType?: string;
  creditDebitIndicator?: string;
  dateTime?: string;
}

export interface BankBalancesResponse {
  success: boolean;
  balances:
    | BankBalance[]
    | {
        data?: {
          balance?: BankBalance[];
        };
        Data?: {
          Balance?: BankBalance[];
        };
        balance?: BankBalance[];
      };
}

// Получить все счета из всех банков
export const getAllBankAccounts = () => {
  return api.get<BankAccountsResponse>("/api/v1/banks/accounts/all");
};

// Получить счета из конкретного банка
export const getBankAccounts = (bankCode: string) => {
  return api.get<{
    success: boolean;
    accounts: BankAccount[];
    consent_id?: string;
    auto_approved?: boolean;
  }>(`/api/v1/banks/accounts?bank_code=${bankCode}`);
};

// Получить балансы счета
export const getAccountBalances = (
  accountId: string,
  bankCode: string,
  consentId?: string
) => {
  const params = new URLSearchParams({
    bank_code: bankCode,
  });

  // Используем согласие из куки, если не указано явно
  const effectiveConsentId = getCookie(`consent_${bankCode}`);
  if (effectiveConsentId) {
    params.append("consent_id", effectiveConsentId);
  }

  return api.get<BankBalancesResponse>(
    `/api/v1/banks/accounts/${accountId}/balances?${params.toString()}`
  );
};

// Утилита для извлечения баланса из ответа API
export const extractBalanceFromResponse = (response: {
  data: BankBalancesResponse;
}): number => {
  let balances = response.data.balances;

  // Поддерживаем разные форматы ответа
  if (balances && !Array.isArray(balances)) {
    // Формат: { data: { balance: [...] } }
    if ((balances as any).data?.balance) {
      balances = (balances as any).data.balance;
    }
    // Формат: { Data: { Balance: [...] } }
    else if ((balances as any).Data?.Balance) {
      balances = (balances as any).Data.Balance;
    }
    // Формат: массив напрямую
    else if (Array.isArray((balances as any).balance)) {
      balances = (balances as any).balance;
    }
  }

  if (Array.isArray(balances) && balances.length > 0) {
    // Ищем баланс типа "InterimAvailable" или "InterimBooked"
    // Поддерживаем оба формата: balanceType/type и balanceAmount/amount
    const balance =
      balances.find(
        (b: any) =>
          b.type === "InterimAvailable" ||
          b.balanceType === "InterimAvailable" ||
          b.type === "InterimBooked" ||
          b.balanceType === "InterimBooked"
      ) || balances[0];

    // Извлекаем сумму из разных форматов
    // Поддерживаем: amount.amount, balanceAmount.amount, amount (строка)
    let amountStr: string | undefined;

    if (balance?.amount) {
      if (typeof balance.amount === "object" && balance.amount.amount) {
        amountStr = balance.amount.amount;
      } else if (typeof balance.amount === "string") {
        amountStr = balance.amount;
      }
    }

    if (!amountStr && balance?.balanceAmount) {
      if (
        typeof balance.balanceAmount === "object" &&
        balance.balanceAmount.amount
      ) {
        amountStr = balance.balanceAmount.amount;
      } else if (typeof balance.balanceAmount === "string") {
        amountStr = balance.balanceAmount;
      }
    }

    if (amountStr) {
      const parsed = parseFloat(String(amountStr));
      if (!isNaN(parsed)) {
        return parsed;
      }
    }
  }

  return 0;
};

export const getAccountTransactions = (
  accountId: string,
  bankCode: string,
  consentId?: string,
  fromDate?: string,
  toDate?: string
) => {
  const params = new URLSearchParams({
    bank_code: bankCode,
  });

  // Используем согласие из куки, если не указано явно
  const effectiveConsentId = getCookie(`consent_${bankCode}`);
  if (effectiveConsentId) {
    params.append("consent_id", effectiveConsentId);
  }

  if (fromDate) params.append("from_date", fromDate);
  if (toDate) params.append("to_date", toDate);

  return api.get<BankTransactionsResponse>(
    `/api/v1/banks/accounts/${accountId}/transactions?${params.toString()}`
  );
};

export interface BankUser {
  id: number;
  user_id: number;
  bank_code: string;
  bank_user_id: string;
  consent_id?: string;
  created_at: string;
  updated_at: string;
}

export interface BankUsersResponse {
  bank_users: Record<string, string>;
}

export interface BankUserCreate {
  bank_code: string;
  bank_user_id: string;
}

// Получить все bank_user_id пользователя
export const getUserBankUsers = () => {
  return api.get<BankUsersResponse>("/users/me/bank-users");
};

// Сохранить или обновить bank_user_id
export const saveBankUser = (bankUser: BankUserCreate) => {
  return api.post<BankUser>("/users/me/bank-users", bankUser);
};

// Удалить bank_user_id
export const deleteBankUser = (bankCode: string) => {
  return api.delete(`/users/me/bank-users/${bankCode}`);
};

// ==================== CONSENTS API ====================

export interface BankConsent {
  consent_id: string;
  bank_code: string;
  status: string;
  auto_approved: boolean;
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateConsentResponse {
  success: boolean;
  consent_id: string;
  status: string;
  auto_approved: boolean;
  permissions: string[];
  expires_at: string;
  message: string;
  is_request?: boolean;
}

export interface ConsentsResponse {
  success: boolean;
  consents: BankConsent[];
}

// Создать согласие для банка
export const createAccountConsent = (
  bankCode: string,
  permissions?: string[]
) => {
  const params = new URLSearchParams({
    bank_code: bankCode,
  });
  if (permissions && permissions.length > 0) {
    permissions.forEach((perm) => params.append("permissions", perm));
  }

  return api.post<CreateConsentResponse>(
    `/api/v1/banks/account-consents?${params.toString()}`
  );
};

// Получить список согласий пользователя
export const getUserConsents = () => {
  return api.get<ConsentsResponse>("/api/v1/banks/consents");
};

// Получить детали согласия и проверить статус
export const getConsentDetails = (consentId: string, bankCode: string) => {
  return api.get<{
    success: boolean;
    consent: any;
    db_status: string;
    consent_id: string;
  }>(`/api/v1/banks/consents/${consentId}?bank_code=${bankCode}`);
};

// ==================== ANALYTICS API ====================

export interface HealthMetrics {
  success: boolean;
  metrics?: {
    total_revenue: number;
    total_expenses: number;
    net_income: number;
    total_assets: number;
    total_liabilities: number;
    net_worth: number;
    current_ratio?: number;
    quick_ratio?: number;
    total_ar: number;
    overdue_ar: number;
    ar_turnover_days?: number;
    operating_cash_flow: number;
    cash_flow_trend?: string;
    health_score?: number;
    health_status?: string;
  };
  error?: string;
}

export interface DashboardSummary {
  success: boolean;
  summary?: {
    total_balance: number;
    total_revenue: number;
    total_expenses: number;
    net_income: number;
    total_ar: number;
    overdue_ar: number;
    accounts_count: number;
  };
  error?: string;
}

export const getHealthMetrics = (periodStart?: string, periodEnd?: string) => {
  const params = new URLSearchParams();
  if (periodStart) params.append("period_start", periodStart);
  if (periodEnd) params.append("period_end", periodEnd);
  return api.get<HealthMetrics>(
    `/api/v1/analytics/health-metrics?${params.toString()}`
  );
};

export const getDashboardSummary = () => {
  return api.get<DashboardSummary>("/api/v1/analytics/dashboard");
};

// ==================== PREDICTIONS API ====================

export interface CashFlowPrediction {
  success: boolean;
  predictions?: Array<{
    prediction_date: string;
    predicted_inflow: number;
    predicted_outflow: number;
    predicted_balance: number;
    gap_probability?: number;
    gap_amount?: number;
    confidence_score?: number;
  }>;
  error?: string;
}

export interface CashFlowGap {
  success: boolean;
  gaps?: Array<{
    date: string;
    gap_amount: number;
    probability: number;
    severity: string;
  }>;
  error?: string;
}

export const getCashFlowPredictions = (
  weeksAhead: number = 4,
  predictionDate?: string
) => {
  const params = new URLSearchParams({ weeks_ahead: weeksAhead.toString() });
  if (predictionDate) params.append("prediction_date", predictionDate);
  return api.get<CashFlowPrediction>(
    `/api/v1/predictions/cash-flow?${params.toString()}`
  );
};

export const getCashFlowGaps = (weeksAhead: number = 4) => {
  return api.get<CashFlowGap>(
    `/api/v1/predictions/cash-flow-gaps?weeks_ahead=${weeksAhead}`
  );
};

// ==================== ACCOUNTS RECEIVABLE API ====================

export interface Invoice {
  id: number;
  counterparty_id: number;
  counterparty_name: string;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  amount: number;
  paid_amount: number;
  currency: string;
  status: string;
  description?: string;
  days_overdue?: number;
}

export interface InvoicesResponse {
  success: boolean;
  invoices?: Invoice[];
  error?: string;
}

export interface ARSummary {
  success: boolean;
  summary?: {
    total_ar: number;
    overdue_ar: number;
    pending_count: number;
    overdue_count: number;
    paid_count: number;
  };
  error?: string;
}

export const getInvoices = (status?: string, counterpartyId?: number) => {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (counterpartyId)
    params.append("counterparty_id", counterpartyId.toString());
  return api.get<InvoicesResponse>(`/api/v1/ar/invoices?${params.toString()}`);
};

export const getOverdueInvoices = () => {
  return api.get<InvoicesResponse>("/api/v1/ar/overdue");
};

export const getARSummary = () => {
  return api.get<ARSummary>("/api/v1/ar/summary");
};

// ==================== OAUTH API ====================

export const initiateBankOAuth = (bankCode: string) => {
  // This will redirect to backend, which redirects to bank
  window.location.href = `${API_URL}/auth/oauth/authorize/${bankCode}`;
};
