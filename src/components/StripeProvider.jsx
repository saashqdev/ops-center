/**
 * Stripe Provider Wrapper
 * Provides Stripe.js context to the application
 */

import React, { useMemo } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements } from '@stripe/react-stripe-js';
import { Alert, Box } from '@mui/material';

// Load Stripe publishable key from environment
const STRIPE_PUBLISHABLE_KEY = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY;

/**
 * StripeProvider Component
 *
 * Wraps children with Stripe Elements provider for payment processing
 */
export const StripeProvider = ({ children }) => {
  // Memoize stripe promise to avoid recreating on every render
  const stripePromise = useMemo(() => {
    if (!STRIPE_PUBLISHABLE_KEY) {
      console.warn('VITE_STRIPE_PUBLISHABLE_KEY not configured');
      return null;
    }
    return loadStripe(STRIPE_PUBLISHABLE_KEY);
  }, []);

  // Show message if Stripe key is missing
  if (!stripePromise) {
    return (
      <>
        <Alert severity="warning" sx={{ mb: 3 }}>
          Stripe payment processing is not configured. Please add your Stripe publishable key to the environment configuration (VITE_STRIPE_PUBLISHABLE_KEY).
        </Alert>
        {children}
      </>
    );
  }

  return (
    <Elements stripe={stripePromise}>
      {children}
    </Elements>
  );
};

export default StripeProvider;
