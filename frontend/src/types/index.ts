export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  currency: string;
  timezone: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface BankAccount {
  id: string;
  bank_name: string;
  account_label: string;
  account_type: string;
  masked_account_number: string;
  currency: string;
  is_active: boolean;
  created_at: string;
}

export interface Statement {
  id: string;
  account_id: string;
  original_filename: string;
  file_type: string;
  period_start: string | null;
  period_end: string | null;
  opening_balance: string | null;
  closing_balance: string | null;
  status: 'QUEUED' | 'PROCESSING' | 'VALIDATING' | 'REVIEW_REQUIRED' | 'CONFIRMED' | 'ANALYZED' | 'FAILED';
  created_at: string;
  warnings_count: number;
}

export interface StatementPreviewRow {
  row_number: number;
  transaction_date: string;
  description_original: string;
  description_normalized: string;
  debit_amount: string | number;
  credit_amount: string | number;
  balance_after: string | number | null;
  reference_number: string | null;
  payment_method: string;
  transaction_kind: string;
  merchant_guess: string | null;
  is_duplicate_candidate: boolean;
  duplicate_confidence: number;
}

export interface StatementPreviewResponse {
  statement_id: string;
  status: string;
  total_records: number;
  rows: StatementPreviewRow[];
  warnings: Array<{
    id: string;
    row_number: number;
    warning_type: string;
    message: string;
  }>;
}

export interface Transaction {
  id: string;
  account_id: string;
  statement_id: string | null;
  transaction_date: string;
  description_original: string;
  description_normalized: string;
  debit_amount: string;
  credit_amount: string;
  currency: string;
  balance_after: string | null;
  reference_number: string | null;
  payment_method: 'UPI' | 'CARD' | 'NETBANKING' | 'CASH' | 'CHEQUE' | 'OTHER';
  transaction_kind: 'EXPENSE' | 'INCOME' | 'TRANSFER' | 'REFUND' | 'INVESTMENT' | 'CASH_WITHDRAWAL' | 'UNCLASSIFIED';
  review_status: 'CONFIRMED' | 'NEEDS_REVIEW' | 'DISMISSED';
  merchant_name: string | null;
  category_name: string | null;
  notes: string | null;
  created_at: string;
}

export interface TransactionListResponse {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface FinancialSummary {
  period: {
    start_date: string | null;
    end_date: string | null;
  };
  currency: string;
  income: string;
  expenses: string;
  net_cash_flow: string;
  savings_rate_pct: number;
  total_debits: string;
  total_credits: string;
  transfers_excluded: string;
  refunds_total: string;
  investments_total: string;
  unclassified_amount: string;
  transaction_count: number;
  average_expense: string;
  highest_expense: string;
}

export interface CategoryBreakdownItem {
  category: string;
  amount: string;
  count: number;
  percentage: number;
}

export interface DailySpendingPoint {
  date: string;
  income: string;
  expense: string;
  net: string;
  count: number;
}

export interface MonthlySpendingPoint {
  month: string;
  income: string;
  expense: string;
  net: string;
  count: number;
}

export interface CalendarDaySummary {
  date: string;
  day: number;
  has_coverage: boolean;
  total_expense: string;
  total_income: string;
  net_cash_flow: string;
  transaction_count: number;
  spending_intensity: number;
  transactions: Array<{
    id: string;
    description: string;
    amount: string;
    kind: string;
    category?: string;
  }>;
}

export interface FinancialCalendarResponse {
  year: number;
  month: number;
  month_name: string;
  total_monthly_expense: string;
  total_monthly_income: string;
  highest_spending_day: string | null;
  days: CalendarDaySummary[];
}

export interface Budget {
  id: string;
  category_id: string;
  category_name: string;
  amount_budgeted: string;
  amount_spent: string;
  amount_remaining: string;
  percentage_used: number;
  start_date: string;
  end_date: string;
  is_overbudget: boolean;
}

export interface RecurringPayment {
  id: string;
  title: string;
  expected_amount: string;
  frequency: string;
  next_expected_date: string;
  status: string;
  confidence: number;
  user_confirmed: boolean;
  merchant_name?: string;
  category_name?: string;
}

export interface AIChatResponse {
  answer: string;
  intent: string;
  period: {
    start: string | null;
    end: string | null;
  };
  currency: string;
  evidence: Record<string, any>;
  data_warnings: string[];
  visualization?: {
    type: string;
    data: any;
  };
}
