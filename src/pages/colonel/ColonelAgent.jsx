import React, { useState, useEffect, useRef } from 'react';
import { 
  SparklesIcon, 
  PaperAirplaneIcon, 
  ArrowPathIcon, 
  CommandLineIcon,
  ServerIcon,
  UserGroupIcon,
  CreditCardIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';
import { motion, AnimatePresence } from 'framer-motion';
import { useTheme } from '../../contexts/ThemeContext';

/**
 * The Colonel - AI Infrastructure Assistant
 * 
 * Natural language interface for infrastructure queries and orchestration.
 * Provides AI-powered assistance for system operations, user management,
 * billing, and service orchestration.
 * 
 * Epic: 12 - The Colonel Agent
 * Features:
 * - Natural language query processing
 * - Multi-tool orchestration
 * - Real-time streaming responses
 * - Context-aware assistance
 */
export default function ColonelAgent() {
  const { currentTheme } = useTheme();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [availableTools, setAvailableTools] = useState([]);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const API_BASE = '/api/v1/colonel';

  const bgClass = currentTheme === 'unicorn'
    ? 'bg-gradient-to-br from-gray-900 via-purple-900 to-violet-900'
    : currentTheme === 'light'
    ? 'bg-gradient-to-br from-gray-50 to-gray-100'
    : 'bg-gray-900';

  const cardBg = currentTheme === 'unicorn'
    ? 'bg-purple-900/20 border-purple-500/20'
    : currentTheme === 'light'
    ? 'bg-white border-gray-200'
    : 'bg-gray-800 border-gray-700';

  const textClass = currentTheme === 'light' ? 'text-gray-900' : 'text-white';
  const subtextClass = currentTheme === 'light' ? 'text-gray-600' : 'text-gray-400';

  // Load initial data
  useEffect(() => {
    loadAvailableTools();
    
    // Add welcome message
    setMessages([{
      id: Date.now(),
      role: 'assistant',
      content: `👋 Greetings! I'm **The Colonel**, your AI infrastructure assistant.

I can help you with:
• 🔍 **System health** - Monitor services, resources, and performance
• 👥 **User management** - Query users, roles, and permissions  
• 💰 **Billing & usage** - Track costs, credits, and subscriptions
• 🔧 **Service operations** - Control services, view logs, and troubleshoot
• 📊 **Analytics** - Generate insights and reports

What can I help you with today?`,
      timestamp: new Date().toISOString(),
      tools: []
    }]);

    // Focus input
    inputRef.current?.focus();
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
        setAvailableTools(data.tools || []);
      }
    } catch (error) {
      console.error('Failed to load tools:', error);
      setAvailableTools([]);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setLoading(true);

    // Add user message
    const userMsgId = Date.now();
    const newMessages = [
      ...messages,
      {
        id: userMsgId,
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
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          message: userMessage,
          conversation_history: messages.slice(-10) // Last 10 messages for context
        })
      });

      const data = await response.json();

      if (data.success) {
        // Add assistant response
        setMessages(prev => [
          ...prev,
          {
            id: Date.now(),
            role: 'assistant',
            content: data.response,
            timestamp: new Date().toISOString(),
            tools: data.tools_used || [],
            executionTime: data.execution_time
          }
        ]);
      } else {
        throw new Error(data.error || 'Failed to get response');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [
        ...prev,
        {
          id: Date.now(),
          role: 'assistant',
          content: `❌ Sorry, I encountered an error: ${error.message}`,
          timestamp: new Date().toISOString(),
          tools: [],
          isError: true
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const quickActions = [
    { label: 'System Status', icon: ServerIcon, query: 'What is the current system health?' },
    { label: 'Active Users', icon: UserGroupIcon, query: 'How many users are currently active?' },
    { label: 'Today\'s Costs', icon: CreditCardIcon, query: 'What are today\'s LLM costs?' },
    { label: 'Recent Errors', icon: CommandLineIcon, query: 'Show me recent error logs' },
  ];

  return (
    <div className={`min-h-screen ${bgClass} p-6`}>
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
              <SparklesIcon className="w-8 h-8 text-white" />
            </div>
            <div>
              <h1 className={`text-3xl font-bold ${textClass}`}>The Colonel</h1>
              <p className={`${subtextClass}`}>AI Infrastructure Assistant</p>
            </div>
          </div>
          
          {/* Available Tools */}
          {availableTools.length > 0 && (
            <div className="flex items-center gap-2 mt-4">
              <span className={`text-sm ${subtextClass}`}>Available Tools:</span>
              <div className="flex gap-2 flex-wrap">
                {availableTools.slice(0, 6).map((tool) => (
                  <span
                    key={tool.name}
                    className="px-2 py-1 text-xs bg-purple-500/20 text-purple-400 rounded-full border border-purple-500/30"
                  >
                    {tool.name}
                  </span>
                ))}
                {availableTools.length > 6 && (
                  <span className={`text-xs ${subtextClass}`}>+{availableTools.length - 6} more</span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Chat Container */}
        <div className={`${cardBg} border rounded-lg shadow-xl flex flex-col h-[calc(100vh-280px)]`}>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg p-4 ${
                      message.role === 'user'
                        ? 'bg-purple-600 text-white'
                        : message.isError
                        ? 'bg-red-900/30 text-red-200 border border-red-500/30'
                        : currentTheme === 'light'
                        ? 'bg-gray-100 text-gray-900'
                        : 'bg-gray-700/50 text-gray-100'
                    }`}
                  >
                    {/* Message Content */}
                    <div className="whitespace-pre-wrap break-words prose prose-invert max-w-none">
                      {message.content}
                    </div>

                    {/* Tool Usage */}
                    {message.tools && message.tools.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-gray-600/30">
                        <div className="text-xs text-gray-400 mb-2">🔧 Tools used:</div>
                        <div className="flex gap-2 flex-wrap">
                          {message.tools.map((tool, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 text-xs bg-blue-500/20 text-blue-300 rounded border border-blue-500/30"
                            >
                              {tool}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Timestamp */}
                    <div className="text-xs opacity-60 mt-2">
                      {new Date(message.timestamp).toLocaleTimeString()}
                      {message.executionTime && ` • ${message.executionTime.toFixed(2)}s`}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Loading Indicator */}
            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex justify-start"
              >
                <div className={`${currentTheme === 'light' ? 'bg-gray-100' : 'bg-gray-700/50'} rounded-lg p-4`}>
                  <div className="flex items-center gap-2">
                    <ArrowPathIcon className="w-4 h-4 animate-spin text-purple-400" />
                    <span className={subtextClass}>The Colonel is thinking...</span>
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Quick Actions */}
          {messages.length === 1 && (
            <div className="px-6 pb-4">
              <div className={`text-sm ${subtextClass} mb-2`}>Quick Actions:</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {quickActions.map((action) => (
                  <button
                    key={action.label}
                    onClick={() => {
                      setInput(action.query);
                      inputRef.current?.focus();
                    }}
                    className="flex items-center gap-2 p-3 rounded-lg border border-purple-500/30 bg-purple-500/10 hover:bg-purple-500/20 transition-colors text-left"
                  >
                    <action.icon className="w-4 h-4 text-purple-400 flex-shrink-0" />
                    <span className="text-sm text-purple-300">{action.label}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input Area */}
          <div className="border-t border-gray-700 p-4">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask The Colonel anything..."
                disabled={loading}
                className={`flex-1 px-4 py-3 rounded-lg border ${
                  currentTheme === 'light'
                    ? 'bg-white border-gray-300 text-gray-900 placeholder-gray-400'
                    : 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
                } focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50`}
              />
              <button
                onClick={sendMessage}
                disabled={loading || !input.trim()}
                className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? (
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                ) : (
                  <PaperAirplaneIcon className="w-5 h-5" />
                )}
                Send
              </button>
            </div>
            <div className={`text-xs ${subtextClass} mt-2`}>
              Press Enter to send • Shift+Enter for new line
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
