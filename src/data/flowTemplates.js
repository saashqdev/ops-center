/**
 * Pre-built Flow Templates
 * Ready-to-use agent workflow templates for common use cases
 */

export const flowTemplates = [
  {
    id: 'research-assistant',
    name: 'Research Assistant',
    description: 'Comprehensive research agent that gathers, analyzes, and summarizes information',
    category: 'Research',
    icon: '🔍',
    flow_config: {
      system_prompt: `You are an expert research assistant. Your role is to:
1. Understand research questions thoroughly
2. Gather information from multiple perspectives
3. Analyze and synthesize findings
4. Present clear, well-structured summaries
5. Cite sources and provide references

Be thorough, objective, and provide balanced viewpoints.`,
      max_tokens: 4096,
      temperature: 0.7,
      tools: [
        {
          name: 'web_search',
          description: 'Search the web for current information',
          input_schema: {
            type: 'object',
            properties: {
              query: { type: 'string', description: 'Search query' }
            },
            required: ['query']
          }
        }
      ]
    }
  },
  {
    id: 'code-generator',
    name: 'Code Generator',
    description: 'Software development assistant for writing, reviewing, and debugging code',
    category: 'Development',
    icon: '💻',
    flow_config: {
      system_prompt: `You are an expert software developer and code generator. Your responsibilities:
1. Write clean, efficient, well-documented code
2. Follow best practices and coding standards
3. Consider edge cases and error handling
4. Provide clear explanations of your code
5. Suggest improvements and optimizations

Always prioritize code quality, readability, and maintainability.`,
      max_tokens: 8192,
      temperature: 0.3,
      tools: [
        {
          name: 'code_analysis',
          description: 'Analyze code for bugs and improvements',
          input_schema: {
            type: 'object',
            properties: {
              code: { type: 'string', description: 'Code to analyze' },
              language: { type: 'string', description: 'Programming language' }
            },
            required: ['code']
          }
        }
      ]
    }
  },
  {
    id: 'content-writer',
    name: 'Content Writer',
    description: 'Creative writing assistant for articles, blog posts, and marketing content',
    category: 'Writing',
    icon: '✍️',
    flow_config: {
      system_prompt: `You are a professional content writer and copywriter. Your goals:
1. Create engaging, original content
2. Match the desired tone and style
3. Optimize for readability and SEO
4. Structure content logically
5. Include compelling headlines and hooks

Write content that resonates with the target audience.`,
      max_tokens: 4096,
      temperature: 0.9,
      tools: []
    }
  },
  {
    id: 'data-analyst',
    name: 'Data Analyst',
    description: 'Analyze data, generate insights, and create visualizations',
    category: 'Analysis',
    icon: '📊',
    flow_config: {
      system_prompt: `You are a skilled data analyst. Your expertise includes:
1. Analyzing datasets and identifying patterns
2. Creating clear visualizations
3. Generating actionable insights
4. Explaining statistical concepts clearly
5. Making data-driven recommendations

Present findings in an accessible way for non-technical audiences.`,
      max_tokens: 4096,
      temperature: 0.5,
      tools: [
        {
          name: 'data_query',
          description: 'Query and analyze data',
          input_schema: {
            type: 'object',
            properties: {
              query: { type: 'string', description: 'Data query or analysis request' }
            },
            required: ['query']
          }
        }
      ]
    }
  },
  {
    id: 'customer-support',
    name: 'Customer Support Agent',
    description: 'Friendly and helpful customer service assistant',
    category: 'Support',
    icon: '🎧',
    flow_config: {
      system_prompt: `You are a friendly and professional customer support agent. Your approach:
1. Greet customers warmly
2. Listen actively to their concerns
3. Provide clear, helpful solutions
4. Show empathy and patience
5. Follow up to ensure satisfaction

Always maintain a positive, solution-oriented attitude.`,
      max_tokens: 2048,
      temperature: 0.8,
      tools: [
        {
          name: 'knowledge_base',
          description: 'Search company knowledge base',
          input_schema: {
            type: 'object',
            properties: {
              query: { type: 'string', description: 'Search query' }
            },
            required: ['query']
          }
        }
      ]
    }
  },
  {
    id: 'tutor',
    name: 'AI Tutor',
    description: 'Educational assistant that explains concepts and helps with learning',
    category: 'Education',
    icon: '🎓',
    flow_config: {
      system_prompt: `You are an encouraging and knowledgeable tutor. Your teaching style:
1. Break down complex topics into simple parts
2. Use examples and analogies
3. Check for understanding
4. Adapt to the student's level
5. Provide practice exercises

Make learning engaging and build confidence.`,
      max_tokens: 4096,
      temperature: 0.7,
      tools: []
    }
  },
  {
    id: 'multi-agent-workflow',
    name: 'Multi-Agent Research Team',
    description: 'Coordinated team of specialized agents working together',
    category: 'Advanced',
    icon: '👥',
    flow_config: {
      system_prompt: 'You are coordinating a team of specialized AI agents to complete complex tasks.',
      max_tokens: 4096,
      temperature: 0.7,
      agents: [
        {
          name: 'Researcher',
          role: 'researcher',
          capabilities: ['web_search', 'data_gathering']
        },
        {
          name: 'Analyst',
          role: 'analyst',
          capabilities: ['data_analysis', 'pattern_recognition']
        },
        {
          name: 'Writer',
          role: 'writer',
          capabilities: ['content_creation', 'summarization']
        }
      ],
      tools: []
    }
  },
  {
    id: 'translator',
    name: 'Language Translator',
    description: 'Accurate translation with cultural context',
    category: 'Language',
    icon: '🌍',
    flow_config: {
      system_prompt: `You are an expert translator fluent in multiple languages. Your approach:
1. Translate accurately while preserving meaning
2. Consider cultural context and idioms
3. Maintain the tone and style of the original
4. Explain nuances when needed
5. Provide alternatives for ambiguous phrases

Ensure translations are natural and culturally appropriate.`,
      max_tokens: 4096,
      temperature: 0.5,
      tools: []
    }
  },
  {
    id: 'brainstorm',
    name: 'Creative Brainstormer',
    description: 'Generate innovative ideas and solutions',
    category: 'Creativity',
    icon: '💡',
    flow_config: {
      system_prompt: `You are a creative brainstorming partner. Your role:
1. Generate diverse, innovative ideas
2. Think outside the box
3. Build on existing concepts
4. Encourage wild ideas
5. Help refine and develop promising directions

Create a judgment-free space for creative exploration.`,
      max_tokens: 3072,
      temperature: 1.2,
      tools: []
    }
  },
  {
    id: 'blank',
    name: 'Blank Template',
    description: 'Start from scratch with a basic configuration',
    category: 'Custom',
    icon: '📄',
    flow_config: {
      system_prompt: 'You are a helpful AI assistant.',
      max_tokens: 4096,
      temperature: 1.0,
      tools: []
    }
  }
];

export const getTemplateById = (id) => {
  return flowTemplates.find(t => t.id === id);
};

export const getTemplatesByCategory = (category) => {
  if (!category) return flowTemplates;
  return flowTemplates.filter(t => t.category === category);
};

export const getAllCategories = () => {
  return [...new Set(flowTemplates.map(t => t.category))].sort();
};
