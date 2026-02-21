import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { EnvelopeIcon, ArrowPathIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';

/**
 * EmailVerificationNotice - Shown when a user tries to login
 * but their email hasn't been verified yet.
 * 
 * Allows them to:
 * 1. Go back to login (after verifying via email link)
 * 2. Resend the verification email
 */
export default function EmailVerificationNotice() {
  const [email, setEmail] = useState('');
  const [resendStatus, setResendStatus] = useState(null); // null | 'sending' | 'sent' | 'error'
  const [message, setMessage] = useState('');

  const handleResend = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;

    setResendStatus('sending');
    try {
      const response = await fetch('/auth/resend-verification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });

      const data = await response.json();
      
      if (data.already_verified) {
        setResendStatus('sent');
        setMessage('Your email is already verified! You can log in now.');
      } else {
        setResendStatus('sent');
        setMessage(data.message || 'If an account with that email exists, a verification link has been sent.');
      }
    } catch (err) {
      setResendStatus('error');
      setMessage('Something went wrong. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-md w-full bg-slate-800/80 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50 p-8"
      >
        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 bg-amber-500/10 rounded-full flex items-center justify-center">
            <ExclamationTriangleIcon className="w-8 h-8 text-amber-400" />
          </div>
        </div>

        {/* Title */}
        <h2 className="text-2xl font-bold text-white text-center mb-2">
          Email Verification Required
        </h2>

        <p className="text-slate-400 text-center mb-6">
          Your email address hasn't been verified yet. Please check your inbox for the verification link, then try logging in again.
        </p>

        {/* Tips */}
        <div className="bg-slate-700/30 rounded-lg p-4 mb-6">
          <div className="flex items-start gap-3 mb-3">
            <EnvelopeIcon className="w-5 h-5 text-emerald-400 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-slate-300">
              Check your <strong className="text-white">inbox</strong> and <strong className="text-white">spam/junk</strong> folder for an email with a verification link.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <ArrowPathIcon className="w-5 h-5 text-emerald-400 mt-0.5 flex-shrink-0" />
            <p className="text-sm text-slate-300">
              The link is valid for <strong className="text-white">24 hours</strong>. Request a new one below if it expired.
            </p>
          </div>
        </div>

        {/* Resend Form */}
        <form onSubmit={handleResend} className="mb-6">
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Resend verification email
          </label>
          <div className="flex gap-2">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              className="flex-1 px-3 py-2 bg-slate-700/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 text-sm"
              required
            />
            <button
              type="submit"
              disabled={resendStatus === 'sending'}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
            >
              {resendStatus === 'sending' ? 'Sending...' : 'Resend'}
            </button>
          </div>
        </form>

        {/* Status Message */}
        {resendStatus === 'sent' && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-lg mb-6"
          >
            <CheckCircleIcon className="w-5 h-5 text-emerald-400 flex-shrink-0" />
            <p className="text-sm text-emerald-300">{message}</p>
          </motion.div>
        )}

        {resendStatus === 'error' && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg mb-6"
          >
            <ExclamationTriangleIcon className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-300">{message}</p>
          </motion.div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-col gap-3">
          <a
            href="/auth/login"
            className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors text-center"
          >
            Back to Login
          </a>
          <a
            href="/"
            className="w-full py-2 text-slate-400 hover:text-white text-sm text-center transition-colors"
          >
            Return to Home
          </a>
        </div>
      </motion.div>
    </div>
  );
}
