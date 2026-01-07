import axios from '../http/axiosAgentConfig';
import { normalizeCategory } from '@/constants/resources';
import { BlueprintValidationResult, BlueprintValidationRequest } from '@/types/validation';

export interface WorkflowBlueprint {
  blueprint_id: string;
  spec_dict: any;
  name?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Session {
  session_id: string;
  blueprint_id: string;
  user_id: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ResourceStats {
  category: string;
  count: number;
  types: { [type: string]: number };
}

export interface AgenticStats {
  totalWorkflows: number;
  activeSessions: number;
  totalResources: number;
  categoriesInUse: number;
  blueprintSessionCounts?: Record<string, number>;
  resourcesByCategory: ResourceStats[];
}

// Fetch available blueprints
export async function fetchBlueprints(userId?: string): Promise<WorkflowBlueprint[]> {
  const userIdParam = userId || 'default';
  const response = await axios.get(`/blueprints/available.blueprints.get?userId=${userIdParam}`);
  return response.data || [];
}

// Fetch active sessions
export async function fetchActiveSessions(userId?: string): Promise<string[]> {
  const userIdParam = userId || 'default';
  const response = await axios.get(`/sessions/session.user.blueprints.get?userId=${userIdParam}`);
  return response.data || [];
}

// Fetch session counts by blueprint_id
// Note: This data is available from the aggregated stats endpoint for better performance
export async function fetchBlueprintSessionCounts(userId?: string): Promise<Record<string, number>> {
  const userIdParam = userId || 'default';
  // Use the aggregated stats endpoint instead of a separate endpoint
  const stats = await fetchAgenticStats(userIdParam);
  return stats.blueprintSessionCounts || {};
}

// Fetch all resources for a user
export async function fetchAllResources(userId?: string): Promise<any[]> {
  const userIdParam = userId || 'default';
  const response = await axios.get(`/resources/resources.list?userId=${userIdParam}`);
  return response.data?.resources || [];
}

// Fetch resources by category
export async function fetchResourcesByCategory(category: string, userId?: string): Promise<any[]> {
  const userIdParam = userId || 'default';
  const response = await axios.get(`/resources/resources.list?userId=${userIdParam}&category=${category}`);
  return response.data?.resources || [];
}

// Fetch catalog elements (for inventory stats)
export async function fetchCatalogElements(): Promise<any> {
  const response = await axios.get('/catalog/elements.list.get');
  return response.data?.elements || {};
}

// Fetch resource categories
export async function fetchResourceCategories(): Promise<string[]> {
  const response = await axios.get('/catalog/categories.list.get');
  return response.data?.categories || [];
}

// Fetch agentic stats summary - uses aggregated backend endpoint for optimal performance
export async function fetchAgenticStats(userId?: string): Promise<AgenticStats> {
  const userIdParam = userId || 'default';
  const response = await axios.get(`/statistics/stats.get?userId=${userIdParam}`);
  const data = response.data;
  
  // Normalize categories on frontend (backend returns raw categories)
  // Group by normalized category to merge duplicates (e.g., 'nodes' -> 'agents')
  const categoryMap = new Map<string, { count: number; types: { [type: string]: number } }>();
  
  for (const item of data.resourcesByCategory || []) {
    const normalizedCategory = normalizeCategory(item.category || 'UNKNOWN');
    const existing = categoryMap.get(normalizedCategory);
    
    if (existing) {
      existing.count += item.count || 0;
      for (const [type, count] of Object.entries(item.types || {})) {
        existing.types[type] = (existing.types[type] || 0) + (count as number);
      }
    } else {
      categoryMap.set(normalizedCategory, {
        count: item.count || 0,
        types: { ...(item.types || {}) }
      });
    }
  }
  
  const resourcesByCategory = Array.from(categoryMap.entries()).map(([category, data]) => ({
    category,
    count: data.count,
    types: data.types
  }));

  return {
    totalWorkflows: data.totalWorkflows || 0,
    activeSessions: data.activeSessions || 0,
    totalResources: data.totalResources || 0,
    categoriesInUse: resourcesByCategory.length,
    blueprintSessionCounts: data.blueprintSessionCounts || {},
    resourcesByCategory
  };
}

// Fetch resolved blueprints (for WorkflowsPanel component)
export async function fetchResolvedBlueprints(userId?: string): Promise<WorkflowBlueprint[]> {
  const userIdParam = userId || 'default';
  const response = await axios.get(`/blueprints/available.blueprints.resolved.get?userId=${userIdParam}`);
  return response.data || [];
}

// Validate a saved blueprint and all its elements
export async function validateBlueprint(request: BlueprintValidationRequest): Promise<BlueprintValidationResult> {
  const response = await axios.post('/blueprints/blueprint.validate', {
    blueprintId: request.blueprintId,
    timeoutSeconds: request.timeoutSeconds ?? 10.0,
  });
  return response.data;
}

// ============ Smart Builder API ============

export interface BuilderSession {
  sessionId: string;
  blueprintId: string;
}

export interface BuilderExecuteRequest {
  sessionId: string;
  userPrompt: string;
}

export interface BuilderPhaseInfo {
  name: string;
  status: 'pending' | 'in_progress' | 'complete' | 'error';
  description: string;
}

export interface BuilderExecuteResponse {
  success: boolean;
  output: string;
  error?: string;
  metadata?: {
    phases_completed?: string[];
    blueprint_id?: string;
    workflow_name?: string;
  };
}

// System blueprint name for the Workflow Builder Agent
const BUILDER_BLUEPRINT_NAME = 'Workflow Builder';
const BUILDER_NODE_TYPE = 'builder_node';

// Check if user has a Builder Agent in their inventory
export async function checkBuilderAgentExists(userId: string): Promise<{ exists: boolean; builderAgent?: any; llms?: any[] }> {
  try {
    // Fetch ALL resources and filter - more reliable than category filter
    const allResources = await fetchAllResources(userId);
    console.log('All resources:', allResources);
    
    // Find builder_node - check both type and category
    const builderAgent = allResources?.find((r: any) => {
      const resourceType = r.type?.toLowerCase();
      return resourceType === BUILDER_NODE_TYPE || resourceType === 'builder_node';
    });
    
    console.log('Found builder agent:', builderAgent);
    
    // Find LLMs
    const llmResources = allResources?.filter((r: any) => {
      const category = r.category?.toLowerCase();
      return category === 'llm' || category === 'llms';
    });
    
    console.log('Found LLMs:', llmResources);
    
    return {
      exists: !!builderAgent,
      builderAgent: builderAgent || null,
      llms: llmResources || [],
    };
  } catch (error) {
    console.error('Error checking builder agent:', error);
    return { exists: false, llms: [] };
  }
}

// Build the builder blueprint spec with a specific builder agent reference
function buildBuilderBlueprintSpec(builderAgentRid: string, builderAgentConfig: any) {
  // Get LLM reference from the builder agent config
  const llmRef = builderAgentConfig?.cfg_dict?.llm || 
                 builderAgentConfig?.config?.llm || 
                 builderAgentConfig?.llm;
  
  console.log('Builder agent config:', builderAgentConfig);
  console.log('LLM ref from config:', llmRef);
  
  if (!llmRef) {
    throw new Error('Builder agent does not have an LLM configured. Please edit the Builder Agent in your inventory and assign an LLM.');
  }
  
  return {
    name: BUILDER_BLUEPRINT_NAME,
    description: "An intelligent agent that creates workflows based on your requirements.",
    // All required sections - even if empty
    providers: [],
    llms: [],
    retrievers: [],
    tools: [],
    conditions: [],
    nodes: [
      {
        rid: "user_question_node_rid",
        name: "User Question Node",
        type: "user_question_node",
        config: { type: "user_question_node" }
      },
      {
        rid: "final_answer_node_rid",
        name: "Final Answer Node",
        type: "final_answer_node",
        config: { type: "final_answer_node" }
      },
      // Include the builder agent inline with full config
      {
        rid: "builder_agent_rid",
        name: builderAgentConfig?.name || "Workflow Builder Agent",
        type: "builder_node",
        config: {
          type: "builder_node",
          llm: llmRef,
          system_message: builderAgentConfig?.cfg_dict?.system_message || 
                          builderAgentConfig?.config?.system_message || 
                          "You are the Workflow Builder Agent. Help users create multi-agent workflows.",
          max_rounds: builderAgentConfig?.cfg_dict?.max_rounds || 
                      builderAgentConfig?.config?.max_rounds || 
                      25
        }
      }
    ],
    plan: [
      { uid: "user_input", node: "user_question_node_rid" },
      { uid: "builder", after: "user_input", node: "builder_agent_rid" },
      { uid: "finalize", after: "builder", node: "final_answer_node_rid" }
    ]
  };
}

// Create a session for the Smart Builder agent
export async function createBuilderSession(userId: string, builderAgent: any): Promise<BuilderSession> {
  const builderAgentRid = builderAgent?.rid;
  
  // Check if builder blueprint already exists
  const existingBlueprints = await fetchBlueprints(userId);
  let existingBuilder = existingBlueprints.find(bp => bp.name === BUILDER_BLUEPRINT_NAME);
  
  if (existingBuilder) {
    console.log('Found existing builder blueprint:', existingBuilder.blueprint_id);
    
    // Create session with existing blueprint
    try {
      const response = await axios.post('/sessions/user.session.create', {
        blueprintId: existingBuilder.blueprint_id,
        userId: userId,
      });
      
      console.log('Session created with existing blueprint:', response.data);
      
      return {
        sessionId: response.data,
        blueprintId: existingBuilder.blueprint_id,
      };
    } catch (sessionError: any) {
      console.error('Session creation failed for existing blueprint:', sessionError.response?.data);
      throw new Error(`Session creation failed: ${sessionError.response?.data?.error || sessionError.message}`);
    }
  }
  
  // Blueprint doesn't exist - create it using the builder agent from inventory
  console.log('Creating builder blueprint with agent:', builderAgentRid, builderAgent);
  
  const blueprintSpec = buildBuilderBlueprintSpec(builderAgentRid, builderAgent);
  console.log('Blueprint spec:', JSON.stringify(blueprintSpec, null, 2));
  
  // Send as YAML string in the expected format
  const yamlContent = JSON.stringify(blueprintSpec);
  let saveResponse;
  try {
    saveResponse = await axios.post('/blueprints/blueprint.save', 
      { blueprintRaw: yamlContent, userId: userId },
      { headers: { 'Content-Type': 'application/json' } }
    );
  } catch (saveError: any) {
    console.error('Blueprint save error:', saveError.response?.data);
    throw new Error(`Failed to save blueprint: ${saveError.response?.data?.error || saveError.message}`);
  }
  
  const blueprintId = saveResponse.data?.blueprint_id;
  console.log('Builder blueprint saved with ID:', blueprintId);
  
  if (!blueprintId) {
    throw new Error('Blueprint saved but no ID returned');
  }
  
  // Now create the session
  let sessionResponse;
  try {
    sessionResponse = await axios.post('/sessions/user.session.create', {
      blueprintId: blueprintId,
      userId: userId,
    });
  } catch (sessionError: any) {
    console.error('Session creation error:', sessionError.response?.data);
    throw new Error(`Blueprint saved (ID: ${blueprintId}) but session creation failed: ${sessionError.response?.data?.error || sessionError.message}`);
  }
  
  console.log('Session created:', sessionResponse.data);
  
  return {
    sessionId: sessionResponse.data,
    blueprintId: blueprintId,
  };
}

// Execute the Smart Builder with user request
export async function executeBuilderRequest(
  sessionId: string,
  userPrompt: string
): Promise<BuilderExecuteResponse> {
  const response = await axios.post('/sessions/user.session.execute', {
    sessionId: sessionId,
    inputs: { user_prompt: userPrompt },
  });
  
  console.log('Builder execution raw response:', response.data);
  
  // The response might be a string (final answer) or an object
  const data = response.data;
  
  // If it's a string, wrap it as success
  if (typeof data === 'string') {
    return {
      success: true,
      output: data,
      metadata: {}
    };
  }
  
  // If it has 'response' field (from FinalAnswerNode), extract it
  if (data?.response) {
    return {
      success: true,
      output: data.response,
      metadata: data.metadata || {}
    };
  }
  
  // If it has 'output' field already
  if (data?.output !== undefined) {
    return {
      success: data.success !== false, // default to true unless explicitly false
      output: data.output || '',
      error: data.error,
      metadata: data.metadata || {}
    };
  }
  
  // Fallback - treat the whole response as success
  return {
    success: true,
    output: JSON.stringify(data),
    metadata: {}
  };
}

// Get builder session state
export async function getBuilderSessionState(sessionId: string): Promise<any> {
  const response = await axios.get(`/sessions/session.state.get?sessionId=${sessionId}`);
  return response.data;
}

