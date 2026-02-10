# Claude Agent SDK Implementation Plan
**Date:** February 10, 2026  
**Goal:** Integrate Claude Agent SDK to allow users and organizations to create custom agent workflows

---

## 📋 Executive Summary

Based on the existing Brigade implementation, we'll create a similar architecture for Claude Agent SDK integration that:
- Allows multi-tenant agent flow creation (per user/org)
- Follows the existing Brigade pattern for consistency
- Provides both UI and API interfaces
- Supports BYOK (Bring Your Own Key) for Claude API keys
- Enables custom tool/MCP server integration

---

## 🏗️ Architecture Overview

### Current Brigade Pattern (Reference)
```
Frontend (Brigade.jsx)
    ↓
Backend API (/api/v1/brigade)
    ↓
Brigade Adapter (format conversion)
    ↓
Unicorn Brigade Service (Docker container)
```

### Proposed Claude Agent SDK Pattern
```
Frontend (ClaudeAgents.jsx)
    ↓
Backend API (/api/v1/claude-agents)
    ↓
Claude Agent SDK Manager
    ↓
Claude API (via SDK)
    ↓
MCP Servers & Custom Tools
```

---

## 📦 Component Breakdown

### 1. Database Schema

#### `agent_flows` table
```sql
CREATE TABLE agent_flows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    org_id VARCHAR(255),  -- NULL for personal flows
    name VARCHAR(255) NOT NULL,
    description TEXT,
    flow_config JSONB NOT NULL,  -- Agent configuration
    status VARCHAR(50) DEFAULT 'active',  -- active, paused, archived
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_executed_at TIMESTAMP,
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_org FOREIGN KEY (org_id) REFERENCES organizations(id)
);

CREATE INDEX idx_agent_flows_user ON agent_flows(user_id);
CREATE INDEX idx_agent_flows_org ON agent_flows(org_id);
CREATE INDEX idx_agent_flows_status ON agent_flows(status);
```

#### `agent_flow_executions` table
```sql
CREATE TABLE agent_flow_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    flow_id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'running',  -- running, completed, failed
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    tokens_used JSONB,  -- {input: 0, output: 0}
    execution_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    
    CONSTRAINT fk_flow FOREIGN KEY (flow_id) REFERENCES agent_flows(id) ON DELETE CASCADE
);

CREATE INDEX idx_executions_flow ON agent_flow_executions(flow_id);
CREATE INDEX idx_executions_user ON agent_flow_executions(user_id);
CREATE INDEX idx_executions_status ON agent_flow_executions(status);
```

#### `agent_api_keys` table
```sql
CREATE TABLE agent_api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    org_id VARCHAR(255),
    key_name VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL,  -- 'anthropic', 'openai', etc.
    encrypted_api_key TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    UNIQUE(user_id, key_name)
);
```

---

### 2. Backend Components

#### File: `backend/claude_agent_sdk.py`
```python
"""
Claude Agent SDK Integration
Handles agent flow creation, execution, and management
"""

from anthropic import Anthropic
import json
from typing import Dict, List, Any, Optional
import asyncio

class ClaudeAgentManager:
    """Manages Claude Agent SDK workflows"""
    
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
    
    async def execute_flow(
        self,
        flow_config: Dict[str, Any],
        user_input: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute an agent flow"""
        pass
    
    async def create_agent_chain(
        self,
        agents: List[Dict],
        tools: List[Dict]
    ) -> Any:
        """Create a multi-agent chain"""
        pass
    
    def stream_execution(self, flow_id: str):
        """Stream agent execution results"""
        pass
```

