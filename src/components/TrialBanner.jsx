import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Clock, Zap, ArrowRight, CheckCircle } from 'lucide-react';

export default function TrialBanner() {
  const [trialInfo, setTrialInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTrialStatus();
  }, []);

  const fetchTrialStatus = async () => {
    try {
      const response = await fetch('/api/v1/my-subscription/', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const data = await response.json();
        
        // Only show banner for active trials
        if (data.status === 'trialing' && data.trial) {
          setTrialInfo(data.trial);
        }
      }
    } catch (error) {
      console.error('Error fetching trial status:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !trialInfo || !trialInfo.is_active_trial) {
    return null;
  }

  const daysRemaining = trialInfo.days_remaining;
  const isExpiringSoon = daysRemaining <= 3;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`
        border-b
        ${isExpiringSoon 
          ? 'bg-gradient-to-r from-red-50 to-orange-50 border-red-200' 
          : 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200'
        }
      `}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="py-3 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`
              p-2 rounded-lg
              ${isExpiringSoon ? 'bg-red-100' : 'bg-blue-100'}
            `}>
              {isExpiringSoon ? (
                <Clock className="w-5 h-5 text-red-600" />
              ) : (
                <Zap className="w-5 h-5 text-blue-600" />
              )}
            </div>
            
            <div>
              <p className="text-sm font-medium text-gray-900">
                {isExpiringSoon ? (
                  <>
                    <span className="text-red-600 font-semibold">
                      {daysRemaining} {daysRemaining === 1 ? 'day' : 'days'}
                    </span>
                    {' '}left in your trial
                  </>
                ) : (
                  <>
                    You're on a free trial with{' '}
                    <span className="text-blue-600 font-semibold">
                      {daysRemaining} days
                    </span>
                    {' '}remaining
                  </>
                )}
              </p>
              <p className="text-xs text-gray-600">
                Upgrade now to keep your features and data
              </p>
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => window.location.href = '/pricing'}
            className={`
              flex items-center space-x-2 px-4 py-2 rounded-lg
              text-sm font-medium transition-all
              ${isExpiringSoon
                ? 'bg-red-600 hover:bg-red-700 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
              }
            `}
          >
            <span>Upgrade Now</span>
            <ArrowRight className="w-4 h-4" />
          </motion.button>
        </div>
      </div>
    </motion.div>
  );
}
