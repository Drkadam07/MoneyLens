import React, { useEffect, useState } from 'react';
import { useAuthStore } from './stores/authStore';
import { Login } from './features/auth/Login';
import { Register } from './features/auth/Register';
import { Sidebar } from './components/layout/Sidebar';
import { Dashboard } from './features/dashboard/Dashboard';
import { TransactionList } from './features/transactions/TransactionList';
import { StatementUploadWizard } from './features/statements/StatementUploadWizard';
import { FinancialCalendar } from './features/calendar/FinancialCalendar';
import { BudgetsAndGoals } from './features/budgets/BudgetsAndGoals';
import { AIAssistantDrawer } from './features/ai-assistant/AIAssistantDrawer';

export const App: React.FC = () => {
  const { isAuthenticated, fetchUser } = useAuthStore();
  const [authView, setAuthView] = useState<'login' | 'register'>('login');
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  if (!isAuthenticated) {
    if (authView === 'login') {
      return <Login onSwitchToRegister={() => setAuthView('register')} />;
    }
    return <Register onSwitchToLogin={() => setAuthView('login')} />;
  }

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard onNavigate={setActiveTab} />;
      case 'transactions':
        return <TransactionList />;
      case 'statements':
        return <StatementUploadWizard />;
      case 'calendar':
        return <FinancialCalendar />;
      case 'budgets':
      case 'recurring':
        return <BudgetsAndGoals />;
      case 'ai-assistant':
        return <AIAssistantDrawer />;
      default:
        return <Dashboard onNavigate={setActiveTab} />;
    }
  };

  return (
    <div className="flex h-screen bg-[#0B0F19] text-gray-100 overflow-hidden font-sans">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-[#0B0F19]">
        {renderContent()}
      </main>
    </div>
  );
};

export default App;