#### File: `backend/routers/claude_agents.py`
```python
"""
Claude Agent API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/claude-agents", tags=["Claude Agents"])

class AgentFlowCreate(BaseModel):
    name: str
    description: Optional[str]
    flow_config: Dict[str, Any]
    org_id: Optional[str] = None

class AgentFlowExecute(BaseModel):
    flow_id: str
    input_data: Dict[str, Any]
    stream: bool = False

@router.post("/flows")
async def create_agent_flow(flow: AgentFlowCreate, user=Depends(get_current_user)):
    """Create a new agent flow"""
    pass

@router.get("/flows")
async def list_agent_flows(
    org_id: Optional[str] = None,
    user=Depends(get_current_user)
):
    """List all agent flows for user/org"""
    pass

@router.get("/flows/{flow_id}")
async def get_agent_flow(flow_id: str, user=Depends(get_current_user)):
    """Get specific agent flow"""
    pass

@router.put("/flows/{flow_id}")
async def update_agent_flow(
    flow_id: str,
    flow: AgentFlowCreate,
    user=Depends(get_current_user)
):
    """Update agent flow"""
    pass

@router.delete("/flows/{flow_id}")
async def delete_agent_flow(flow_id: str, user=Depends(get_current_user)):
    """Delete agent flow"""
    pass

@router.post("/flows/{flow_id}/execute")
async def execute_agent_flow(
    flow_id: str,
    execution: AgentFlowExecute,
    user=Depends(get_current_user)
):
    """Execute an agent flow"""
    pass

@router.get("/flows/{flow_id}/executions")
async def get_flow_executions(
    flow_id: str,
    limit: int = 50,
    user=Depends(get_current_user)
):
    """Get execution history for a flow"""
    pass

@router.get("/api-keys")
async def list_api_keys(user=Depends(get_current_user)):
    """List user's Claude API keys"""
    pass

@router.post("/api-keys")
async def add_api_key(
    key_name: str,
    provider: str,
    api_key: str,
    user=Depends(get_current_user)
):
    """Add a new API key"""
    pass
```

---

### 3. Frontend Components

#### File: `src/pages/ClaudeAgents.jsx`
```jsx
import React, { useState, useEffect } from 'react';
import { useToast } from '../components/Toast';
import {
  Box,
  Card,
  CardContent,
  Button,
  Grid,
  Typography,
  Tabs,
  Tab,
  Dialog
} from '@mui/material';

export default function ClaudeAgents() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState(0);
  const [flows, setFlows] = useState([]);
  const [selectedFlow, setSelectedFlow] = useState(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [executions, setExecutions] = useState([]);

  // Fetch user's agent flows
  const fetchFlows = async () => {
    const response = await fetch('/api/v1/claude-agents/flows');
    const data = await response.json();
    setFlows(data);
  };

  // Create new flow
  const createFlow = async (flowData) => {
    const response = await fetch('/api/v1/claude-agents/flows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(flowData)
    });
    if (response.ok) {
      toast.success('Agent flow created!');
      fetchFlows();
    }
  };

  // Execute flow
  const executeFlow = async (flowId, inputData) => {
    const response = await fetch(`/api/v1/claude-agents/flows/${flowId}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input_data: inputData })
    });
    return await response.json();
  };

  return (
    <Box p={3}>
      <Box mb={3} display="flex" justifyContent="space-between">
        <div>
          <Typography variant="h4">🤖 Claude Agent Workflows</Typography>
          <Typography variant="body2" color="text.secondary">
            Create and manage custom AI agent workflows
          </Typography>
        </div>
        <Button
          variant="contained"
          color="primary"
          onClick={() => setShowCreateDialog(true)}
        >
          Create New Flow
        </Button>
      </Box>

      <Tabs value={activeTab} onChange={(e, v) => setActiveTab(v)}>
        <Tab label="My Flows" />
        <Tab label="Organization Flows" />
        <Tab label="Execution History" />
        <Tab label="API Keys" />
      </Tabs>

      {activeTab === 0 && <MyFlowsTab flows={flows} onExecute={executeFlow} />}
      {activeTab === 1 && <OrgFlowsTab />}
      {activeTab === 2 && <ExecutionHistoryTab executions={executions} />}
      {activeTab === 3 && <APIKeysTab />}

      <CreateFlowDialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        onCreate={createFlow}
      />
    </Box>
  );
}
```

#### File: `src/components/agents/FlowBuilder.jsx`
```jsx
import React, { useState } from 'react';
import { Box, Card, Button, TextField } from '@mui/material';

