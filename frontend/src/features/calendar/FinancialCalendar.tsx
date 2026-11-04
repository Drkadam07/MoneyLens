import React, { useEffect, useState } from 'react';
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight, Info, AlertCircle } from 'lucide-react';
import api from '../../services/api';
import { CalendarDaySummary, FinancialCalendarResponse } from '../../types';

export const FinancialCalendar: React.FC = () => {
  const [calendarData, setCalendarData] = useState<FinancialCalendarResponse | null>(null);
  const [currentYear, setCurrentYear] = useState(2026);
  const [currentMonth, setCurrentMonth] = useState(10);
  const [selectedDay, setSelectedDay] = useState<CalendarDaySummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCalendar(currentYear, currentMonth);
  }, [currentYear, currentMonth]);

  const fetchCalendar = async (y: number, m: number) => {
    setLoading(true);
    try {
      const resp = await api.get<FinancialCalendarResponse>(`/calendar?year=${y}&month=${m}`);
      setCalendarData(resp.data);
      if (resp.data.days.length > 0) {
        setSelectedDay(resp.data.days[0]);
      }
    } catch (err) {
      console.error('Failed to load calendar data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handlePrevMonth = () => {
    if (currentMonth === 1) {
      setCurrentMonth(12);
      setCurrentYear((y) => y - 1);
    } else {
      setCurrentMonth((m) => m - 1);
    }
  };

  const handleNextMonth = () => {
    if (currentMonth === 12) {
      setCurrentMonth(1);
      setCurrentYear((y) => y + 1);
    } else {
      setCurrentMonth((m) => m + 1);
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

  const getIntensityColor = (intensity: number, hasCoverage: boolean) => {
    if (!hasCoverage) return 'bg-gray-900/40 border-gray-800/40 text-gray-600 opacity-60';
    switch (intensity) {
      case 0:
        return 'bg-gray-800/20 border-gray-800 text-gray-400 hover:border-gray-700';
      case 1:
        return 'bg-teal-950/40 border-teal-900 text-teal-300 hover:border-teal-700';
      case 2:
        return 'bg-teal-900/50 border-teal-700 text-teal-200 hover:border-teal-500';
      case 3:
        return 'bg-teal-800/60 border-teal-600 text-teal-100 hover:border-teal-400';
      case 4:
        return 'bg-teal-600/80 border-teal-400 text-white font-bold shadow-lg shadow-teal-500/20';
      default:
        return 'bg-gray-800/30 border-gray-800';
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-8 space-y-6 bg-[#0B0F19]">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Financial Calendar & Time Machine</h2>
          <p className="text-sm text-gray-400 mt-1">
            Explore daily financial activity • Identifies spending intensity and statement coverage gaps
          </p>
        </div>

        {/* Month Selector */}
        <div className="flex items-center space-x-3 bg-[#111827] border border-[#1F2937] p-1.5 rounded-xl">
          <button
            onClick={handlePrevMonth}
            className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="font-semibold text-sm text-white px-2">
            {calendarData?.month_name || 'October'} {currentYear}
          </span>
          <button
            onClick={handleNextMonth}
            className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar Heatmap Grid */}
        <div className="lg:col-span-2 bg-[#111827] border border-[#1F2937] rounded-2xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white">Daily Spending Heatmap</h3>
            {/* Heatmap Legend */}
            <div className="flex items-center space-x-2 text-xs text-gray-400">
              <span>Less</span>
              <span className="w-3 h-3 rounded bg-gray-800 border border-gray-700"></span>
              <span className="w-3 h-3 rounded bg-teal-950 border border-teal-900"></span>
              <span className="w-3 h-3 rounded bg-teal-900 border border-teal-700"></span>
              <span className="w-3 h-3 rounded bg-teal-800 border border-teal-600"></span>
              <span className="w-3 h-3 rounded bg-teal-600 border border-teal-400"></span>
              <span>More</span>
            </div>
          </div>

          {loading ? (
            <div className="h-64 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500"></div>
            </div>
          ) : (
            <div className="grid grid-cols-7 gap-2.5 pt-2">
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
                <div key={d} className="text-center text-xs font-semibold text-gray-500 py-1 uppercase">
                  {d}
                </div>
              ))}
              {calendarData?.days.map((day) => {
                const isSelected = selectedDay?.date === day.date;
                return (
                  <button
                    key={day.date}
                    onClick={() => setSelectedDay(day)}
                    className={`h-20 p-2 rounded-xl border flex flex-col justify-between text-left transition relative ${getIntensityColor(
                      day.spending_intensity,
                      day.has_coverage
                    )} ${isSelected ? 'ring-2 ring-teal-400 border-teal-400' : ''}`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-xs font-semibold font-mono">{day.day}</span>
                      {!day.has_coverage && (
                        <span title="No statement uploaded for this date" className="text-gray-500">
                          <AlertCircle className="w-3 h-3" />
                        </span>
                      )}
                    </div>
                    {day.has_coverage && parseFloat(day.total_expense) > 0 && (
                      <div className="text-[11px] font-mono font-medium truncate text-red-300">
                        {formatINR(day.total_expense)}
                      </div>
                    )}
                    {day.has_coverage && parseFloat(day.total_income) > 0 && (
                      <div className="text-[10px] font-mono font-medium truncate text-emerald-400">
                        +{formatINR(day.total_income)}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Day Activity Details */}
        <div className="bg-[#111827] border border-[#1F2937] rounded-2xl p-6 shadow-sm flex flex-col">
          <div className="border-b border-[#1F2937] pb-4 mb-4">
            <span className="text-xs uppercase font-semibold text-gray-400">Selected Day Activity</span>
            <h3 className="text-lg font-bold text-white mt-1">
              {selectedDay ? selectedDay.date : 'Select a date'}
            </h3>
            {selectedDay && (
              <div className="flex items-center gap-3 mt-3">
                <div className="text-xs font-mono">
                  <span className="text-gray-400">Spent: </span>
                  <span className="text-red-400 font-bold">{formatINR(selectedDay.total_expense)}</span>
                </div>
                <div className="text-xs font-mono">
                  <span className="text-gray-400">Received: </span>
                  <span className="text-emerald-400 font-bold">{formatINR(selectedDay.total_income)}</span>
                </div>
              </div>
            )}
          </div>

          <div className="flex-1 overflow-y-auto space-y-3">
            {selectedDay?.transactions && selectedDay.transactions.length > 0 ? (
              selectedDay.transactions.map((tx) => (
                <div
                  key={tx.id}
                  className="p-3 bg-[#0E1524] border border-[#1F2937] rounded-xl flex items-center justify-between text-xs"
                >
                  <div>
                    <div className="font-semibold text-white">{tx.description}</div>
                    <div className="text-gray-400 text-[11px] mt-0.5">{tx.category || tx.kind}</div>
                  </div>
                  <div
                    className={`font-mono font-semibold ${
                      tx.kind === 'EXPENSE' ? 'text-red-400' : 'text-emerald-400'
                    }`}
                  >
                    {tx.kind === 'EXPENSE' ? '-' : '+'} {formatINR(tx.amount)}
                  </div>
                </div>
              ))
            ) : (
              <div className="h-40 flex items-center justify-center text-gray-500 text-xs text-center p-4">
                {selectedDay?.has_coverage
                  ? 'No transactions recorded on this day (₹0 spend).'
                  : 'No statement data covers this day.'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
