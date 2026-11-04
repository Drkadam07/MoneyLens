import React, { useEffect, useState } from 'react';
import {
  ArrowDownRight,
  ArrowUpRight,
  Wallet,
  Percent,
  Calendar,
  Layers,
  Sparkles,
  Upload,
  Receipt,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import api from '../../services/api';
import { CategoryBreakdownItem, FinancialSummary, MonthlySpendingPoint, Transaction } from '../../types';

interface DashboardProps {
  onNavigate: (tab: string) => void;
}

const COLORS = ['#0D9488', '#3B82F6', '#6366F1', '#EC4899', '#F59E0B', '#10B981', '#8B5CF6'];

export const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [categories, setCategories] = useState<CategoryBreakdownItem[]>([]);
  const [monthlyData, setMonthlyData] = useState<MonthlySpendingPoint[]>([]);
  const [recentTxs, setRecentTxs] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [sumRes, catRes, monthRes, txRes] = await Promise.all([
        api.get<FinancialSummary>('/analytics/summary'),
        api.get<CategoryBreakdownItem[]>('/analytics/categories'),
        api.get<MonthlySpendingPoint[]>('/analytics/monthly'),
        api.get<{ items: Transaction[] }>('/transactions?page_size=6'),
      ]);
      setSummary(sumRes.data);
      setCategories(catRes.data);
      setMonthlyData(monthRes.data);
      setRecentTxs(txRes.data.items);
    } catch (err) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatINR = (val: string | number | undefined) => {
    if (val === undefined || val === null) return '₹0.00';
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(num);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-12">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-teal-500"></div>
      </div>
    );
  }

  const netCashFlowNum = summary ? parseFloat(summary.net_cash_flow) : 0;

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8 bg-[#0B0F19]">
      {/* Top Banner & Quick Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Financial Intelligence Overview</h2>
          <p className="text-sm text-gray-400 mt-1">
            Authoritative statement ledger data • Grounded PostgreSQL source of truth
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => onNavigate('statements')}
            className="px-4 py-2 bg-[#1F2937] hover:bg-[#374151] text-gray-200 text-sm font-medium rounded-xl flex items-center space-x-2 transition border border-gray-700/50"
          >
            <Upload className="w-4 h-4 text-teal-400" />
            <span>Upload Statement</span>
          </button>
          <button
            onClick={() => onNavigate('ai-assistant')}
            className="px-4 py-2 bg-gradient-to-r from-teal-500 to-emerald-600 hover:from-teal-600 hover:to-emerald-700 text-gray-950 text-sm font-semibold rounded-xl flex items-center space-x-2 shadow-lg shadow-teal-500/20 transition"
          >
            <Sparkles className="w-4 h-4" />
            <span>Ask AI Assistant</span>
          </button>
        </div>
      </div>

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {/* Income */}
        <div className="bg-[#111827] border border-[#1F2937] p-5 rounded-2xl relative overflow-hidden shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-gray-400">Classified Income</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
              <ArrowDownRight className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold tracking-tight text-white font-mono">
              {formatINR(summary?.income)}
            </div>
            <p className="text-xs text-gray-400 mt-1">Excludes transfers & refunds</p>
          </div>
        </div>

        {/* Expenses */}
        <div className="bg-[#111827] border border-[#1F2937] p-5 rounded-2xl relative overflow-hidden shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-gray-400">Classified Expenses</span>
            <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center text-red-400">
              <ArrowUpRight className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold tracking-tight text-white font-mono">
              {formatINR(summary?.expenses)}
            </div>
            <p className="text-xs text-gray-400 mt-1">Excludes self-transfers & SIPs</p>
          </div>
        </div>

        {/* Net Cash Flow */}
        <div className="bg-[#111827] border border-[#1F2937] p-5 rounded-2xl relative overflow-hidden shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-gray-400">Net Cash Flow</span>
            <div
              className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                netCashFlowNum >= 0 ? 'bg-teal-500/10 text-teal-400' : 'bg-rose-500/10 text-rose-400'
              }`}
            >
              <Wallet className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div
              className={`text-2xl font-bold tracking-tight font-mono ${
                netCashFlowNum >= 0 ? 'text-teal-400' : 'text-rose-400'
              }`}
            >
              {formatINR(summary?.net_cash_flow)}
            </div>
            <p className="text-xs text-gray-400 mt-1">Income minus Classified Expenses</p>
          </div>
        </div>

        {/* Savings Rate */}
        <div className="bg-[#111827] border border-[#1F2937] p-5 rounded-2xl relative overflow-hidden shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider font-semibold text-gray-400">Savings Rate</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
              <Percent className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-2xl font-bold tracking-tight text-white font-mono">
              {summary?.savings_rate_pct ?? 0}%
            </div>
            <p className="text-xs text-gray-400 mt-1">Proportion of income retained</p>
          </div>
        </div>
      </div>

      {/* Visual Analytics Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cash Flow Over Time Area Chart */}
        <div className="lg:col-span-2 bg-[#111827] border border-[#1F2937] p-6 rounded-2xl shadow-sm">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-semibold text-white">Monthly Cash Flow Trend</h3>
              <p className="text-xs text-gray-400">Income vs. Expense trajectory over statement periods</p>
            </div>
            <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-[#1F2937] text-gray-300">
              Deterministic Aggregation
            </span>
          </div>
          <div className="h-72 w-full">
            {monthlyData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={monthlyData}>
                  <defs>
                    <linearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10B981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10B981" stopOpacity={0.0} />
                    </linearGradient>
                    <linearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#EF4444" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#EF4444" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                  <XAxis dataKey="month" stroke="#6B7280" tick={{ fill: '#9CA3AF', fontSize: 12 }} />
                  <YAxis
                    stroke="#6B7280"
                    tick={{ fill: '#9CA3AF', fontSize: 12 }}
                    tickFormatter={(val) => `₹${(val / 1000).toFixed(0)}k`}
                  />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.75rem' }}
                    formatter={(val: any) => [formatINR(val), '']}
                  />
                  <Area
                    type="monotone"
                    dataKey="income"
                    stroke="#10B981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#incomeGrad)"
                    name="Income"
                  />
                  <Area
                    type="monotone"
                    dataKey="expense"
                    stroke="#EF4444"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#expenseGrad)"
                    name="Expense"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-gray-500 text-sm">
                No monthly data available yet. Upload statements to visualize trends.
              </div>
            )}
          </div>
        </div>

        {/* Category Breakdown Donut */}
        <div className="bg-[#111827] border border-[#1F2937] p-6 rounded-2xl shadow-sm flex flex-col">
          <div className="mb-4">
            <h3 className="text-base font-semibold text-white">Expense by Category</h3>
            <p className="text-xs text-gray-400">Classified spending distribution</p>
          </div>
          <div className="h-56 relative flex items-center justify-center">
            {categories.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={categories}
                    dataKey="percentage"
                    nameKey="category"
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={3}
                  >
                    {categories.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#374151', borderRadius: '0.75rem' }}
                    formatter={(val: any, name: any) => [`${val}%`, name]}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-gray-500 text-sm">No expenses categorized yet.</div>
            )}
          </div>
          <div className="mt-4 flex-1 space-y-2 overflow-y-auto max-h-36 pr-1">
            {categories.slice(0, 5).map((cat, idx) => (
              <div key={idx} className="flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                  ></span>
                  <span className="text-gray-300 truncate max-w-[120px]">{cat.category}</span>
                </div>
                <div className="font-mono text-gray-400">
                  <span>{cat.percentage}%</span>
                  <span className="ml-2 text-gray-200">{formatINR(cat.amount)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Transactions Table */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 shadow-sm">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="text-base font-semibold text-white">Recent Ledger Transactions</h3>
            <p className="text-xs text-gray-400">Latest parsed records with normalized payment methods</p>
          </div>
          <button
            onClick={() => onNavigate('transactions')}
            className="text-xs font-semibold text-teal-400 hover:text-teal-300 transition"
          >
            View All Transactions →
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-gray-400 border-b border-[#1F2937]">
                <th className="pb-3 font-semibold">Date</th>
                <th className="pb-3 font-semibold">Narration / Merchant</th>
                <th className="pb-3 font-semibold">Method</th>
                <th className="pb-3 font-semibold">Category</th>
                <th className="pb-3 font-semibold text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              {recentTxs.map((tx) => {
                const isDebit = parseFloat(tx.debit_amount) > 0;
                return (
                  <tr key={tx.id} className="hover:bg-gray-800/40 transition">
                    <td className="py-3.5 text-gray-400 font-mono text-xs whitespace-nowrap">
                      {tx.transaction_date}
                    </td>
                    <td className="py-3.5 pr-4">
                      <div className="font-medium text-white">{tx.description_normalized}</div>
                      <div className="text-xs text-gray-500 font-mono truncate max-w-xs">
                        {tx.description_original}
                      </div>
                    </td>
                    <td className="py-3.5">
                      <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-gray-800 text-gray-300 border border-gray-700">
                        {tx.payment_method}
                      </span>
                    </td>
                    <td className="py-3.5 text-gray-300 text-xs">
                      {tx.category_name || 'Uncategorized'}
                    </td>
                    <td
                      className={`py-3.5 text-right font-mono font-medium whitespace-nowrap ${
                        isDebit ? 'text-red-400' : 'text-emerald-400'
                      }`}
                    >
                      {isDebit ? `- ${formatINR(tx.debit_amount)}` : `+ ${formatINR(tx.credit_amount)}`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
