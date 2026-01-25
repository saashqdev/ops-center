import React, { useState, useEffect, useRef } from 'react';
import { SparklesIcon, PaperAirplaneIcon, ArrowPathIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * Lt. Colonel Atlas - AI Infrastructure Assistant
 * 
 * Chat interface for Atlas, the AI-powered infrastructure orchestration
 * assistant for Ops-Center.
 * 
 * Epic: 6.1
 * Author: AI Agent
 * Date: January 25, 2026
 */
export default function AtlasChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState(null);
  const [availableTools, setAvailableTools] = useState([]);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const API_BASE = '/api/v1/atlas';

  // Load initial data
  useEffect(() => {
    loadAvailableTools();
    loadQuickSystemStatus();
    
    // Add welcome message
    setMessages([{
      role: 'assistant',
      content: `👋 Hello! I'm Lt. Colonel "Atlas", your AI infrastructure assistant for Ops-Center.

I can help you with:
• 🔍 System health monitoring
• 👥 User management
• 💰 Billing and usage tracking
• 🔧 Service operations
• 📊 Log analysis

What would you like to do today?`,
      timestamp: new Date().toISOString()
    }]);
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadAvailableTools = async () => {
    try {
      const response = await fetch(`${API_BASE}/tools`, {
        credentials: 'include'
      });
      const data = await response.json();
      if (data.success) {
        setAvailableTools(data.tools);
      }
    } catch (error) {
      console.error('Failed to load tools:', error);
    }
  };

  const loadQuickSystemStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/status`, {
        credentials: 'include'
      });
      const data = await response.json();
      setSystemStatus(data);
    } catch (error) {
      console.error('Failed to load system status:', error);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    // Add user message
    const newMessages = [
      ...messages,
      {
        role: 'user',
        content: userMessage,
        timestamp: new Date().toISOString()
      }
    ];
    setMessages(newMessages);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({
          message: userMessage,
          conversation_history: messages,
          context: {
            system_status: systemStatus
          }
        })
      });

      const data = await response.json();

      if (data.success) {
        // Add assistant response
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: data.message,
            tool_calls: data.tool_calls,
            tool_results: data.tool_results,
            timestamp: new Date().toISOString()
          }
        ]);

        // Update system status if it changed
        if (data.tool_results) {
          for (const result of data.tool_results) {
            if (result.tool_name === 'system_status') {
              setSystemStatus(result.result);
            }
          }
        }
      } else {
        // Add error message
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: `I encountered an error: ${data.message}`,
            timestamp: new Date().toISOString(),
            error: true
          }
        ]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: 'I apologize, but I encountered a technical error. Please try again.',
          timestamp: new Date().toISOString(),
          error: true
        }
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearConversation = () => {
    setMessages([{
      role: 'assistant',
      content: 'Conversation cleared. How can I assist you?',
      timestamp: new Date().toISOString()
    }]);
  };

  const quickAction = async (action) => {
    let message = '';
    switch (action) {
      case 'status':
        message = 'Check the system status';
        break;
      case 'billing':
        message = 'Show me the billing usage for this month';
        break;
      case 'logs':
        message = 'Show me recent error logs';
        break;
      case 'services':
        message = 'List all running services';
        break;
      default:
        return;
    }
    setInput(message);
    inputRef.current?.focus();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <div className="bg-slate-800/50 backdrop-blur-lg border-b border-purple-500/20">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl shadow-lg">
                <SparklesIcon className="w-7 h-7 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Lt. Colonel Atlas</h1>
                <p className="text-purple-300 text-sm">AI Infrastructure Assistant</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* System Status Indicator */}
              {systemStatus && (
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
                  systemStatus.overall_status === 'healthy'
                    ? 'bg-green-500/20 text-green-300'
                    : systemStatus.overall_status === 'degraded'
                    ? 'bg-yellow-500/20 text-yellow-300'
                    : 'bg-red-500/20 text-red-300'
                }`}>
                  <div className={`w-2 h-2 rounded-full ${
                    systemStatus.overall_status === 'healthy'
                      ? 'bg-green-400'
                      : systemStatus.overall_status === 'degraded'
                      ? 'bg-yellow-400'
                      : 'bg-red-400'
                  } animate-pulse`}></div>
                  <span className="text-sm font-medium capitalize">{systemStatus.overall_status}</span>
                </div>
              )}

              {/* Clear Button */}
              <button
                onClick={clearConversation}
                className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
              >
                <XMarkIcon className="w-5 h-5" />
                <span className="hidden sm:inline">Clear</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-6">
          {/* Main Chat Area */}
          <div className="flex-1 flex flex-col bg-slate-800/30 backdrop-blur-lg rounded-2xl border border-purple-500/20 overflow-hidden" style={{ height: 'calc(100vh - 180px)' }}>
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              <AnimatePresence>
                {messages.map((message, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-gradient-to-br from-purple-600 to-indigo-600 text-white'
                        : message.error
                        ? 'bg-red-500/10 border border-red-500/20 text-red-300'
                        : 'bg-slate-700/50 text-slate-100'
                    }`}>
                      <div className="whitespace-pre-wrap">{message.content}</div>
                      
                      {/* Tool Results */}
                      {message.tool_results && message.tool_results.length > 0 && (
                        <div className="mt-3 space-y-2">
                          {message.tool_results.map((toolResult, idx) => (
                            <div key={idx} className="bg-slate-800/50 rounded-lg p-3 text-sm">
                              <div className="text-purple-400 font-semibold mb-2">
                                🔧 {toolResult.tool_name}
                              </div>
                              <pre className="text-xs text-slate-300 overflow-x-auto">
                                {JSON.stringify(toolResult.result, null, 2)}
                              </pre>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="text-xs opacity-50 mt-2">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {loading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex justify-start"
                >
                  <div className="bg-slate-700/50 rounded-2xl px-4 py-3">
                    <div className="flex items-center gap-2">
                      <ArrowPathIcon className="w-5 h-5 text-purple-400 animate-spin" />
                      <span className="text-slate-300">Atlas is thinking...</span>
                    </div>
                  </div>
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="border-t border-purple-500/20 p-4 bg-slate-800/50">
              {/* Quick Actions */}
              <div className="flex gap-2 mb-3 overflow-x-auto">
                <button
                  onClick={() => quickAction('status')}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm whitespace-nowrap transition-colors"
                >
                  🔍 System Status
                </button>
                <button
                  onClick={() => quickAction('billing')}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm whitespace-nowrap transition-colors"
                >
                  💰 Billing
                </button>
                <button
                  onClick={() => quickAction('logs')}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm whitespace-nowrap transition-colors"
                >
                  📊 Logs
                </button>
                <button
                  onClick={() => quickAction('services')}
                  className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm whitespace-nowrap transition-colors"
                >
                  🔧 Services
                </button>
              </div>

              <div className="flex gap-2">
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask Atlas anything about your infrastructure..."
                  className="flex-1 px-4 py-3 bg-slate-700 border border-slate-600 rounded-xl text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
                  rows="2"
                  disabled={loading}
                />
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || loading}
                  className="px-6 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/20"
                >
                  <PaperAirplaneIcon className="w-5 h-5" />
                </button>
              </div>

              <div className="mt-2 text-xs text-slate-400 text-center">
                Press Enter to send • Shift+Enter for new line
              </div>
            </div>
          </div>

          {/* Sidebar - Available Tools */}
          <div className="hidden lg:block w-80">
            <div className="bg-slate-800/30 backdrop-blur-lg rounded-2xl border border-purple-500/20 p-6">
              <h3 className="text-lg font-bold text-white mb-4">Available Tools</h3>
              <div className="space-y-3">
                {availableTools.map((tool, index) => (
                  <div key={index} className="bg-slate-700/30 rounded-lg p-3">
                    <div className="font-semibold text-purple-300 mb-1">{tool.name}</div>
                    <div className="text-xs text-slate-400">{tool.description}</div>
                  </div>
                ))}
              </div>

              {systemStatus && (
                <div className="mt-6 pt-6 border-t border-slate-700">
                  <h4 className="text-sm font-semibold text-white mb-3">Quick Stats</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between text-slate-300">
                      <span>Services</span>
                      <span className="font-mono">
                        {systemStatus.services?.length || 0}
                      </span>
                    </div>
                    {systemStatus.system_metrics && (
                      <>
                        <div className="flex justify-between text-slate-300">
                          <span>CPU</span>
                          <span className="font-mono">
                            {systemStatus.system_metrics.cpu_percent?.toFixed(1) || '0'}%
                          </span>
                        </div>
                        <div className="flex justify-between text-slate-300">
                          <span>Memory</span>
                          <span className="font-mono">
                            {systemStatus.system_metrics.memory_percent?.toFixed(1) || '0'}%
                          </span>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
