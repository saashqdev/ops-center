/**
 * Stripe Provider Wrapper
 * Provides Stripe.js context to the application
 */

import React, { useEffect, useState } from 'react';
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
  const [stripePromise, setStripePromise] = useState(null);
  const [stripeError, setStripeError] = useState(null);
  const [stripeLoading, setStripeLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    const initStripe = async () => {
      try {
        if (STRIPE_PUBLISHABLE_KEY) {
          if (isMounted) setStripePromise(loadStripe(STRIPE_PUBLISHABLE_KEY));
          return;
        }

        const response = await fetch('/api/v1/checkout/config');
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        if (!data?.publishable_key) {
          throw new Error('Stripe publishable key not available');
        }

        if (isMounted) setStripePromise(loadStripe(data.publishable_key));
      } catch (error) {
        console.warn('Stripe key not configured:', error);
        if (isMounted) setStripeError(error);
      } finally {
        if (isMounted) setStripeLoading(false);
      }
    };

    initStripe();

    return () => {
      isMounted = false;
    };
  }, []);

  // Don't render Elements if Stripe is not available
  if (!stripePromise && !stripeLoading) {
    return (
      <Box>
        <Alert severity="warning" sx={{ mb: 3 }}>
          Stripe payment processing is not configured. Please add your Stripe publishable key to the environment configuration (VITE_STRIPE_PUBLISHABLE_KEY).
        </Alert>
        {children}
      </Box>
    );
  }

  return (
    <Elements stripe={stripePromise}>
      {children}
    </Elements>
  );
};

export default StripeProvider;
