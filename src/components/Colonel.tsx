/**
 * The Colonel - AI Assistant Chat Interface
 * 
 * Main chat component for conversing with The Colonel AI agent.
 */

import React, { useState, useEffect, useRef } from 'react';
import { Send, Plus, Archive, Trash2, Settings, MessageSquare, Loader } from 'lucide-react';
import './Colonel.css';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  tool_calls?: any[];
  tool_results?: any[];
  created_at: string;
}

interface Conversation {
  id: string;
  title: string;
  model_provider: string;
  model_name: string;
  created_at: string;
  last_message_at?: string;
}

export function Colonel() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, []);

  // Load messages when conversation changes
  useEffect(() => {
    if (currentConversationId) {
      loadMessages(currentConversationId);
    }
  }, [currentConversationId]);

  // Auto-scroll to bottom when messages update
  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async () => {
    try {
      const response = await fetch('/api/colonel/conversations', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setConversations(data.conversations || []);
      
      // Auto-select first conversation
      if (data.conversations && data.conversations.length > 0 && !currentConversationId) {
        setCurrentConversationId(data.conversations[0].id);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadMessages = async (conversationId: string) => {
    try {
      const response = await fetch(`/api/colonel/conversations/${conversationId}/messages`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const createNewConversation = async () => {
    try {
      const response = await fetch('/api/colonel/conversations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          model_provider: 'anthropic',
          model_name: 'claude-3-5-sonnet-20241022'
        })
      });
      const newConv = await response.json();
      
      setConversations([newConv, ...conversations]);
      setCurrentConversationId(newConv.id);
      setMessages([]);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || !currentConversationId || isStreaming) return;

    const userMessage = inputMessage;
    setInputMessage('');
    setIsStreaming(true);
    setStreamingMessage('');

    // Add user message to UI immediately
    const newUserMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: userMessage,
      created_at: new Date().toISOString()
    };
    setMessages(prev => [...prev, newUserMessage]);

    try {
      // Send message via SSE
      const response = await fetch(`/api/colonel/conversations/${currentConversationId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ message: userMessage })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      let assistantContent = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'text_delta') {
                assistantContent += data.text;
                setStreamingMessage(assistantContent);
              } else if (data.type === 'tool_call_start') {
                assistantContent += `\n\n🔧 Using tool: ${data.tool_name}...\n`;
                setStreamingMessage(assistantContent);
              } else if (data.type === 'tool_result') {
                assistantContent += data.success ? '✅ Success\n' : '❌ Failed\n';
                setStreamingMessage(assistantContent);
              } else if (data.type === 'done') {
                // Reload messages to get full conversation
                await loadMessages(currentConversationId);
                setStreamingMessage('');
                setIsStreaming(false);
              } else if (data.type === 'error') {
                console.error('Stream error:', data.error);
                assistantContent += `\n\n❌ Error: ${data.error}`;
                setStreamingMessage(assistantContent);
                setIsStreaming(false);
              }
            }
          }
        }
      }

      // Reload conversations to update last_message_at
      loadConversations();

    } catch (error) {
      console.error('Failed to send message:', error);
      setIsStreaming(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const deleteConversation = async (conversationId: string) => {
    if (!confirm('Delete this conversation?')) return;

    try {
      await fetch(`/api/colonel/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      setConversations(conversations.filter(c => c.id !== conversationId));
      
      if (currentConversationId === conversationId) {
        setCurrentConversationId(conversations[0]?.id || null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  return (
    <div className="colonel-container">
      {/* Sidebar */}
      <div className={`colonel-sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
          <h2>🎖️ The Colonel</h2>
          <button className="btn-icon" onClick={createNewConversation} title="New Conversation">
            <Plus size={20} />
          </button>
        </div>

        <div className="conversation-list">
          {conversations.map(conv => (
            <div
              key={conv.id}
              className={`conversation-item ${currentConversationId === conv.id ? 'active' : ''}`}
              onClick={() => setCurrentConversationId(conv.id)}
            >
              <div className="conversation-icon">
                <MessageSquare size={18} />
              </div>
              <div className="conversation-info">
                <div className="conversation-title">{conv.title}</div>
                <div className="conversation-meta">
                  {new Date(conv.last_message_at || conv.created_at).toLocaleDateString()}
                </div>
              </div>
              <button
                className="btn-icon btn-delete"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteConversation(conv.id);
                }}
                title="Delete"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <button className="btn-secondary btn-sm">
            <Settings size={16} />
            Settings
          </button>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="colonel-main">
        {currentConversationId ? (
          <>
            {/* Messages */}
            <div className="messages-container">
              {messages.length === 0 && !streamingMessage && (
                <div className="welcome-message">
                  <h1>👋 Hello, I'm The Colonel</h1>
                  <p>Your AI infrastructure assistant. Ask me anything about your devices, alerts, or system status.</p>
                  <div className="example-queries">
                    <h3>Try asking:</h3>
                    <button className="example-query" onClick={() => setInputMessage("Show me all offline devices")}>
                      "Show me all offline devices"
                    </button>
                    <button className="example-query" onClick={() => setInputMessage("What critical alerts do I have?")}>
                      "What critical alerts do I have?"
                    </button>
                    <button className="example-query" onClick={() => setInputMessage("What's our API usage this month?")}>
                      "What's our API usage this month?"
                    </button>
                  </div>
                </div>
              )}

              {messages.map((message) => (
                <div key={message.id} className={`message ${message.role}`}>
                  <div className="message-avatar">
                    {message.role === 'user' ? '👤' : '🎖️'}
                  </div>
                  <div className="message-content">
                    <div className="message-text">
                      {message.content}
                    </div>
                    {message.tool_calls && message.tool_calls.length > 0 && (
                      <div className="tool-calls">
                        <div className="tool-calls-header">🔧 Tools Used:</div>
                        {message.tool_calls.map((tool, idx) => (
                          <div key={idx} className="tool-call">
                            <code>{tool.name}</code>
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="message-time">
                      {new Date(message.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}

              {/* Streaming Message */}
              {streamingMessage && (
                <div className="message assistant streaming">
                  <div className="message-avatar">🎖️</div>
                  <div className="message-content">
                    <div className="message-text">
                      {streamingMessage}
                      <span className="cursor">▊</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="input-container">
              <div className="input-wrapper">
                <textarea
                  className="message-input"
                  placeholder="Ask The Colonel anything..."
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  disabled={isStreaming}
                  rows={1}
                />
                <button
                  className="btn-send"
                  onClick={sendMessage}
                  disabled={!inputMessage.trim() || isStreaming}
                >
                  {isStreaming ? <Loader size={20} className="spinning" /> : <Send size={20} />}
                </button>
              </div>
              <div className="input-hint">
                Press Enter to send, Shift+Enter for new line
              </div>
            </div>
          </>
        ) : (
          <div className="no-conversation">
            <MessageSquare size={64} color="#ccc" />
            <h2>No Conversation Selected</h2>
            <p>Create a new conversation to get started</p>
            <button className="btn-primary" onClick={createNewConversation}>
              <Plus size={20} />
              New Conversation
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Colonel;
