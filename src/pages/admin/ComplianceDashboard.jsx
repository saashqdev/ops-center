/**
 * SOC2 Compliance Dashboard - Epic 18
 * 
 * Comprehensive compliance management interface:
 * - Compliance overview and readiness score
 * - Control management and automated checks
 * - Evidence collection
 * - Security incident tracking
 * - Report generation
 */

import React, { useState, useEffect } from 'react';
import { 
  CheckCircle, XCircle, AlertTriangle, Clock, Shield, 
  FileText, Activity, TrendingUp, Download, PlayCircle,
  Eye, Plus, Filter, RefreshCw 
} from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = '/api/v1/compliance';

const ComplianceDashboard = () => {
  // State
  const [overview, setOverview] = useState(null);
  const [controls, setControls] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedControl, setSelectedControl] = useState(null);
  const [runningChecks, setRunningChecks] = useState(false);

  // Fetch overview data
  const fetchOverview = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/dashboard/overview`);
      setOverview(response.data);
    } catch (error) {
      console.error('Error fetching overview:', error);
    }
  };

  // Fetch controls
  const fetchControls = async (category = null) => {
    try {
      const params = category ? { category } : {};
      const response = await axios.get(`${API_BASE_URL}/controls`, { params });
      setControls(response.data);
    } catch (error) {
      console.error('Error fetching controls:', error);
    }
  };

  // Fetch incidents
  const fetchIncidents = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/dashboard/recent-incidents`);
      setIncidents(response.data);
    } catch (error) {
      console.error('Error fetching incidents:', error);
    }
  };

  // Fetch evidence
  const fetchEvidence = async (controlId = null) => {
    try {
      const params = controlId ? { control_id: controlId } : {};
      const response = await axios.get(`${API_BASE_URL}/evidence`, { params });
      setEvidence(response.data);
    } catch (error) {
      console.error('Error fetching evidence:', error);
    }
  };

  // Run all automated checks
  const runAllChecks = async () => {
    setRunningChecks(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/controls/check-all`);
      alert(`Checks complete: ${response.data.passed} passed, ${response.data.failed} failed, ${response.data.warnings} warnings`);
      await fetchControls();
      await fetchOverview();
    } catch (error) {
      console.error('Error running checks:', error);
      alert('Error running compliance checks');
    } finally {
      setRunningChecks(false);
    }
  };

  // Run single check
  const runCheck = async (controlId) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/controls/${controlId}/check`);
      alert(`${controlId}: ${response.data.status.toUpperCase()} - ${response.data.message}`);
      await fetchControls();
    } catch (error) {
      console.error('Error running check:', error);
      alert('Error running check');
    }
  };

  // Initial load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchOverview(),
        fetchControls(),
        fetchIncidents(),
        fetchEvidence()
      ]);
      setLoading(false);
    };
    loadData();
  }, []);

  // Refresh when category filter changes
  useEffect(() => {
    if (activeTab === 'controls') {
      fetchControls(selectedCategory);
    }
  }, [selectedCategory, activeTab]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Helper functions
  const getStatusIcon = (status) => {
    switch (status) {
      case 'passed':
      case 'implemented':
      case 'verified':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
      case 'not_implemented':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'warning':
      case 'in_progress':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getSeverityBadge = (severity) => {
    const colors = {
      low: 'bg-blue-100 text-blue-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-orange-100 text-orange-800',
      critical: 'bg-red-100 text-red-800'
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[severity] || colors.low}`}>
        {severity?.toUpperCase()}
      </span>
    );
  };

  const getCategoryColor = (category) => {
    const colors = {
      'Security': 'bg-red-100 text-red-800',
      'Availability': 'bg-green-100 text-green-800',
      'Processing Integrity': 'bg-blue-100 text-blue-800',
      'Confidentiality': 'bg-purple-100 text-purple-800',
      'Privacy': 'bg-pink-100 text-pink-800'
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            <Shield className="w-8 h-8" />
            SOC2 Compliance
          </h1>
          <p className="text-gray-600 mt-1">Monitor and manage compliance controls, evidence, and security incidents</p>
        </div>
        <button
          onClick={runAllChecks}
          disabled={runningChecks}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {runningChecks ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Running Checks...
            </>
          ) : (
            <>
              <PlayCircle className="w-4 h-4" />
              Run All Checks
            </>
          )}
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex gap-4">
          {['overview', 'controls', 'incidents', 'evidence'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`py-2 px-4 border-b-2 font-medium text-sm ${
                activeTab === tab
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && overview && (
        <div className="space-y-6">
          {/* Readiness Score */}
          <div className="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-6 text-white">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold mb-2">Overall Compliance Readiness</h2>
                <p className="text-blue-100">
                  {overview.readiness.total_controls} controls | {overview.readiness.implemented_controls} implemented
                </p>
              </div>
              <div className="text-center">
                <div className="text-5xl font-bold">
                  {overview.readiness.readiness_percentage?.toFixed(1) || '0'}%
                </div>
                <div className="text-blue-100 text-sm mt-1">Ready</div>
              </div>
            </div>
          </div>

          {/* Category Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {overview.by_category.map((cat) => (
              <div key={cat.category} className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(cat.category)}`}>
                    {cat.category}
                  </span>
                  <span className="text-2xl font-bold text-gray-900">
                    {((cat.implemented / cat.total) * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="space-y-1 text-sm text-gray-600">
                  <div className="flex justify-between">
                    <span>Total Controls:</span>
                    <span className="font-medium">{cat.total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Implemented:</span>
                    <span className="font-medium text-green-600">{cat.implemented}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>In Progress:</span>
                    <span className="font-medium text-yellow-600">{cat.in_progress}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Not Started:</span>
                    <span className="font-medium text-gray-400">{cat.not_implemented}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Recent Incidents */}
          {incidents.length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-orange-500" />
                Recent Security Incidents
              </h3>
              <div className="space-y-3">
                {incidents.slice(0, 5).map((incident) => (
                  <div key={incident.incident_id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex-1">
                      <div className="font-medium text-gray-900">{incident.title}</div>
                      <div className="text-sm text-gray-600">
                        {new Date(incident.detected_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getSeverityBadge(incident.severity)}
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        incident.status === 'resolved' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {incident.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Controls Tab */}
      {activeTab === 'controls' && (
        <div className="space-y-4">
          {/* Category Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-gray-400" />
            <select
              value={selectedCategory || ''}
              onChange={(e) => setSelectedCategory(e.target.value || null)}
              className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Categories</option>
              <option value="Security">Security</option>
              <option value="Availability">Availability</option>
              <option value="Processing Integrity">Processing Integrity</option>
              <option value="Confidentiality">Confidentiality</option>
              <option value="Privacy">Privacy</option>
            </select>
          </div>

          {/* Controls List */}
          <div className="space-y-3">
            {controls.map((control) => (
              <div key={control.control_id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="font-mono text-sm font-medium text-gray-900">
                        {control.control_id}
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getCategoryColor(control.category)}`}>
                        {control.category}
                      </span>
                      <span className="text-xs text-gray-500">{control.soc2_criteria}</span>
                    </div>
                    <h4 className="font-semibold text-gray-900 mb-1">{control.name}</h4>
                    <p className="text-sm text-gray-600 mb-3">{control.description}</p>
                    
                    {control.last_check_at && (
                      <div className="flex items-center gap-4 text-sm">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(control.last_check_status)}
                          <span className="text-gray-600">
                            Last check: {new Date(control.last_check_at).toLocaleString()}
                          </span>
                        </div>
                        {control.last_check_result?.message && (
                          <span className="text-gray-600">
                            {control.last_check_result.message}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2">
                    {getStatusIcon(control.implementation_status)}
                    {control.automated && (
                      <button
                        onClick={() => runCheck(control.control_id)}
                        className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm flex items-center gap-1"
                      >
                        <PlayCircle className="w-4 h-4" />
                        Check
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Incidents Tab */}
      {activeTab === 'incidents' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Security Incidents</h2>
            <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Report Incident
            </button>
          </div>

          <div className="space-y-3">
            {incidents.map((incident) => (
              <div key={incident.incident_id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h4 className="font-semibold text-gray-900">{incident.title}</h4>
                      {getSeverityBadge(incident.severity)}
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{incident.description}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>Detected: {new Date(incident.detected_at).toLocaleString()}</span>
                      {incident.reported_by && <span>Reporter: {incident.reported_by}</span>}
                      {incident.assigned_to && <span>Assigned: {incident.assigned_to}</span>}
                    </div>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                    incident.status === 'resolved' ? 'bg-green-100 text-green-800' :
                    incident.status === 'investigating' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {incident.status}
                  </span>
                </div>
                {incident.affected_systems?.length > 0 && (
                  <div className="text-sm">
                    <span className="text-gray-600">Affected Systems: </span>
                    <span className="text-gray-900">{incident.affected_systems.join(', ')}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Tab */}
      {activeTab === 'evidence' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Compliance Evidence</h2>
            <button className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2">
              <Plus className="w-4 h-4" />
              Add Evidence
            </button>
          </div>

          <div className="space-y-3">
            {evidence.map((item) => (
              <div key={item.evidence_id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <FileText className="w-5 h-5 text-gray-400" />
                      <h4 className="font-semibold text-gray-900">{item.title}</h4>
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                        {item.evidence_type}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{item.description}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>Control: {item.control_id}</span>
                      <span>Collected: {new Date(item.collected_at).toLocaleString()}</span>
                      {item.collected_by && <span>By: {item.collected_by}</span>}
                      <span className="flex items-center gap-1">
                        {item.verified ? (
                          <>
                            <CheckCircle className="w-3 h-3 text-green-500" />
                            Verified
                          </>
                        ) : (
                          'Not verified'
                        )}
                      </span>
                    </div>
                  </div>
                  <button className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm flex items-center gap-1">
                    <Eye className="w-4 h-4" />
                    View
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ComplianceDashboard;
