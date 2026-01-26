import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { 
  CreditCard, 
  Lock, 
  CheckCircle, 
  AlertCircle,
  ArrowLeft,
  Loader2,
  ShieldCheck,
  Zap
} from 'lucide-react';

const Checkout = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const tierCode = searchParams.get('tier');
  const billingCycle = searchParams.get('billing') || 'monthly';
  
  const [tier, setTier] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    email: '',
    cardName: '',
    cardNumber: '',
    expiry: '',
    cvc: '',
    country: 'US',
    postalCode: ''
  });

  useEffect(() => {
    fetchTierDetails();
  }, [tierCode]);

  const fetchTierDetails = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/public/tiers');
      const tiers = await response.json();
      
      const selectedTier = tiers.find(t => t.tier_code === tierCode);
      
      if (!selectedTier) {
        setError('Invalid tier selected');
        return;
      }
      
      setTier(selectedTier);
    } catch (err) {
      console.error('Error fetching tier:', err);
      setError('Failed to load tier information');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    
    // Format card number with spaces
    if (name === 'cardNumber') {
      const formatted = value.replace(/\s/g, '').replace(/(\d{4})/g, '$1 ').trim();
      setFormData(prev => ({ ...prev, [name]: formatted }));
      return;
    }
    
    // Format expiry date
    if (name === 'expiry') {
      const formatted = value.replace(/\D/g, '').replace(/(\d{2})(\d)/, '$1/$2').substr(0, 5);
      setFormData(prev => ({ ...prev, [name]: formatted }));
      return;
    }
    
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setProcessing(true);
    setError(null);

    try {
      // TODO: Integrate with Stripe payment API
      // For now, simulate payment processing
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Redirect to success page
      navigate(`/checkout/success?tier=${tierCode}`);
    } catch (err) {
      console.error('Payment error:', err);
      setError('Payment failed. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  const getPrice = () => {
    if (!tier) return 0;
    return billingCycle === 'yearly' ? tier.price_yearly : tier.price_monthly;
  };

  const getTotalPrice = () => {
    const price = parseFloat(getPrice());
    return billingCycle === 'yearly' ? price : price;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-purple-600 animate-spin" />
      </div>
    );
  }

  if (error && !tier) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-2">Error</h2>
          <p className="text-gray-600 text-center mb-6">{error}</p>
          <button
            onClick={() => navigate('/pricing')}
            className="w-full bg-purple-600 text-white py-3 rounded-lg hover:bg-purple-700 transition-colors"
          >
            Back to Pricing
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-white to-blue-50 py-12 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <button
          onClick={() => navigate('/pricing')}
          className="flex items-center text-gray-600 hover:text-gray-900 mb-8 transition-colors"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Pricing
        </button>

        <div className="grid lg:grid-cols-2 gap-8">
          {/* Order Summary */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white rounded-2xl shadow-xl p-8"
          >
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Order Summary</h2>
            
            {tier && (
              <div className="space-y-6">
                {/* Tier Info */}
                <div className="border-b border-gray-200 pb-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-xl font-semibold text-gray-900">{tier.tier_name}</h3>
                      <p className="text-gray-600 text-sm mt-1">{tier.description}</p>
                    </div>
                    <Zap className="w-8 h-8 text-purple-600" />
                  </div>
                  
                  <div className="bg-purple-50 rounded-lg p-4 space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">API Calls</span>
                      <span className="font-semibold text-gray-900">
                        {parseInt(tier.api_calls_limit).toLocaleString()} / month
                      </span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Team Seats</span>
                      <span className="font-semibold text-gray-900">{tier.team_seats}</span>
                    </div>
                    {tier.byok_enabled && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">BYOK</span>
                        <span className="font-semibold text-green-600">Enabled</span>
                      </div>
                    )}
                    {tier.priority_support && (
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Priority Support</span>
                        <span className="font-semibold text-green-600">Included</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Pricing Breakdown */}
                <div className="space-y-3">
                  <div className="flex justify-between text-gray-600">
                    <span>
                      {billingCycle === 'yearly' ? 'Annual' : 'Monthly'} subscription
                    </span>
                    <span>${getPrice()}</span>
                  </div>
                  
                  {billingCycle === 'yearly' && (
                    <div className="flex justify-between text-green-600 text-sm">
                      <span>Annual discount (save 20%)</span>
                      <span>
                        -${(parseFloat(tier.price_monthly) * 12 - parseFloat(tier.price_yearly)).toFixed(2)}
                      </span>
                    </div>
                  )}
                  
                  <div className="border-t border-gray-200 pt-3 flex justify-between text-xl font-bold text-gray-900">
                    <span>Total {billingCycle === 'yearly' ? 'per year' : 'per month'}</span>
                    <span>${getTotalPrice()}</span>
                  </div>
                </div>

                {/* Trust Badges */}
                <div className="bg-gray-50 rounded-lg p-4 space-y-3">
                  <div className="flex items-center text-sm text-gray-600">
                    <ShieldCheck className="w-5 h-5 text-green-600 mr-2" />
                    <span>Secure 256-bit SSL encrypted payment</span>
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                    <span>Cancel anytime, no questions asked</span>
                  </div>
                  <div className="flex items-center text-sm text-gray-600">
                    <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                    <span>14-day money-back guarantee</span>
                  </div>
                </div>
              </div>
            )}
          </motion.div>

          {/* Payment Form */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white rounded-2xl shadow-xl p-8"
          >
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Payment Details</h2>
            
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start">
                <AlertCircle className="w-5 h-5 text-red-600 mr-3 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-semibold text-red-900">Payment Error</p>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Email Address
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="you@example.com"
                />
              </div>

              {/* Card Information */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Card Information
                </label>
                <div className="space-y-3">
                  <div className="relative">
                    <input
                      type="text"
                      name="cardNumber"
                      value={formData.cardNumber}
                      onChange={handleInputChange}
                      required
                      maxLength="19"
                      className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      placeholder="1234 5678 9012 3456"
                    />
                    <CreditCard className="absolute right-4 top-3.5 w-5 h-5 text-gray-400" />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <input
                      type="text"
                      name="expiry"
                      value={formData.expiry}
                      onChange={handleInputChange}
                      required
                      placeholder="MM/YY"
                      className="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    />
                    <input
                      type="text"
                      name="cvc"
                      value={formData.cvc}
                      onChange={handleInputChange}
                      required
                      maxLength="4"
                      placeholder="CVC"
                      className="px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    />
                  </div>
                </div>
              </div>

              {/* Cardholder Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Cardholder Name
                </label>
                <input
                  type="text"
                  name="cardName"
                  value={formData.cardName}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="John Doe"
                />
              </div>

              {/* Billing Address */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Country
                  </label>
                  <select
                    name="country"
                    value={formData.country}
                    onChange={handleInputChange}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  >
                    <option value="US">United States</option>
                    <option value="CA">Canada</option>
                    <option value="GB">United Kingdom</option>
                    <option value="AU">Australia</option>
                    <option value="DE">Germany</option>
                    <option value="FR">France</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Postal Code
                  </label>
                  <input
                    type="text"
                    name="postalCode"
                    value={formData.postalCode}
                    onChange={handleInputChange}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                    placeholder="12345"
                  />
                </div>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={processing}
                className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-4 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center shadow-lg"
              >
                {processing ? (
                  <>
                    <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Lock className="w-5 h-5 mr-2" />
                    Pay ${getTotalPrice()}
                  </>
                )}
              </button>

              <p className="text-xs text-gray-500 text-center">
                By confirming your subscription, you allow Ops Center to charge your card for this payment and future payments in accordance with their terms. You can always cancel your subscription.
              </p>
            </form>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default Checkout;
