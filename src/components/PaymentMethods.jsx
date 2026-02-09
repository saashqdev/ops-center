import { useState } from 'react';
import { motion } from 'framer-motion';
import { CreditCard, ExternalLink, Shield, AlertCircle } from 'lucide-react';

export default function PaymentMethods() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const openCustomerPortal = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/v1/invoices/stripe/portal-session', {
        credentials: 'include'
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to open payment portal');
      }

      const data = await response.json();
      
      // Redirect to Stripe Customer Portal
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2
          className="text-2xl font-bold text-gray-300"
          style={{ color: 'rgb(209, 213, 219)' }}
        >
          Payment Methods
        </h2>
        <p className="text-gray-600 mt-1">Manage your payment information and billing details</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
          <div>
            <p className="text-red-600 font-medium">Error</p>
            <p className="text-sm text-red-600">{error}</p>
          </div>
        </div>
      )}

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-start space-x-4">
          <div className="p-3 bg-blue-100 rounded-lg">
            <CreditCard className="w-6 h-6 text-blue-600" />
          </div>
          
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Stripe Customer Portal
            </h3>
            <p className="text-gray-600 mb-4">
              Securely manage your payment methods, view billing history, and update your billing information through Stripe's secure portal.
            </p>
            
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <h4 className="text-sm font-medium text-gray-900 mb-2">
                What you can do:
              </h4>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-start space-x-2">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>Add or remove payment methods</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>Update credit card information</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>View complete billing history</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>Download invoices and receipts</span>
                </li>
                <li className="flex items-start space-x-2">
                  <span className="text-green-600 mt-0.5">✓</span>
                  <span>Update billing address</span>
                </li>
              </ul>
            </div>

            <motion.button
              onClick={openCustomerPortal}
              disabled={loading}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center space-x-2 px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  <span>Opening portal...</span>
                </>
              ) : (
                <>
                  <ExternalLink className="w-5 h-5" />
                  <span>Open Payment Portal</span>
                </>
              )}
            </motion.button>

            <div className="flex items-center space-x-2 mt-4 text-sm text-gray-500">
              <Shield className="w-4 h-4" />
              <span>Secured by Stripe • PCI DSS compliant</span>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
          <div className="text-sm text-blue-900">
            <p className="font-medium mb-1">About Stripe Customer Portal</p>
            <p className="text-blue-800">
              You'll be redirected to Stripe's secure portal where you can manage all aspects of your payment information. 
              Your payment data is never stored on our servers and is always encrypted by Stripe.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
