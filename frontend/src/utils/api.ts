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


const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: API_URL,
});

// Логирование запросов
api.interceptors.request.use((config) => {
  const token = getCookie("access_token");
  if (token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${token}`;
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
      console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
        status: response.status,
        data: response.data,
      });
    }
    return response;
  },
  (error) => {
    // Логируем ошибки
    if (error.response) {
      console.error(`[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
        status: error.response.status,
        data: error.response.data,
        headers: error.response.headers,
      });
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
  (response: any) => response,
  async (error: { config: any; response: { status: number; }; }) => {
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
          setCookie("access_token", data.access_token, 15 / (24 * 60)); // 15 минут
          setCookie("refresh_token", data.refresh_token, 7); // 7 дней
          axios.defaults.headers.common["Authorization"] = `Bearer ${data.access_token}`;
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          console.log("[API] Token refreshed successfully");
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
  console.log("api: send register request: ", data)
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
  account_id: string;
  account_type?: string;
  currency?: string;
  nickname?: string;
  account?: {
    schemeName?: string;
    identification?: string;
    name?: string;
    secondaryIdentification?: string;
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
  transactionId: string;
  transactionReference?: string;
  amount: {
    amount: string;
    currency: string;
  };
  creditDebitIndicator: string;
  status: string;
  bookingDateTime?: string;
  valueDateTime?: string;
  transactionInformation?: string;
  creditorName?: string;
  debtorName?: string;
  remittanceInformation?: {
    unstructured?: string;
  };
}

export interface BankTransactionsResponse {
  success: boolean;
  account_id: string;
  transactions: BankTransaction[];
  total_count: number;
}

// Получить все счета из всех банков
export const getAllBankAccounts = () => {
  return api.get<BankAccountsResponse>("/api/v1/banks/accounts/all");
};

// Получить счета из конкретного банка
export const getBankAccounts = (bankCode: string) => {
  return api.get<{ success: boolean; accounts: BankAccount[]; consent_id?: string; auto_approved?: boolean }>(
    `/api/v1/banks/accounts?bank_code=${bankCode}`
  );
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
  if (consentId) params.append("consent_id", consentId);
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
  return api.get<HealthMetrics>(`/api/v1/analytics/health-metrics?${params.toString()}`);
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

export const getCashFlowPredictions = (weeksAhead: number = 4, predictionDate?: string) => {
  const params = new URLSearchParams({ weeks_ahead: weeksAhead.toString() });
  if (predictionDate) params.append("prediction_date", predictionDate);
  return api.get<CashFlowPrediction>(`/api/v1/predictions/cash-flow?${params.toString()}`);
};

export const getCashFlowGaps = (weeksAhead: number = 4) => {
  return api.get<CashFlowGap>(`/api/v1/predictions/cash-flow-gaps?weeks_ahead=${weeksAhead}`);
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
  if (counterpartyId) params.append("counterparty_id", counterpartyId.toString());
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