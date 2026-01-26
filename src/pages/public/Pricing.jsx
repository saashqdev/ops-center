import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Check, 
  X, 
  Zap, 
  Shield, 
  Users, 
  TrendingUp,
  CreditCard,
  ArrowRight,
  Sparkles,
  Star,
  Crown
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const Pricing = () => {
  const navigate = useNavigate();
  const [tiers, setTiers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState('monthly'); // 'monthly' or 'yearly'
  const [features, setFeatures] = useState({});

  useEffect(() => {
    fetchTiersAndFeatures();
  }, []);

  const fetchTiersAndFeatures = async () => {
    setLoading(true);
    try {
      // Fetch tiers (public endpoint)
      const tiersRes = await fetch('/api/v1/public/tiers', {
        credentials: 'include'
      });
      const tiersData = await tiersRes.json();
      
      // Fetch features for each tier
      const featuresMap = {};
      for (const tier of tiersData) {
        const featuresRes = await fetch(`/api/v1/public/tiers/${tier.tier_code}/features`, {
          credentials: 'include'
        });
        const featuresData = await featuresRes.json();
        featuresMap[tier.tier_code] = featuresData;
      }
      
      setTiers(tiersData.filter(t => t.is_active && t.tier_code !== 'enterprise'));
      setFeatures(featuresMap);
    } catch (error) {
      console.error('Failed to fetch pricing:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTierIcon = (tierCode) => {
    const icons = {
      trial: Sparkles,
      starter: Zap,
      byok: Shield,
      managed: TrendingUp,
      vip_founder: Crown
    };
    return icons[tierCode] || Star;
  };

  const getTierColor = (tierCode) => {
    const colors = {
      trial: 'from-gray-500 to-gray-700',
      starter: 'from-blue-500 to-cyan-500',
      byok: 'from-purple-500 to-indigo-600',
      managed: 'from-green-500 to-emerald-600',
      vip_founder: 'from-yellow-500 to-amber-600'
    };
    return colors[tierCode] || 'from-slate-500 to-slate-700';
  };

  const getPrice = (tier) => {
    if (billingCycle === 'yearly' && tier.price_yearly > 0) {
      return {
        amount: tier.price_yearly,
        period: '/year',
        savings: tier.price_monthly * 12 - tier.price_yearly
      };
    }
    return {
      amount: tier.price_monthly,
      period: '/month',
      savings: 0
    };
  };

  const handleSelectPlan = (tier) => {
    if (tier.tier_code === 'trial') {
      navigate('/signup?tier=trial');
    } else {
      navigate(`/checkout?tier=${tier.tier_code}&billing=${billingCycle}`);
    }
  };

  const isPopular = (tierCode) => tierCode === 'managed' || tierCode === 'byok';

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-purple-400 mx-auto mb-4"></div>
          <p className="text-slate-300">Loading pricing...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 backdrop-blur-lg border-b border-purple-500/20">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-white">Unicorn Commander</h1>
            </div>
            <button
              onClick={() => navigate('/auth/login')}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
            >
              Sign In
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-16">
        {/* Hero Section */}
        <div className="text-center mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
              Simple, Transparent Pricing
            </h1>
            <p className="text-xl text-slate-300 mb-8 max-w-3xl mx-auto">
              Choose the perfect plan for your needs. Start with a free trial, no credit card required.
            </p>
          </motion.div>

          {/* Billing Toggle */}
          <div className="flex items-center justify-center gap-4 mb-12">
            <span className={`text-lg font-medium ${billingCycle === 'monthly' ? 'text-white' : 'text-slate-400'}`}>
              Monthly
            </span>
            <button
              onClick={() => setBillingCycle(billingCycle === 'monthly' ? 'yearly' : 'monthly')}
              className="relative w-16 h-8 bg-slate-700 rounded-full transition-colors hover:bg-slate-600"
            >
              <div
                className={`absolute top-1 left-1 w-6 h-6 bg-purple-500 rounded-full transition-transform ${
                  billingCycle === 'yearly' ? 'translate-x-8' : ''
                }`}
              />
            </button>
            <span className={`text-lg font-medium ${billingCycle === 'yearly' ? 'text-white' : 'text-slate-400'}`}>
              Yearly
            </span>
            {billingCycle === 'yearly' && (
              <span className="px-3 py-1 bg-green-500/20 text-green-400 text-sm font-semibold rounded-full">
                Save up to 20%
              </span>
            )}
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
          {tiers.map((tier, index) => {
            const Icon = getTierIcon(tier.tier_code);
            const price = getPrice(tier);
            const popular = isPopular(tier.tier_code);

            return (
              <motion.div
                key={tier.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className={`relative rounded-2xl border ${
                  popular
                    ? 'border-purple-500 bg-slate-800/80'
                    : 'border-slate-700 bg-slate-800/50'
                } backdrop-blur-lg p-8 ${popular ? 'ring-2 ring-purple-500/50' : ''}`}
              >
                {popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="px-4 py-1 bg-gradient-to-r from-purple-500 to-pink-500 text-white text-sm font-bold rounded-full">
                      MOST POPULAR
                    </span>
                  </div>
                )}

                {/* Tier Header */}
                <div className="mb-6">
                  <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${getTierColor(tier.tier_code)} flex items-center justify-center mb-4`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <h3 className="text-2xl font-bold text-white mb-2">{tier.tier_name}</h3>
                  <p className="text-slate-400 text-sm">{tier.description}</p>
                </div>

                {/* Price */}
                <div className="mb-6">
                  {price.amount === 0 ? (
                    <div className="text-4xl font-bold text-white">Free</div>
                  ) : (
                    <>
                      <div className="flex items-baseline gap-1">
                        <span className="text-4xl font-bold text-white">${price.amount}</span>
                        <span className="text-slate-400">{price.period}</span>
                      </div>
                      {price.savings > 0 && (
                        <p className="text-green-400 text-sm mt-1">
                          Save ${price.savings.toFixed(2)}/year
                        </p>
                      )}
                    </>
                  )}
                </div>

                {/* CTA Button */}
                <button
                  onClick={() => handleSelectPlan(tier)}
                  className={`w-full py-3 px-4 rounded-lg font-semibold transition-all mb-6 ${
                    popular
                      ? 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white'
                      : 'bg-slate-700 hover:bg-slate-600 text-white'
                  }`}
                >
                  {tier.tier_code === 'trial' ? 'Start Free Trial' : 'Get Started'}
                  <ArrowRight className="w-4 h-4 inline ml-2" />
                </button>

                {/* Key Features */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-slate-300">
                    <Check className="w-5 h-5 text-green-400" />
                    <span className="text-sm">{tier.api_calls_limit.toLocaleString()} API calls/month</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-300">
                    <Users className="w-5 h-5 text-blue-400" />
                    <span className="text-sm">{tier.team_seats} team {tier.team_seats === 1 ? 'seat' : 'seats'}</span>
                  </div>
                  {tier.byok_enabled && (
                    <div className="flex items-center gap-2 text-slate-300">
                      <Shield className="w-5 h-5 text-purple-400" />
                      <span className="text-sm">BYOK (Bring Your Own Keys)</span>
                    </div>
                  )}
                  {tier.priority_support && (
                    <div className="flex items-center gap-2 text-slate-300">
                      <Zap className="w-5 h-5 text-yellow-400" />
                      <span className="text-sm">Priority Support</span>
                    </div>
                  )}
                </div>

                {/* All Features Link */}
                <div className="mt-6 pt-6 border-t border-slate-700">
                  <button
                    onClick={() => {
                      const element = document.getElementById('feature-comparison');
                      element?.scrollIntoView({ behavior: 'smooth' });
                    }}
                    className="text-purple-400 hover:text-purple-300 text-sm font-medium"
                  >
                    View all features →
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Enterprise Tier */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="rounded-2xl border border-amber-500/50 bg-gradient-to-br from-amber-500/10 to-orange-500/10 backdrop-blur-lg p-8 mb-16"
        >
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                  <Crown className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-white">Enterprise</h3>
                  <p className="text-amber-300">Custom solutions for large teams</p>
                </div>
              </div>
              <ul className="space-y-2 text-slate-300">
                <li className="flex items-center gap-2">
                  <Check className="w-5 h-5 text-green-400" />
                  <span>Unlimited API calls</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-5 h-5 text-green-400" />
                  <span>Unlimited team seats</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-5 h-5 text-green-400" />
                  <span>Dedicated account manager</span>
                </li>
                <li className="flex items-center gap-2">
                  <Check className="w-5 h-5 text-green-400" />
                  <span>Custom integrations & SLA</span>
                </li>
              </ul>
            </div>
            <div className="text-center md:text-right">
              <p className="text-3xl font-bold text-white mb-4">Custom Pricing</p>
              <button
                onClick={() => navigate('/contact-sales')}
                className="px-8 py-3 bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white font-semibold rounded-lg transition-all"
              >
                Contact Sales
              </button>
            </div>
          </div>
        </motion.div>

        {/* Feature Comparison Table */}
        <div id="feature-comparison" className="mb-16">
          <h2 className="text-3xl font-bold text-white text-center mb-8">
            Compare All Features
          </h2>
          <div className="bg-slate-800/50 backdrop-blur-lg rounded-2xl border border-slate-700 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left p-4 text-slate-300 font-semibold">Feature</th>
                    {tiers.map(tier => (
                      <th key={tier.id} className="text-center p-4 text-white font-semibold">
                        {tier.tier_name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.keys(features).length > 0 && features[tiers[0]?.tier_code]?.map((feature, index) => (
                    <tr key={index} className="border-b border-slate-700/50">
                      <td className="p-4 text-slate-300">{feature.feature_name}</td>
                      {tiers.map(tier => {
                        const tierFeature = features[tier.tier_code]?.find(f => f.feature_name === feature.feature_name);
                        return (
                          <td key={tier.id} className="text-center p-4">
                            {tierFeature?.enabled ? (
                              <Check className="w-5 h-5 text-green-400 mx-auto" />
                            ) : (
                              <X className="w-5 h-5 text-slate-600 mx-auto" />
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Frequently Asked Questions
          </h2>
          <p className="text-slate-400 mb-8">
            Need help? Check our{' '}
            <button
              onClick={() => navigate('/docs')}
              className="text-purple-400 hover:text-purple-300 underline"
            >
              documentation
            </button>
            {' '}or{' '}
            <button
              onClick={() => navigate('/contact')}
              className="text-purple-400 hover:text-purple-300 underline"
            >
              contact support
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Pricing;
