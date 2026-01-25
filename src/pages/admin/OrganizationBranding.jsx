import React, { useState, useEffect } from 'react';
import { 
  Save, Upload, RefreshCw, Palette, Building2, Globe, 
  Mail, Link as LinkIcon, Eye, AlertCircle, Check, X 
} from 'lucide-react';

const OrganizationBranding = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('colors');
  const [previewMode, setPreviewMode] = useState(false);
  const [message, setMessage] = useState(null);
  const [tierLimits, setTierLimits] = useState(null);
  
  // Get org_id from session or use default for testing
  const orgId = sessionStorage.getItem('org_id') || 'default-org';
  
  const [branding, setBranding] = useState({
    org_id: orgId,
    org_name: '',
    colors: {
      primary_color: '#3B82F6',
      secondary_color: '#10B981',
      accent_color: '#F59E0B',
      text_color: '#1F2937',
      background_color: '#FFFFFF'
    },
    typography: {
      font_family: 'Inter',
      heading_font: 'Poppins'
    },
    company_info: {
      company_name: '',
      tagline: '',
      description: '',
      support_email: '',
      support_phone: ''
    },
    social_links: {
      twitter_url: '',
      linkedin_url: '',
      github_url: '',
      discord_url: ''
    },
    custom_domain: {
      custom_domain: '',
      domain_verified: false,
      ssl_enabled: false
    },
    email_branding: {
      email_from_name: '',
      email_from_address: '',
      email_logo_url: '',
      email_footer_text: ''
    },
    features: {
      custom_logo_enabled: false,
      custom_colors_enabled: true,
      custom_domain_enabled: false,
      custom_email_enabled: false,
      white_label_enabled: false
    }
  });

  useEffect(() => {
    loadBranding();
    loadTierLimits();
  }, []);

  const loadBranding = async () => {
    try {
      const response = await fetch(`/api/v1/organizations/${orgId}/branding/`);
      if (response.ok) {
        const data = await response.json();
        // Map API response to form state
        setBranding({
          org_id: data.org_id,
          org_name: data.org_name,
          colors: {
            primary_color: data.primary_color || '#3B82F6',
            secondary_color: data.secondary_color || '#10B981',
            accent_color: data.accent_color || '#F59E0B',
            text_color: data.text_color || '#1F2937',
            background_color: data.background_color || '#FFFFFF'
          },
          typography: {
            font_family: data.font_family || 'Inter',
            heading_font: data.heading_font || 'Poppins'
          },
          company_info: {
            company_name: data.company_name || '',
            tagline: data.tagline || '',
            description: data.description || '',
            support_email: data.support_email || '',
            support_phone: data.support_phone || ''
          },
          social_links: {
            twitter_url: data.twitter_url || '',
            linkedin_url: data.linkedin_url || '',
            github_url: data.github_url || '',
            discord_url: data.discord_url || ''
          },
          custom_domain: {
            custom_domain: data.custom_domain || '',
            domain_verified: data.custom_domain_verified || false,
            ssl_enabled: data.custom_domain_ssl_enabled || false
          },
          email_branding: {
            email_from_name: data.email_from_name || '',
            email_from_address: data.email_from_address || '',
            email_logo_url: data.email_logo_url || '',
            email_footer_text: data.email_footer_text || ''
          },
          features: {
            custom_logo_enabled: data.custom_logo_enabled || false,
            custom_colors_enabled: data.custom_colors_enabled || true,
            custom_domain_enabled: data.custom_domain_enabled || false,
            custom_email_enabled: data.custom_email_enabled || false,
            white_label_enabled: data.white_label_enabled || false
          }
        });
      }
    } catch (error) {
      console.error('Failed to load branding:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadTierLimits = async () => {
    try {
      const response = await fetch(`/api/v1/organizations/${orgId}/branding/limits/`);
      if (response.ok) {
        const data = await response.json();
        setTierLimits(data);
      }
    } catch (error) {
      console.error('Failed to load tier limits:', error);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    
    try {
      // First try to update (PUT)
      let response = await fetch(`/api/v1/organizations/${orgId}/branding/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(branding)
      });

      // If not found, create (POST)
      if (response.status === 404) {
        response = await fetch(`/api/v1/organizations/${orgId}/branding/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(branding)
        });
      }

      if (response.ok) {
        const data = await response.json();
        setMessage({ type: 'success', text: 'Branding saved successfully!' });
        // Reload to get updated data
        await loadBranding();
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Failed to save branding' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error: ' + error.message });
    } finally {
      setSaving(false);
    }
  };

  const updateColors = (colorKey, value) => {
    setBranding(prev => ({
      ...prev,
      colors: { ...prev.colors, [colorKey]: value }
    }));
  };

  const updateCompanyInfo = (field, value) => {
    setBranding(prev => ({
      ...prev,
      company_info: { ...prev.company_info, [field]: value }
    }));
  };

  const updateSocialLinks = (platform, value) => {
    setBranding(prev => ({
      ...prev,
      social_links: { ...prev.social_links, [platform]: value }
    }));
  };

  const updateCustomDomain = (field, value) => {
    setBranding(prev => ({
      ...prev,
      custom_domain: { ...prev.custom_domain, [field]: value }
    }));
  };

  const updateEmailBranding = (field, value) => {
    setBranding(prev => ({
      ...prev,
      email_branding: { ...prev.email_branding, [field]: value }
    }));
  };

  const ColorPicker = ({ label, value, onChange, disabled }) => (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">{label}</label>
      <div className="flex items-center space-x-3">
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="h-10 w-20 rounded border border-gray-300 cursor-pointer disabled:opacity-50"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
          placeholder="#3B82F6"
        />
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const canUseFeature = (feature) => {
    if (!tierLimits) return true;
    return tierLimits[feature] === true;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Organization Branding</h1>
              <p className="mt-1 text-sm text-gray-500">
                Customize your organization's appearance and identity
                {tierLimits && (
                  <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                    {tierLimits.tier_code.toUpperCase()} TIER
                  </span>
                )}
              </p>
            </div>
            <div className="flex space-x-3">
              <button
                onClick={() => setPreviewMode(!previewMode)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <Eye className="w-4 h-4 mr-2" />
                {previewMode ? 'Edit' : 'Preview'}
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {saving ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save Changes
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Success/Error Message */}
          {message && (
            <div className={`mt-4 p-4 rounded-md ${
              message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
            }`}>
              <div className="flex items-center">
                {message.type === 'success' ? (
                  <Check className="w-5 h-5 mr-2" />
                ) : (
                  <AlertCircle className="w-5 h-5 mr-2" />
                )}
                {message.text}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'colors', label: 'Colors', icon: Palette },
              { id: 'company', label: 'Company Info', icon: Building2 },
              { id: 'social', label: 'Social Links', icon: LinkIcon },
              { id: 'domain', label: 'Custom Domain', icon: Globe },
              { id: 'email', label: 'Email Branding', icon: Mail }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                } flex items-center whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                <tab.icon className="w-5 h-5 mr-2" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="mt-8 bg-white shadow rounded-lg p-6">
          {/* Colors Tab */}
          {activeTab === 'colors' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Color Scheme</h3>
                {!canUseFeature('custom_colors') && (
                  <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                    <p className="text-sm text-yellow-800">
                      Custom colors are not available in your current tier. Upgrade to enable this feature.
                    </p>
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <ColorPicker
                    label="Primary Color"
                    value={branding.colors.primary_color}
                    onChange={(val) => updateColors('primary_color', val)}
                    disabled={!canUseFeature('custom_colors')}
                  />
                  <ColorPicker
                    label="Secondary Color"
                    value={branding.colors.secondary_color}
                    onChange={(val) => updateColors('secondary_color', val)}
                    disabled={!canUseFeature('custom_colors')}
                  />
                  <ColorPicker
                    label="Accent Color"
                    value={branding.colors.accent_color}
                    onChange={(val) => updateColors('accent_color', val)}
                    disabled={!canUseFeature('custom_colors')}
                  />
                  <ColorPicker
                    label="Text Color"
                    value={branding.colors.text_color}
                    onChange={(val) => updateColors('text_color', val)}
                    disabled={!canUseFeature('custom_colors')}
                  />
                  <ColorPicker
                    label="Background Color"
                    value={branding.colors.background_color}
                    onChange={(val) => updateColors('background_color', val)}
                    disabled={!canUseFeature('custom_colors')}
                  />
                </div>
              </div>

              {/* Preview */}
              <div className="mt-8 p-6 border border-gray-200 rounded-lg" style={{
                backgroundColor: branding.colors.background_color,
                color: branding.colors.text_color
              }}>
                <h4 className="text-sm font-medium text-gray-500 mb-4">Preview</h4>
                <div className="space-y-3">
                  <button
                    className="px-4 py-2 rounded-md font-medium text-white"
                    style={{ backgroundColor: branding.colors.primary_color }}
                  >
                    Primary Button
                  </button>
                  <button
                    className="px-4 py-2 rounded-md font-medium text-white ml-2"
                    style={{ backgroundColor: branding.colors.secondary_color }}
                  >
                    Secondary Button
                  </button>
                  <button
                    className="px-4 py-2 rounded-md font-medium text-white ml-2"
                    style={{ backgroundColor: branding.colors.accent_color }}
                  >
                    Accent Button
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Company Info Tab */}
          {activeTab === 'company' && (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900">Company Information</h3>
              <div className="grid grid-cols-1 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Company Name</label>
                  <input
                    type="text"
                    value={branding.company_info.company_name}
                    onChange={(e) => updateCompanyInfo('company_name', e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Acme Corporation"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Tagline</label>
                  <input
                    type="text"
                    value={branding.company_info.tagline}
                    onChange={(e) => updateCompanyInfo('tagline', e.target.value)}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Innovation at Scale"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Description</label>
                  <textarea
                    value={branding.company_info.description}
                    onChange={(e) => updateCompanyInfo('description', e.target.value)}
                    rows="4"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Tell us about your company..."
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Support Email</label>
                    <input
                      type="email"
                      value={branding.company_info.support_email}
                      onChange={(e) => updateCompanyInfo('support_email', e.target.value)}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                      placeholder="support@company.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Support Phone</label>
                    <input
                      type="tel"
                      value={branding.company_info.support_phone}
                      onChange={(e) => updateCompanyInfo('support_phone', e.target.value)}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                      placeholder="+1-555-0100"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Social Links Tab */}
          {activeTab === 'social' && (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900">Social Media Links</h3>
              <div className="grid grid-cols-1 gap-6">
                {[
                  { key: 'twitter_url', label: 'Twitter URL', placeholder: 'https://twitter.com/company' },
                  { key: 'linkedin_url', label: 'LinkedIn URL', placeholder: 'https://linkedin.com/company/company' },
                  { key: 'github_url', label: 'GitHub URL', placeholder: 'https://github.com/company' },
                  { key: 'discord_url', label: 'Discord URL', placeholder: 'https://discord.gg/company' }
                ].map((field) => (
                  <div key={field.key}>
                    <label className="block text-sm font-medium text-gray-700">{field.label}</label>
                    <input
                      type="url"
                      value={branding.social_links[field.key]}
                      onChange={(e) => updateSocialLinks(field.key, e.target.value)}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                      placeholder={field.placeholder}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Custom Domain Tab */}
          {activeTab === 'domain' && (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900">Custom Domain</h3>
              {!canUseFeature('custom_domain') && (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                  <p className="text-sm text-yellow-800">
                    Custom domain is not available in your current tier. Upgrade to Professional or higher.
                  </p>
                </div>
              )}
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Domain</label>
                  <input
                    type="text"
                    value={branding.custom_domain.custom_domain}
                    onChange={(e) => updateCustomDomain('custom_domain', e.target.value)}
                    disabled={!canUseFeature('custom_domain')}
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    placeholder="app.company.com"
                  />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={branding.custom_domain.domain_verified}
                      onChange={(e) => updateCustomDomain('domain_verified', e.target.checked)}
                      disabled={!canUseFeature('custom_domain')}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50"
                    />
                    <label className="text-sm font-medium text-gray-700">Domain Verified</label>
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={branding.custom_domain.ssl_enabled}
                      onChange={(e) => updateCustomDomain('ssl_enabled', e.target.checked)}
                      disabled={!canUseFeature('custom_domain')}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50"
                    />
                    <label className="text-sm font-medium text-gray-700">SSL Enabled</label>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Email Branding Tab */}
          {activeTab === 'email' && (
            <div className="space-y-6">
              <h3 className="text-lg font-medium text-gray-900">Email Branding</h3>
              {!canUseFeature('custom_email_branding') && (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                  <p className="text-sm text-yellow-800">
                    Email branding is not available in your current tier. Upgrade to enable this feature.
                  </p>
                </div>
              )}
              <div className="grid grid-cols-1 gap-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">From Name</label>
                    <input
                      type="text"
                      value={branding.email_branding.email_from_name}
                      onChange={(e) => updateEmailBranding('email_from_name', e.target.value)}
                      disabled={!canUseFeature('custom_email_branding')}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                      placeholder="Company Support"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">From Address</label>
                    <input
                      type="email"
                      value={branding.email_branding.email_from_address}
                      onChange={(e) => updateEmailBranding('email_from_address', e.target.value)}
                      disabled={!canUseFeature('custom_email_branding')}
                      className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                      placeholder="noreply@company.com"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Email Footer Text</label>
                  <textarea
                    value={branding.email_branding.email_footer_text}
                    onChange={(e) => updateEmailBranding('email_footer_text', e.target.value)}
                    disabled={!canUseFeature('custom_email_branding')}
                    rows="3"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    placeholder="© 2026 Company Name. All rights reserved."
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Tier Limits Info */}
        {tierLimits && (
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="text-lg font-medium text-blue-900 mb-4">Your Tier Limits</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-blue-700">Max Logo Size:</span>
                <span className="ml-2 font-medium text-blue-900">{tierLimits.max_logo_size_mb}MB</span>
              </div>
              <div>
                <span className="text-blue-700">Max Assets:</span>
                <span className="ml-2 font-medium text-blue-900">{tierLimits.max_assets}</span>
              </div>
              <div>
                <span className="text-blue-700">Custom Colors:</span>
                <span className="ml-2 font-medium text-blue-900">
                  {tierLimits.custom_colors ? '✓ Yes' : '✗ No'}
                </span>
              </div>
              <div>
                <span className="text-blue-700">Custom Domain:</span>
                <span className="ml-2 font-medium text-blue-900">
                  {tierLimits.custom_domain ? '✓ Yes' : '✗ No'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrganizationBranding;
