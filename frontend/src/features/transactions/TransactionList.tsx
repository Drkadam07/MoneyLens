import React, { useEffect, useState } from 'react';
import {
  Search,
  Filter,
  Receipt,
  ArrowDownRight,
  ArrowUpRight,
  Edit2,
  Tag,
  StickyNote,
  ChevronLeft,
  ChevronRight,
  Check,
  X,
} from 'lucide-react';
import api from '../../services/api';
import { Transaction, TransactionListResponse } from '../../types';

export const TransactionList: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [method, setMethod] = useState('');
  const [kind, setKind] = useState('');
  const [loading, setLoading] = useState(true);

  // Edit category state
  const [editingTxId, setEditingTxId] = useState<string | null>(null);
  const [noteText, setNoteText] = useState('');
  const [activeNoteModalTx, setActiveNoteModalTx] = useState<Transaction | null>(null);

  useEffect(() => {
    fetchTransactions();
  }, [page, method, kind]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
      });
      if (search) params.append('search', search);
      if (method) params.append('payment_method', method);
      if (kind) params.append('transaction_kind', kind);

      const resp = await api.get<TransactionListResponse>(`/transactions?${params.toString()}`);
      setTransactions(resp.data.items);
      setTotal(resp.data.total);
      setTotalPages(resp.data.total_pages);
    } catch (err) {
      console.error('Failed to load transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchTransactions();
  };

  const handleSaveNote = async () => {
    if (!activeNoteModalTx) return;
    try {
      await api.post(`/transactions/${activeNoteModalTx.id}/notes`, { note: noteText });
      setActiveNoteModalTx(null);
      setNoteText('');
      fetchTransactions();
    } catch (err) {
      console.error('Failed to save note:', err);
    }
  };

  const formatINR = (val: string | number) => {
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 2,
    }).format(num);
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-6 bg-[#0B0F19]">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Transaction Management</h2>
          <p className="text-sm text-gray-400 mt-1">
            Deterministic double-entry records • {total} transactions recorded
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#111827] border border-[#1F2937] p-4 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-4 shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex-1 w-full md:w-auto relative">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-gray-500" />
          <input
            type="text"
            placeholder="Search by merchant, description, or reference..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-[#0E1524] border border-[#1F2937] rounded-xl text-white placeholder-gray-500 text-sm focus:outline-none focus:border-teal-500"
          />
        </form>

        <div className="flex items-center space-x-3 w-full md:w-auto">
          <select
            value={method}
            onChange={(e) => {
              setMethod(e.target.value);
              setPage(1);
            }}
            className="px-3.5 py-2 bg-[#0E1524] border border-[#1F2937] rounded-xl text-gray-300 text-xs focus:outline-none focus:border-teal-500"
          >
            <option value="">All Payment Methods</option>
            <option value="UPI">UPI</option>
            <option value="CARD">Card / POS</option>
            <option value="NETBANKING">Netbanking / NEFT / IMPS</option>
            <option value="CASH">Cash / ATM</option>
          </select>

          <select
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              setPage(1);
            }}
            className="px-3.5 py-2 bg-[#0E1524] border border-[#1F2937] rounded-xl text-gray-300 text-xs focus:outline-none focus:border-teal-500"
          >
            <option value="">All Classifications</option>
            <option value="EXPENSE">Expense</option>
            <option value="INCOME">Income</option>
            <option value="TRANSFER">Internal Transfer</option>
            <option value="REFUND">Refund</option>
            <option value="INVESTMENT">Investment</option>
            <option value="CASH_WITHDRAWAL">Cash Withdrawal</option>
          </select>
        </div>
      </div>

      {/* Transactions Data Table */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-2xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-gray-400 bg-[#0E1524] border-b border-[#1F2937]">
                <th className="py-3 px-4 font-semibold">Date</th>
                <th className="py-3 px-4 font-semibold">Merchant / Narration</th>
                <th className="py-3 px-4 font-semibold">Method</th>
                <th className="py-3 px-4 font-semibold">Category</th>
                <th className="py-3 px-4 font-semibold">Nature</th>
                <th className="py-3 px-4 font-semibold text-right">Debit</th>
                <th className="py-3 px-4 font-semibold text-right">Credit</th>
                <th className="py-3 px-4 font-semibold text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              {loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-gray-500">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500"></div>
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-gray-500">
                    No transactions found matching your criteria.
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => {
                  const isDebit = parseFloat(tx.debit_amount) > 0;
                  return (
                    <tr key={tx.id} className="hover:bg-gray-800/30 transition">
                      <td className="py-3.5 px-4 font-mono text-xs text-gray-400 whitespace-nowrap">
                        {tx.transaction_date}
                      </td>
                      <td className="py-3.5 px-4 pr-6">
                        <div className="font-medium text-white flex items-center gap-2">
                          <span>{tx.description_normalized}</span>
                          {tx.notes && (
                            <span title={tx.notes} className="text-teal-400">
                              <StickyNote className="w-3.5 h-3.5" />
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-gray-500 font-mono truncate max-w-xs">
                          {tx.description_original}
                        </div>
                        {tx.reference_number && (
                          <div className="text-[10px] text-gray-500 font-mono">
                            Ref: {tx.reference_number}
                          </div>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-gray-800 text-gray-300 border border-gray-700">
                          {tx.payment_method}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-xs text-gray-300">
                        {tx.category_name || 'Uncategorized'}
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-mono font-medium ${
                            tx.transaction_kind === 'EXPENSE'
                              ? 'bg-rose-500/15 text-rose-300 border border-rose-500/20'
                              : tx.transaction_kind === 'INCOME'
                              ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/20'
                              : tx.transaction_kind === 'TRANSFER'
                              ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/20'
                              : tx.transaction_kind === 'REFUND'
                              ? 'bg-amber-500/15 text-amber-300 border border-amber-500/20'
                              : 'bg-gray-800 text-gray-300'
                          }`}
                        >
                          {tx.transaction_kind}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-medium text-red-400 whitespace-nowrap">
                        {isDebit ? formatINR(tx.debit_amount) : '-'}
                      </td>
                      <td className="py-3.5 px-4 text-right font-mono font-medium text-emerald-400 whitespace-nowrap">
                        {!isDebit ? formatINR(tx.credit_amount) : '-'}
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <button
                          onClick={() => {
                            setActiveNoteModalTx(tx);
                            setNoteText(tx.notes || '');
                          }}
                          className="p-1.5 text-gray-400 hover:text-teal-400 hover:bg-gray-800 rounded-lg transition"
                          title="Add / Edit Note"
                        >
                          <StickyNote className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="p-4 bg-[#0E1524] border-t border-[#1F2937] flex items-center justify-between text-xs text-gray-400">
          <div>
            Showing Page <span className="font-semibold text-white">{page}</span> of{' '}
            <span className="font-semibold text-white">{totalPages}</span> ({total} items)
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1.5 rounded-lg bg-[#111827] border border-[#1F2937] hover:bg-gray-800 disabled:opacity-40 text-gray-300 flex items-center gap-1 transition"
            >
              <ChevronLeft className="w-3.5 h-3.5" /> Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1.5 rounded-lg bg-[#111827] border border-[#1F2937] hover:bg-gray-800 disabled:opacity-40 text-gray-300 flex items-center gap-1 transition"
            >
              Next <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Note Modal */}
      {activeNoteModalTx && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 w-full max-w-md shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-base font-semibold text-white">Add Transaction Note</h4>
              <button
                onClick={() => setActiveNoteModalTx(null)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-xs text-gray-400">
              For transaction: <span className="text-white font-medium">{activeNoteModalTx.description_normalized}</span>
            </p>
            <textarea
              rows={3}
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="e.g. Split with room partner, reimbursed by company..."
              className="w-full p-3 bg-[#0E1524] border border-[#1F2937] rounded-xl text-white text-sm focus:outline-none focus:border-teal-500"
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setActiveNoteModalTx(null)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-xs font-semibold rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveNote}
                className="px-5 py-2 bg-teal-500 hover:bg-teal-600 text-gray-950 text-xs font-semibold rounded-xl"
              >
                Save Note
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
