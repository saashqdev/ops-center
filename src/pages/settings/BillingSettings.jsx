import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, CreditCard, Settings, ArrowLeft } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import InvoiceHistory from '../../components/InvoiceHistory';
import PaymentMethods from '../../components/PaymentMethods';
import { useTheme } from '../../contexts/ThemeContext';

export default function BillingSettings() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('invoices');

  const tabs = [
    { id: 'invoices', label: 'Invoice History', icon: FileText },
    { id: 'payment', label: 'Payment Methods', icon: CreditCard },
  ];

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: theme.background }}>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate('/admin/system/billing')}
            className={`flex items-center space-x-2 ${theme.text.secondary} hover:${theme.text.primary} mb-4 transition-colors`}
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </button>
          
          <h1 className={`text-3xl font-bold ${theme.text.primary}`}>Billing & Invoices</h1>
          <p className={`${theme.text.secondary} mt-2`}>
            Manage your payment methods and view billing history
          </p>
        </div>

        {/* Tabs */}
        <div className={`border-b ${theme.border} mb-6`}>
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`
                    flex items-center space-x-2 py-4 px-1 border-b-2 font-medium text-sm
                    transition-colors
                    ${activeTab === tab.id
                      ? 'border-purple-500 text-purple-400'
                      : `border-transparent ${theme.text.secondary} hover:${theme.text.primary} hover:border-gray-500`
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Tab Content */}
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {activeTab === 'invoices' && <InvoiceHistory />}
          {activeTab === 'payment' && <PaymentMethods />}
        </motion.div>
      </div>
    </div>
  );
}
