import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { XCircle, ArrowLeft, HelpCircle } from 'lucide-react';

const CheckoutCancelled = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50 via-white to-orange-50 flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="bg-white rounded-2xl shadow-2xl p-12 max-w-2xl w-full text-center"
      >
        {/* Cancelled Icon */}
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
          className="mx-auto w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mb-6"
        >
          <XCircle className="w-12 h-12 text-red-600" />
        </motion.div>

        {/* Cancelled Message */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Payment Cancelled
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Your payment was not processed. No charges were made to your account.
          </p>
        </motion.div>

        {/* Common Issues */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
          className="bg-gray-50 rounded-xl p-6 mb-8 text-left"
        >
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <HelpCircle className="w-5 h-5 text-orange-600 mr-2" />
            Common issues
          </h2>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-start">
              <span className="text-orange-600 mr-2">•</span>
              Payment window closed or timed out
            </li>
            <li className="flex items-start">
              <span className="text-orange-600 mr-2">•</span>
              Card was declined by your bank
            </li>
            <li className="flex items-start">
              <span className="text-orange-600 mr-2">•</span>
              Incorrect card details entered
            </li>
            <li className="flex items-start">
              <span className="text-orange-600 mr-2">•</span>
              Insufficient funds or card limit reached
            </li>
          </ul>
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="flex flex-col sm:flex-row gap-4"
        >
          <button
            onClick={() => navigate('/pricing')}
            className="flex-1 bg-gradient-to-r from-purple-600 to-blue-600 text-white py-4 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all flex items-center justify-center shadow-lg"
          >
            Try Again
          </button>
          <button
            onClick={() => navigate('/')}
            className="flex-1 bg-white text-gray-700 py-4 rounded-lg font-semibold border-2 border-gray-300 hover:border-gray-400 transition-all flex items-center justify-center"
          >
            <ArrowLeft className="w-5 h-5 mr-2" />
            Back to Home
          </button>
        </motion.div>

        {/* Support */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          className="text-sm text-gray-500 mt-8"
        >
          Having trouble?{' '}
          <a href="/support" className="text-purple-600 hover:text-purple-700 font-medium">
            Contact our support team
          </a>
          {' '}and we'll help you get set up.
        </motion.p>
      </motion.div>
    </div>
  );
};

export default CheckoutCancelled;
