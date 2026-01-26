import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CheckCircle, ArrowRight, Download, Mail } from 'lucide-react';

const CheckoutSuccess = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const tierCode = searchParams.get('tier');

  useEffect(() => {
    // Track conversion event (can integrate with analytics)
    console.log('Conversion tracked:', tierCode);
  }, [tierCode]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-blue-50 flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="bg-white rounded-2xl shadow-2xl p-12 max-w-2xl w-full text-center"
      >
        {/* Success Icon */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
          className="mx-auto w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mb-6"
        >
          <CheckCircle className="w-12 h-12 text-green-600" />
        </motion.div>

        {/* Success Message */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Payment Successful!
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Welcome to Ops Center! Your subscription is now active.
          </p>
        </motion.div>

        {/* What's Next */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-gray-50 rounded-xl p-6 mb-8 text-left"
        >
          <h2 className="text-lg font-semibold text-gray-900 mb-4">What happens next?</h2>
          <div className="space-y-3">
            <div className="flex items-start">
              <Mail className="w-5 h-5 text-purple-600 mr-3 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-900">Confirmation Email</p>
                <p className="text-sm text-gray-600">
                  We've sent a receipt and account details to your email
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <CheckCircle className="w-5 h-5 text-purple-600 mr-3 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-900">Instant Access</p>
                <p className="text-sm text-gray-600">
                  Your account has been upgraded and all features are now available
                </p>
              </div>
            </div>
            <div className="flex items-start">
              <Download className="w-5 h-5 text-purple-600 mr-3 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-gray-900">Download Invoice</p>
                <p className="text-sm text-gray-600">
                  Your invoice is available in the billing section
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="flex flex-col sm:flex-row gap-4"
        >
          <button
            onClick={() => navigate('/admin/dashboard')}
            className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white py-4 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all flex items-center justify-center shadow-lg"
          >
            Go to Dashboard
            <ArrowRight className="w-5 h-5 ml-2" />
          </button>
          <button
            onClick={() => navigate('/admin/subscription/billing')}
            className="flex-1 bg-white text-gray-700 py-4 rounded-lg font-semibold border-2 border-gray-300 hover:border-purple-600 hover:text-purple-600 transition-all"
          >
            View Billing
          </button>
        </motion.div>

        {/* Support */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="text-sm text-gray-500 mt-8"
        >
          Need help getting started?{' '}
          <a href="/docs" className="text-purple-600 hover:text-purple-700 font-medium">
            View Documentation
          </a>
          {' '}or{' '}
          <a href="/support" className="text-purple-600 hover:text-purple-700 font-medium">
            Contact Support
          </a>
        </motion.p>
      </motion.div>
    </div>
  );
};

export default CheckoutSuccess;