/**
 * Visual flow builder for creating agent workflows
 * Allows drag-drop of:
 * - Agent nodes (researcher, coder, analyst, etc.)
 * - Tool nodes (web search, database, API calls)
 * - MCP server connections
 * - Decision nodes (branching logic)
 */
export default function FlowBuilder({ onSave }) {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);

  const addNode = (type) => {
    // Add a new node to the flow
  };

  const connectNodes = (sourceId, targetId) => {
    // Create edge between nodes
  };

  const saveFlow = () => {
    const flowConfig = {
      nodes,
      edges,
      version: '1.0'
    };
    onSave(flowConfig);
  };

  return (
    <Box>
      <Card>
        {/* Flow canvas */}
        <Box p={2} minHeight={400}>
          {/* Render nodes and edges */}
        </Box>
      </Card>
      <Button onClick={saveFlow}>Save Flow</Button>
    </Box>
  );
}
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create database schema and migrations
- [ ] Implement basic backend API endpoints
- [ ] Set up Claude Agent SDK manager
- [ ] Create basic frontend page structure
- [ ] Test CRUD operations for flows

### Phase 2: Flow Builder (Week 2)
- [ ] Design flow configuration schema
- [ ] Build visual flow builder UI
- [ ] Implement agent node types
- [ ] Add tool/MCP integration
- [ ] Create flow validation logic

### Phase 3: Execution Engine (Week 3)
- [ ] Implement flow execution logic
- [ ] Add streaming support
- [ ] Create execution monitoring
- [ ] Build error handling
- [ ] Add usage tracking

### Phase 4: Multi-tenancy (Week 4)
- [ ] Add organization-level flows
- [ ] Implement sharing/permissions
- [ ] Create flow templates
- [ ] Add version control
- [ ] Build collaboration features

### Phase 5: Advanced Features (Week 5)
- [ ] Add flow analytics
- [ ] Implement A/B testing
- [ ] Create marketplace for flows
- [ ] Add webhook triggers
- [ ] Build scheduling system

---

## 🔒 Security Considerations

1. **API Key Encryption**: Store Claude API keys encrypted at rest
2. **Access Control**: Enforce user/org permissions on all operations
3. **Rate Limiting**: Prevent abuse of agent executions
4. **Input Validation**: Sanitize all flow configurations
5. **Audit Logging**: Track all flow executions and modifications

---

## 📊 Success Metrics

- Number of flows created per user
- Average execution time
- Success/failure rates
- Token usage per flow
- User engagement (executions per day)
- Cost per execution

---

## 🎯 Quick Start Implementation

### Minimal Viable Product (MVP)
For immediate implementation, start with:

1. **Database Setup**: Run migration for `agent_flows` table
2. **Backend API**: Implement 3 core endpoints:
   - POST `/api/v1/claude-agents/flows` - Create flow
   - GET `/api/v1/claude-agents/flows` - List flows
   - POST `/api/v1/claude-agents/flows/{id}/execute` - Execute flow
3. **Frontend**: Create basic `ClaudeAgents.jsx` with:
   - Flow list view
   - Simple flow creation form (JSON editor)
   - Execution trigger button
4. **Integration**: Wire up to Claude API using SDK

This MVP can be implemented in **2-3 days** and provides immediate value.

---

## 📚 References

- Existing Brigade implementation: `backend/brigade_api.py`
- Brigade adapter pattern: `backend/brigade_adapter.py`
- Frontend pattern: `src/pages/Brigade.jsx`
- Service discovery: `backend/atlas/atlas_tools.py`

---

## Next Steps

1. Review and approve this plan
2. Create database migration files
3. Set up development branch
4. Begin Phase 1 implementation
5. Weekly progress reviews
