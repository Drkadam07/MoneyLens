import React, { useEffect, useState } from 'react';
import {
  Upload,
  FileSpreadsheet,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react';
import api from '../../services/api';
import { BankAccount, Statement, StatementPreviewResponse, StatementPreviewRow } from '../../types';

export const StatementUploadWizard: React.FC = () => {
  const [accounts, setAccounts] = useState<BankAccount[]>([]);
  const [selectedAccount, setSelectedAccount] = useState<string>('');
  const [statements, setStatements] = useState<Statement[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<StatementPreviewResponse | null>(null);
  const [activeStatementId, setActiveStatementId] = useState<string | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);
  const [retryingStatementId, setRetryingStatementId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchAccountsAndStatements();
  }, []);

  const fetchAccountsAndStatements = async () => {
    try {
      const [accRes, stmtRes] = await Promise.all([
        api.get<BankAccount[]>('/accounts'),
        api.get<Statement[]>('/statements'),
      ]);
      setAccounts(accRes.data);
      if (accRes.data.length > 0 && !selectedAccount) {
        setSelectedAccount(accRes.data[0].id);
      }
      setStatements(stmtRes.data);
    } catch (err) {
      console.error('Failed to load accounts/statements', err);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setPreviewData(null);
      setSuccessMessage(null);
      setErrorMessage(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !selectedAccount) return;
    setIsUploading(true);
    setUploadProgress('Uploading statement file and validating SHA-256 idempotency...');
    setErrorMessage(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('account_id', selectedAccount);

    try {
      const resp = await api.post('/statements/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const stmtId = resp.data.statement_id;
      const jobId = resp.data.job_id;
      setActiveStatementId(stmtId);
      setUploadProgress('Statement queued. Extracting transactions...');
      for (let attempt = 0; attempt < 120; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        const jobResp = await api.get(`/statements/jobs/${jobId}`);
        const job = jobResp.data;
        if (job.status === 'FAILED') {
          throw new Error(job.error_message || 'Statement extraction failed.');
        }
        if (job.status === 'REVIEW_REQUIRED') {
          const prevResp = await api.get<StatementPreviewResponse>(`/statements/${stmtId}/preview`);
          setPreviewData(prevResp.data);
          break;
        }
        setUploadProgress(
          job.total_rows > 0
            ? `Extracting transactions... ${job.processed_rows} of ${job.total_rows}`
            : 'Extracting transactions...'
        );
        if (attempt === 119) throw new Error('Extraction is taking longer than expected. Check the statement list shortly.');
      }
      setUploadProgress(null);
      fetchAccountsAndStatements();
    } catch (err: any) {
      setErrorMessage(
        err.message || err.response?.data?.error?.message || 'Upload failed. Check format and permissions.'
      );
      setUploadProgress(null);
    } finally {
      setIsUploading(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!activeStatementId) return;
    setIsConfirming(true);
    try {
      const resp = await api.post(`/statements/${activeStatementId}/confirm`, {});
      setSuccessMessage(resp.data.message || 'Statement successfully confirmed and imported to financial ledger!');
      setPreviewData(null);
      setSelectedFile(null);
      fetchAccountsAndStatements();
    } catch (err: any) {
      setErrorMessage(err.response?.data?.error?.message || 'Failed to confirm statement import.');
    } finally {
      setIsConfirming(false);
    }
  };

  const loadPreview = async (stmtId: string) => {
    try {
      setActiveStatementId(stmtId);
      const resp = await api.get<StatementPreviewResponse>(`/statements/${stmtId}/preview`);
      setPreviewData(resp.data);
    } catch (err) {
      console.error('Failed to load preview:', err);
    }
  };

  const retryExtraction = async (stmtId: string) => {
    setRetryingStatementId(stmtId);
    setErrorMessage(null);
    try {
      await api.post(`/statements/${stmtId}/retry`);
      await fetchAccountsAndStatements();
      setSuccessMessage('Extraction has been queued again.');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.error?.message || 'Could not retry statement extraction.');
    } finally {
      setRetryingStatementId(null);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-8 bg-[#0B0F19]">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Statement Ingestion Engine</h2>
        <p className="text-sm text-gray-400 mt-1">
          Upload PDF, CSV, or Excel bank statements • Automatic UPI normalization & balance verification
        </p>
      </div>

      {successMessage && (
        <div className="p-4 rounded-xl bg-teal-500/10 border border-teal-500/30 flex items-center space-x-3 text-teal-400 text-sm">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-center space-x-3 text-red-400 text-sm">
          <AlertTriangle className="w-5 h-5 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Upload Wizard Box */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 shadow-sm">
        <h3 className="text-base font-semibold text-white mb-4">Step 1: Select Account & Upload Document</h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
          <div>
            <label className="block text-xs uppercase tracking-wider font-semibold text-gray-400 mb-2">
              Target Bank Account
            </label>
            <select
              value={selectedAccount}
              onChange={(e) => setSelectedAccount(e.target.value)}
              className="w-full px-4 py-2.5 bg-[#0E1524] border border-[#1F2937] rounded-xl text-white text-sm focus:outline-none focus:border-teal-500"
            >
              {accounts.map((acc) => (
                <option key={acc.id} value={acc.id}>
                  {acc.bank_name} ({acc.masked_account_number}) - {acc.account_label}
                </option>
              ))}
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs uppercase tracking-wider font-semibold text-gray-400 mb-2">
              Statement File (.pdf, .csv, .xlsx)
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="file"
                accept=".pdf,.csv,.xlsx,.xls"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-teal-500/10 file:text-teal-400 hover:file:bg-teal-500/20 file:cursor-pointer cursor-pointer border border-[#1F2937] rounded-xl bg-[#0E1524]"
              />
              <button
                onClick={handleUpload}
                disabled={!selectedFile || isUploading}
                className="px-6 py-2.5 bg-teal-500 hover:bg-teal-600 disabled:opacity-50 text-gray-950 font-semibold rounded-xl text-sm transition shrink-0 flex items-center space-x-2 shadow-lg shadow-teal-500/20"
              >
                <Upload className="w-4 h-4" />
                <span>{isUploading ? 'Extracting...' : 'Extract & Validate'}</span>
              </button>
            </div>
          </div>
        </div>

        {uploadProgress && (
          <div className="mt-4 p-3 bg-teal-500/10 border border-teal-500/20 rounded-xl flex items-center space-x-3 text-teal-400 text-xs">
            <RefreshCw className="w-4 h-4 animate-spin" />
            <span>{uploadProgress}</span>
          </div>
        )}
      </div>

      {/* Staging Preview Section */}
      {previewData && (
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 shadow-sm space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1F2937] pb-4">
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-lg font-semibold text-white">Step 2: Staging Preview & Verification</h3>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                  {previewData.total_records} Records Extracted
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Verify balance arithmetic and examine potential duplicate candidates before confirming.
              </p>
            </div>

            <button
              onClick={handleConfirmImport}
              disabled={isConfirming}
              className="px-6 py-2.5 bg-gradient-to-r from-teal-500 to-emerald-600 hover:from-teal-600 hover:to-emerald-700 text-gray-950 font-semibold rounded-xl text-sm transition shadow-lg shadow-teal-500/20 flex items-center space-x-2"
            >
              <ShieldCheck className="w-4 h-4" />
              <span>{isConfirming ? 'Importing...' : 'Confirm & Commit to Ledger'}</span>
            </button>
          </div>

          {/* Warnings Banner if any */}
          {previewData.warnings.length > 0 && (
            <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl space-y-2">
              <div className="flex items-center space-x-2 text-yellow-400 text-sm font-semibold">
                <AlertTriangle className="w-4 h-4" />
                <span>Reconciliation Discrepancies / Warnings Detected ({previewData.warnings.length})</span>
              </div>
              <ul className="text-xs text-yellow-300/80 space-y-1 pl-6 list-disc">
                {previewData.warnings.map((w, idx) => (
                  <li key={idx}>
                    <span className="font-mono">Row {w.row_number}</span> [{w.warning_type}]: {w.message}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Staging Rows Table */}
          <div className="overflow-x-auto max-h-96">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-[#111827] text-gray-400 uppercase tracking-wider border-b border-[#1F2937]">
                <tr>
                  <th className="py-2.5 font-semibold">Row</th>
                  <th className="py-2.5 font-semibold">Date</th>
                  <th className="py-2.5 font-semibold">Normalized Merchant</th>
                  <th className="py-2.5 font-semibold">Method</th>
                  <th className="py-2.5 font-semibold">Classification</th>
                  <th className="py-2.5 font-semibold text-right">Debit</th>
                  <th className="py-2.5 font-semibold text-right">Credit</th>
                  <th className="py-2.5 font-semibold text-right">Balance</th>
                  <th className="py-2.5 font-semibold text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1F2937]">
                {previewData.rows.map((r, idx) => (
                  <tr
                    key={idx}
                    className={`hover:bg-gray-800/40 transition ${
                      r.is_duplicate_candidate ? 'bg-red-500/5' : ''
                    }`}
                  >
                    <td className="py-2 font-mono text-gray-500">{r.row_number}</td>
                    <td className="py-2 font-mono text-gray-300">{r.transaction_date}</td>
                    <td className="py-2">
                      <div className="font-medium text-white">{r.description_normalized}</div>
                      <div className="text-[10px] text-gray-500 truncate max-w-xs font-mono">
                        {r.description_original}
                      </div>
                    </td>
                    <td className="py-2">
                      <span className="px-1.5 py-0.5 rounded bg-gray-800 text-gray-300 font-mono">
                        {r.payment_method}
                      </span>
                    </td>
                    <td className="py-2">
                      <span className="px-1.5 py-0.5 rounded bg-teal-500/10 text-teal-400 font-mono">
                        {r.transaction_kind}
                      </span>
                    </td>
                    <td className="py-2 text-right font-mono text-red-400">
                      {parseFloat(String(r.debit_amount)) > 0 ? `₹${r.debit_amount}` : '-'}
                    </td>
                    <td className="py-2 text-right font-mono text-emerald-400">
                      {parseFloat(String(r.credit_amount)) > 0 ? `₹${r.credit_amount}` : '-'}
                    </td>
                    <td className="py-2 text-right font-mono text-gray-400">
                      {r.balance_after ? `₹${r.balance_after}` : '-'}
                    </td>
                    <td className="py-2 text-center">
                      {r.is_duplicate_candidate ? (
                        <span
                          title={`Potential duplicate (${(r.duplicate_confidence * 100).toFixed(0)}% match)`}
                          className="px-2 py-0.5 rounded bg-red-500/20 text-red-300 text-[10px] font-mono border border-red-500/30"
                        >
                          Duplicate?
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px] font-mono">
                          Ready
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Uploaded Statements History */}
      <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 shadow-sm">
        <h3 className="text-base font-semibold text-white mb-4">Imported Statements Lifecycle</h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-gray-400 border-b border-[#1F2937]">
                <th className="pb-3 font-semibold">Statement File</th>
                <th className="pb-3 font-semibold">Period</th>
                <th className="pb-3 font-semibold">Balances</th>
                <th className="pb-3 font-semibold">Status</th>
                <th className="pb-3 font-semibold">Uploaded</th>
                <th className="pb-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F2937]">
              {statements.map((s) => (
                <tr key={s.id} className="hover:bg-gray-800/40 transition">
                  <td className="py-3.5 flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-lg bg-teal-500/10 flex items-center justify-center text-teal-400">
                      <FileSpreadsheet className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="font-medium text-white">{s.original_filename}</div>
                      <div className="text-xs text-gray-500 uppercase font-mono">{s.file_type}</div>
                    </div>
                  </td>
                  <td className="py-3.5 text-xs text-gray-300 font-mono">
                    {s.period_start && s.period_end ? `${s.period_start} to ${s.period_end}` : 'N/A'}
                  </td>
                  <td className="py-3.5 text-xs font-mono text-gray-400">
                    <div>Open: ₹{s.opening_balance || '0.00'}</div>
                    <div>Close: ₹{s.closing_balance || '0.00'}</div>
                  </td>
                  <td className="py-3.5">
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-mono ${
                        s.status === 'CONFIRMED'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : s.status === 'REVIEW_REQUIRED'
                          ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                          : 'bg-gray-800 text-gray-300'
                      }`}
                    >
                      {s.status}
                    </span>
                  </td>
                  <td className="py-3.5 text-xs text-gray-400 font-mono">
                    {new Date(s.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3.5 text-right">
                    {s.status === 'REVIEW_REQUIRED' && (
                      <button
                        onClick={() => loadPreview(s.id)}
                        className="text-xs font-semibold text-teal-400 hover:text-teal-300 transition"
                      >
                        Review Staging →
                      </button>
                    )}
                    {(s.status === 'FAILED' || s.status === 'PROCESSING') && (
                      <button
                        onClick={() => retryExtraction(s.id)}
                        disabled={retryingStatementId === s.id}
                        className="ml-3 text-xs font-semibold text-amber-400 hover:text-amber-300 disabled:opacity-50 transition"
                      >
                        {retryingStatementId === s.id ? 'Queueing...' : 'Retry extraction'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
