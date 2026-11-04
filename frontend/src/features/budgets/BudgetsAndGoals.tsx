import React, { useEffect, useState } from 'react';
import { PiggyBank, Plus, CheckCircle, AlertCircle, RefreshCw, Check } from 'lucide-react';
import api from '../../services/api';
import { Budget, RecurringPayment } from '../../types';

export const BudgetsAndGoals: React.FC = () => {
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [recurring, setRecurring] = useState<RecurringPayment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBudgetsAndRecurring();
  }, []);

  const fetchBudgetsAndRecurring = async () => {
    setLoading(true);
    try {
      const [bRes, rRes] = await Promise.all([
        api.get<Budget[]>('/budgets'),
        api.get<RecurringPayment[]>('/recurring'),
      ]);
      setBudgets(bRes.data);
      setRecurring(rRes.data);
    } catch (err) {
      console.error('Failed to load budgets and recurring items:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmRecurring = async (id: string) => {
    try {
      await api.post(`/recurring/${id}/confirm`, { user_confirmed: true });
      fetchBudgetsAndRecurring();
    } catch (err) {
      console.error('Failed to confirm recurring payment:', err);
    }
  };

  const formatINR = (val: string | number) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(num);
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8 bg-[#0B0F19]">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Budgets & Recurring Intelligence</h2>
        <p className="text-sm text-gray-400 mt-1">
          Category spending limits • Automated recurring subscription & bill detection
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Budgets Section */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-teal-500/10 flex items-center justify-center text-teal-400">
                <PiggyBank className="w-5 h-5" />
              </div>
              <h3 className="text-base font-semibold text-white">Active Monthly Budgets</h3>
            </div>
          </div>

          <div className="space-y-4">
            {budgets.map((b) => (
              <div
                key={b.id}
                className="p-4 bg-[#0E1524] border border-[#1F2937] rounded-xl space-y-2.5"
              >
                <div className="flex items-center justify-between text-sm">
                  <span className="font-semibold text-white">{b.category_name}</span>
                  <span className="font-mono text-xs text-gray-300">
                    <span className="text-white font-bold">{formatINR(b.amount_spent)}</span> / {formatINR(b.amount_budgeted)}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full h-2 rounded-full bg-gray-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      b.is_overbudget ? 'bg-red-500' : b.percentage_used > 80 ? 'bg-yellow-500' : 'bg-teal-500'
                    }`}
                    style={{ width: `${Math.min(100, b.percentage_used)}%` }}
                  ></div>
                </div>

                <div className="flex items-center justify-between text-xs text-gray-400 font-mono">
                  <span>{b.percentage_used}% used</span>
                  <span className={b.is_overbudget ? 'text-red-400 font-semibold' : 'text-gray-300'}>
                    {b.is_overbudget
                      ? `Overbudget by ${formatINR(Math.abs(parseFloat(b.amount_remaining)))}`
                      : `${formatINR(b.amount_remaining)} remaining`}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recurring Payments Section */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 shadow-sm space-y-5">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
              <RefreshCw className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Detected Subscriptions & Bills</h3>
              <p className="text-xs text-gray-400">Regular recurring debits detected by cadence heuristics</p>
            </div>
          </div>

          <div className="space-y-3">
            {recurring.map((r) => (
              <div
                key={r.id}
                className="p-4 bg-[#0E1524] border border-[#1F2937] rounded-xl flex items-center justify-between"
              >
                <div>
                  <div className="text-sm font-semibold text-white">{r.title}</div>
                  <div className="text-xs text-gray-400 font-mono mt-0.5">
                    {r.frequency} • Next: {r.next_expected_date}
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="text-sm font-mono font-bold text-red-400">
                    {formatINR(r.expected_amount)}
                  </div>
                  {r.user_confirmed ? (
                    <span className="flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      <Check className="w-3 h-3" /> Confirmed
                    </span>
                  ) : (
                    <button
                      onClick={() => handleConfirmRecurring(r.id)}
                      className="text-xs px-2.5 py-1 bg-teal-500/10 hover:bg-teal-500/20 text-teal-300 border border-teal-500/30 rounded-lg transition"
                    >
                      Confirm
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
