import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  CardMedia,
  CardActions,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Stack,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import {
  ShoppingCart as ShoppingCartIcon,
  CheckCircle as CheckIcon,
  TrendingUp as UpgradeIcon,
  Public as PublicIcon,
  Business as BusinessIcon,
  AttachMoney as MoneyIcon
} from '@mui/icons-material';

/**
 * AppMarketplace - Browse & Purchase Apps
 *
 * Shows apps NOT in user's current tier:
 * - Premium apps (can be purchased individually)
 * - Higher-tier apps (requires tier upgrade)
 *
 * Fetches from /api/v1/my-apps/marketplace
 * Shows pricing, tier requirements, and where apps are hosted.
 */
const AppMarketplace = () => {
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    console.log('📦 AppMarketplace Component Loaded - v2.10.02:15');
    fetchMarketplaceApps();
  }, []);

  const fetchMarketplaceApps = async () => {
    try {
      const response = await fetch('/api/v1/my-apps/marketplace');
      if (!response.ok) throw new Error('Failed to fetch marketplace apps');

      const data = await response.json();
      setApps(data);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching marketplace apps:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  const getHostBadge = (launch_url) => {
    try {
      const url = new URL(launch_url);
      const host = url.hostname;

      if (host.includes('your-domain.com')) {
        return { label: 'UC Hosted', icon: <BusinessIcon />, color: 'primary' };
      } else {
        return { label: 'Federated Service', icon: <PublicIcon />, color: 'secondary' };
      }
    } catch (e) {
      return { label: 'External', icon: <PublicIcon />, color: 'default' };
    }
  };

  const handlePurchase = (app) => {
    // TODO: Implement purchase flow
    console.log('Purchase app:', app);
    alert(`Purchase flow for ${app.name} - Coming soon!`);
  };

  const handleUpgrade = (app) => {
    // Redirect to upgrade page
    window.location.href = '/admin/upgrade';
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">Error loading marketplace: {error}</Alert>
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Box mb={4}>
        <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
          App Marketplace
        </Typography>
        <Typography variant="body1" sx={{ color: '#c084fc' }}>
          Discover premium apps and upgrade your subscription for more features
        </Typography>
      </Box>

      <Box 
        sx={{ 
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            sm: 'repeat(2, 1fr)',
            md: 'repeat(3, 1fr)'
          },
          gap: 3,
          width: '100%'
        }}
      >
        {apps.map((app) => {
          const hostBadge = getHostBadge(app.launch_url);
          const isPurchasable = app.access_type === 'premium_purchase';
          const requiresUpgrade = app.access_type === 'upgrade_required';

          return (
            <Card
              key={app.id}
              sx={{
                height: '100%',
                minHeight: 480,
                width: '100%',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                overflow: 'hidden',
                '&:hover': {
                  boxShadow: 6,
                  transform: 'translateY(-4px)',
                  transition: 'all 0.3s'
                }
              }}
            >
                {/* App Icon */}
                <Box
                  sx={{
                    p: 3,
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    bgcolor: 'background.default',
                    height: 140,
                    position: 'relative'
                  }}
                >
                  {/* Host Badge */}
                  <Box sx={{ position: 'absolute', top: 12, right: 12 }}>
                    <Chip
                      icon={hostBadge.icon}
                      label={hostBadge.label}
                      size="small"
                      color={hostBadge.color}
                      sx={{ fontSize: '0.7rem' }}
                    />
                  </Box>

                  {app.icon_url ? (
                    <CardMedia
                      component="img"
                      image={app.icon_url}
                      alt={app.name}
                      sx={{
                        width: 80,
                        height: 80,
                        objectFit: 'contain'
                      }}
                    />
                  ) : (
                    <ShoppingCartIcon sx={{ fontSize: 80, color: 'text.secondary' }} />
                  )}
                </Box>

                {/* App Details */}
                <CardContent sx={{ 
                  flex: 1,
                  display: 'flex', 
                  flexDirection: 'column',
                  pt: 2,
                  pb: 1,
                  minHeight: 0,
                  overflow: 'hidden'
                }}>
                  <Typography variant="h6" gutterBottom sx={{ 
                    minHeight: 32,
                    mb: 1,
                    fontWeight: 'bold'
                  }}>
                    {app.name}
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ 
                      mb: 2,
                      minHeight: 48,
                      maxHeight: 48,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical'
                    }}
                  >
                    {app.description || 'No description available'}
                  </Typography>

                  {/* Spacer */}
                  <Box sx={{ flexGrow: 1 }} />

                  <Divider sx={{ mb: 2 }} />

                  {/* Pricing Info */}
                  <Box sx={{ mt: 1, p: 1.5, bgcolor: 'action.hover', borderRadius: 1 }}>
                    {isPurchasable && (
                      <Stack direction="row" alignItems="center" spacing={1} justifyContent="center">
                        <MoneyIcon color="primary" fontSize="small" />
                        <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                          ${app.price || 0}/{app.billing_type || 'month'}
                        </Typography>
                      </Stack>
                    )}
                    {requiresUpgrade && (
                      <Chip
                        icon={<UpgradeIcon />}
                        label="Upgrade Required"
                        color="warning"
                        size="small"
                        sx={{ width: '100%' }}
                      />
                    )}
                  </Box>
                </CardContent>

                <CardActions sx={{ p: 2, pt: 0, mt: 'auto' }}>
                  {isPurchasable && (
                    <Button
                      variant="contained"
                      color="primary"
                      fullWidth
                      size="large"
                      startIcon={<ShoppingCartIcon />}
                      onClick={() => handlePurchase(app)}
                    >
                      Purchase
                    </Button>
                  )}
                  {requiresUpgrade && (
                    <Button
                      variant="outlined"
                      color="warning"
                      fullWidth
                      size="large"
                      startIcon={<UpgradeIcon />}
                      onClick={() => handleUpgrade(app)}
                    >
                      Upgrade Tier
                    </Button>
                  )}
                </CardActions>
              </Card>
          );
        })}
      </Box>

      {apps.length === 0 && (
        <Box textAlign="center" py={8}>
          <Typography variant="h6" sx={{ color: '#D1D5DB' }} gutterBottom>
            No additional apps available
          </Typography>
          <Typography variant="body2" sx={{ color: '#D1D5DB' }}>
            You have access to all apps in your subscription tier!
          </Typography>
          <Button
            variant="contained"
            color="primary"
            sx={{ mt: 3 }}
            onClick={() => window.location.href = '/admin/apps'}
          >
            View My Apps
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default AppMarketplace;
