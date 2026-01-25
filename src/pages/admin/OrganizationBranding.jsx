import React, { useState, useEffect, useRef } from 'react';
import { 
  Save, Upload, RefreshCw, Palette, Building2, Globe, 
  Mail, Link as LinkIcon, Eye, AlertCircle, Check, X,
  Image, Trash2, FileImage, Copy, CheckCircle
} from 'lucide-react';

const OrganizationBranding = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('colors');
  const [previewMode, setPreviewMode] = useState(false);
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  const [message, setMessage] = useState(null);
  const [tierLimits, setTierLimits] = useState(null);
  const [assets, setAssets] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [verifyingDomain, setVerifyingDomain] = useState(false);
  const [dnsRecord, setDnsRecord] = useState(null);
  const fileInputRef = useRef(null);
  
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
    loadAssets();
    generateDnsRecord();
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

  const loadAssets = async () => {
    try {
      const response = await fetch(`/api/v1/organizations/${orgId}/branding/assets/`);
      if (response.ok) {
        const data = await response.json();
        setAssets(data);
      }
    } catch (error) {
      console.error('Failed to load assets:', error);
    }
  };

  const generateDnsRecord = () => {
    // Generate unique TXT record for domain verification
    const timestamp = Date.now();
    const recordValue = `ops-center-verify=${orgId}-${timestamp}`;
    setDnsRecord({
      type: 'TXT',
      name: '_ops-center-verification',
      value: recordValue,
      ttl: '3600'
    });
  };

  const handleFileUpload = async (files, assetType = 'logo') => {
    if (!files || files.length === 0) return;
    
    const file = files[0];
    
    // Check file size against tier limits
    const maxSizeMB = tierLimits?.max_logo_size_mb || 5;
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    
    if (file.size > maxSizeBytes) {
      setMessage({ 
        type: 'error', 
        text: `File too large. Maximum size is ${maxSizeMB}MB for your tier.` 
      });
      return;
    }

    // Check asset count against tier limits
    const maxAssets = tierLimits?.max_assets || 10;
    if (assets.length >= maxAssets) {
      setMessage({ 
        type: 'error', 
        text: `Asset limit reached. Maximum ${maxAssets} assets allowed for your tier.` 
      });
      return;
    }

    setUploading(true);
    setMessage(null);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('asset_type', assetType);

      const response = await fetch(`/api/v1/organizations/${orgId}/branding/assets/upload/`, {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        setMessage({ type: 'success', text: `${assetType} uploaded successfully!` });
        
        // Update the appropriate branding field based on asset type
        if (assetType === 'logo') {
          setBranding(prev => ({ ...prev, logo_url: data.asset_url }));
        } else if (assetType === 'favicon') {
          setBranding(prev => ({ ...prev, favicon_url: data.asset_url }));
        } else if (assetType === 'background') {
          setBranding(prev => ({ ...prev, background_image_url: data.asset_url }));
        } else if (assetType === 'email_logo') {
          setBranding(prev => ({
            ...prev,
            email_branding: { ...prev.email_branding, email_logo_url: data.asset_url }
          }));
        }
        
        await loadAssets();
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Upload failed' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error: ' + error.message });
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteAsset = async (assetId) => {
    if (!confirm('Are you sure you want to delete this asset?')) return;

    try {
      const response = await fetch(`/api/v1/organizations/${orgId}/branding/assets/${assetId}/`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Asset deleted successfully!' });
        await loadAssets();
      } else {
        const error = await response.json();
        setMessage({ type: 'error', text: error.detail || 'Delete failed' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error: ' + error.message });
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files, 'logo');
    }
  };

  const verifyDomain = async () => {
    setVerifyingDomain(true);
    setMessage(null);

    try {
      // Simulate domain verification API call
      // In production, this would check DNS records
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // For demo, randomly succeed or fail
      const verified = Math.random() > 0.3;
      
      if (verified) {
        updateCustomDomain('domain_verified', true);
        setMessage({ type: 'success', text: 'Domain verified successfully!' });
      } else {
        setMessage({ 
          type: 'error', 
          text: 'Domain verification failed. Please check your DNS records and try again.' 
        });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Verification failed: ' + error.message });
    } finally {
      setVerifyingDomain(false);
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    setMessage({ type: 'success', text: 'Copied to clipboard!' });
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
                onClick={() => setShowPreviewModal(true)}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <Eye className="w-4 h-4 mr-2" />
                Preview
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
              { id: 'assets', label: 'Assets', icon: Image },
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

          {/* Assets Tab */}
          {activeTab === 'assets' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-4">Asset Management</h3>
                {!canUseFeature('custom_logo') && (
                  <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                    <p className="text-sm text-yellow-800">
                      Asset uploads are not available in your current tier. Upgrade to enable this feature.
                    </p>
                  </div>
                )}

                {/* File Upload Area */}
                <div
                  className={`relative border-2 border-dashed rounded-lg p-8 text-center ${
                    dragActive 
                      ? 'border-blue-500 bg-blue-50' 
                      : 'border-gray-300 hover:border-gray-400'
                  } ${!canUseFeature('custom_logo') ? 'opacity-50 pointer-events-none' : ''}`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={(e) => handleFileUpload(e.target.files, 'logo')}
                    className="hidden"
                    disabled={!canUseFeature('custom_logo')}
                  />
                  
                  <FileImage className="mx-auto h-12 w-12 text-gray-400" />
                  <div className="mt-4">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      disabled={uploading || !canUseFeature('custom_logo')}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                    >
                      {uploading ? (
                        <>
                          <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                          Uploading...
                        </>
                      ) : (
                        <>
                          <Upload className="w-4 h-4 mr-2" />
                          Upload Image
                        </>
                      )}
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    or drag and drop PNG, JPG, SVG up to {tierLimits?.max_logo_size_mb || 5}MB
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    {assets.length} / {tierLimits?.max_assets || 10} assets used
                  </p>
                </div>

                {/* Asset Gallery */}
                <div className="mt-6">
                  <h4 className="text-sm font-medium text-gray-900 mb-4">Uploaded Assets</h4>
                  {assets.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <Image className="mx-auto h-12 w-12 text-gray-400 mb-2" />
                      <p className="text-sm">No assets uploaded yet</p>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {assets.map((asset) => (
                        <div key={asset.id} className="relative group border border-gray-200 rounded-lg p-3 hover:shadow-md transition-shadow">
                          <div className="aspect-square bg-gray-100 rounded-md mb-2 flex items-center justify-center overflow-hidden">
                            <img
                              src={asset.asset_url}
                              alt={asset.file_name}
                              className="max-w-full max-h-full object-contain"
                            />
                          </div>
                          <div className="text-xs text-gray-600 truncate" title={asset.file_name}>
                            {asset.file_name}
                          </div>
                          <div className="text-xs text-gray-400">
                            {(asset.file_size / 1024 / 1024).toFixed(2)} MB
                          </div>
                          <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => handleDeleteAsset(asset.id)}
                              className="p-1 bg-red-600 text-white rounded-md hover:bg-red-700"
                              title="Delete asset"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
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

                {/* DNS Verification Section */}
                {canUseFeature('custom_domain') && branding.custom_domain.custom_domain && (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-6">
                    <h4 className="text-sm font-medium text-gray-900 mb-4">
                      Domain Verification
                      {branding.custom_domain.domain_verified && (
                        <span className="ml-2 inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                          <CheckCircle className="w-3 h-3 mr-1" />
                          Verified
                        </span>
                      )}
                    </h4>
                    
                    {!branding.custom_domain.domain_verified && (
                      <>
                        <p className="text-sm text-gray-600 mb-4">
                          Add the following DNS record to verify your domain:
                        </p>
                        
                        {dnsRecord && (
                          <div className="bg-white border border-gray-300 rounded-md p-4 mb-4 font-mono text-sm">
                            <div className="grid grid-cols-4 gap-4">
                              <div>
                                <div className="text-xs text-gray-500 mb-1">Type</div>
                                <div className="flex items-center">
                                  <span className="font-medium">{dnsRecord.type}</span>
                                  <button
                                    onClick={() => copyToClipboard(dnsRecord.type)}
                                    className="ml-2 text-gray-400 hover:text-gray-600"
                                  >
                                    <Copy className="w-3 h-3" />
                                  </button>
                                </div>
                              </div>
                              <div>
                                <div className="text-xs text-gray-500 mb-1">Name</div>
                                <div className="flex items-center">
                                  <span className="font-medium truncate">{dnsRecord.name}</span>
                                  <button
                                    onClick={() => copyToClipboard(dnsRecord.name)}
                                    className="ml-2 text-gray-400 hover:text-gray-600"
                                  >
                                    <Copy className="w-3 h-3" />
                                  </button>
                                </div>
                              </div>
                              <div className="col-span-2">
                                <div className="text-xs text-gray-500 mb-1">Value</div>
                                <div className="flex items-center">
                                  <span className="font-medium truncate">{dnsRecord.value}</span>
                                  <button
                                    onClick={() => copyToClipboard(dnsRecord.value)}
                                    className="ml-2 text-gray-400 hover:text-gray-600"
                                  >
                                    <Copy className="w-3 h-3" />
                                  </button>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}

                        <button
                          onClick={verifyDomain}
                          disabled={verifyingDomain}
                          className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
                        >
                          {verifyingDomain ? (
                            <>
                              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                              Verifying...
                            </>
                          ) : (
                            <>
                              <CheckCircle className="w-4 h-4 mr-2" />
                              Verify Domain
                            </>
                          )}
                        </button>

                        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
                          <p className="text-xs text-blue-800">
                            💡 <strong>Tip:</strong> DNS changes can take up to 48 hours to propagate. 
                            You can verify your domain anytime after adding the DNS record.
                          </p>
                        </div>
                      </>
                    )}

                    {branding.custom_domain.domain_verified && (
                      <div className="p-3 bg-green-50 border border-green-200 rounded-md">
                        <p className="text-sm text-green-800">
                          ✓ Your domain has been verified successfully!
                        </p>
                      </div>
                    )}
                  </div>
                )}

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
                      disabled={!canUseFeature('custom_domain') || !branding.custom_domain.domain_verified}
                      className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded disabled:opacity-50"
                    />
                    <label className="text-sm font-medium text-gray-700">
                      SSL Enabled {!branding.custom_domain.domain_verified && '(Verify domain first)'}
                    </label>
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

      {/* Preview Modal */}
      {showPreviewModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            {/* Background overlay */}
            <div 
              className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" 
              onClick={() => setShowPreviewModal(false)}
            ></div>

            {/* Modal panel */}
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">Branding Preview</h3>
                  <button
                    onClick={() => setShowPreviewModal(false)}
                    className="text-gray-400 hover:text-gray-500"
                  >
                    <X className="w-6 h-6" />
                  </button>
                </div>

                {/* Preview Content */}
                <div 
                  className="border rounded-lg p-8 space-y-6"
                  style={{
                    backgroundColor: branding.colors.background_color,
                    color: branding.colors.text_color
                  }}
                >
                  {/* Header Preview */}
                  <div className="border-b pb-4" style={{ borderColor: branding.colors.primary_color }}>
                    <h1 className="text-3xl font-bold" style={{ 
                      fontFamily: branding.typography.heading_font,
                      color: branding.colors.primary_color 
                    }}>
                      {branding.company_info.company_name || 'Your Company'}
                    </h1>
                    {branding.company_info.tagline && (
                      <p className="mt-2 text-lg" style={{ color: branding.colors.secondary_color }}>
                        {branding.company_info.tagline}
                      </p>
                    )}
                  </div>

                  {/* Content Preview */}
                  <div className="space-y-4">
                    <p style={{ fontFamily: branding.typography.font_family }}>
                      {branding.company_info.description || 'Your company description will appear here.'}
                    </p>

                    {/* Button Previews */}
                    <div className="flex flex-wrap gap-3 pt-4">
                      <button
                        className="px-6 py-3 rounded-md font-medium text-white transition-colors"
                        style={{ 
                          backgroundColor: branding.colors.primary_color,
                          fontFamily: branding.typography.font_family
                        }}
                      >
                        Primary Action
                      </button>
                      <button
                        className="px-6 py-3 rounded-md font-medium text-white transition-colors"
                        style={{ 
                          backgroundColor: branding.colors.secondary_color,
                          fontFamily: branding.typography.font_family
                        }}
                      >
                        Secondary Action
                      </button>
                      <button
                        className="px-6 py-3 rounded-md font-medium text-white transition-colors"
                        style={{ 
                          backgroundColor: branding.colors.accent_color,
                          fontFamily: branding.typography.font_family
                        }}
                      >
                        Accent Action
                      </button>
                    </div>

                    {/* Card Preview */}
                    <div className="mt-6 p-6 rounded-lg border-2" style={{ borderColor: branding.colors.primary_color }}>
                      <h3 className="text-xl font-semibold mb-2" style={{ 
                        fontFamily: branding.typography.heading_font,
                        color: branding.colors.primary_color 
                      }}>
                        Sample Card
                      </h3>
                      <p className="text-sm" style={{ fontFamily: branding.typography.font_family }}>
                        This is how your content will look with the selected branding.
                      </p>
                    </div>

                    {/* Contact Info Preview */}
                    {(branding.company_info.support_email || branding.company_info.support_phone) && (
                      <div className="mt-6 pt-6 border-t" style={{ borderColor: branding.colors.primary_color }}>
                        <h4 className="font-medium mb-2" style={{ color: branding.colors.primary_color }}>
                          Contact Information
                        </h4>
                        <div className="space-y-1 text-sm">
                          {branding.company_info.support_email && (
                            <p>Email: {branding.company_info.support_email}</p>
                          )}
                          {branding.company_info.support_phone && (
                            <p>Phone: {branding.company_info.support_phone}</p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Social Links Preview */}
                    {(branding.social_links.twitter_url || branding.social_links.linkedin_url || 
                      branding.social_links.github_url || branding.social_links.discord_url) && (
                      <div className="mt-4 flex gap-4">
                        {branding.social_links.twitter_url && (
                          <a 
                            href={branding.social_links.twitter_url} 
                            className="text-sm hover:underline"
                            style={{ color: branding.colors.accent_color }}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Twitter
                          </a>
                        )}
                        {branding.social_links.linkedin_url && (
                          <a 
                            href={branding.social_links.linkedin_url} 
                            className="text-sm hover:underline"
                            style={{ color: branding.colors.accent_color }}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            LinkedIn
                          </a>
                        )}
                        {branding.social_links.github_url && (
                          <a 
                            href={branding.social_links.github_url} 
                            className="text-sm hover:underline"
                            style={{ color: branding.colors.accent_color }}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            GitHub
                          </a>
                        )}
                        {branding.social_links.discord_url && (
                          <a 
                            href={branding.social_links.discord_url} 
                            className="text-sm hover:underline"
                            style={{ color: branding.colors.accent_color }}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            Discord
                          </a>
                        )}
                      </div>
                    )}

                    {/* Email Preview */}
                    {branding.email_branding.email_from_name && (
                      <div className="mt-6 p-4 bg-gray-50 rounded border">
                        <h4 className="font-medium mb-2 text-gray-900">Email Preview</h4>
                        <div className="bg-white p-4 rounded border text-sm">
                          <p className="font-medium" style={{ color: branding.colors.primary_color }}>
                            From: {branding.email_branding.email_from_name} 
                            {branding.email_branding.email_from_address && 
                              ` <${branding.email_branding.email_from_address}>`
                            }
                          </p>
                          <div className="mt-3 pt-3 border-t text-xs text-gray-500">
                            {branding.email_branding.email_footer_text || 'Email footer text will appear here'}
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
                <button
                  type="button"
                  onClick={() => setShowPreviewModal(false)}
                  className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm"
                >
                  Close Preview
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OrganizationBranding;
