/**
 * Smart Builder API Module
 * 
 * API functions for the Smart Builder workflow creation feature.
 * Separated from agentic.ts for better organization.
 */

import axios from '../http/axiosAgentConfig';
import { fetchBlueprints, fetchAllResources } from './agentic';

// ============ Types ============

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

export interface BuilderAgentCheckResult {
  exists: boolean;
  builderAgent?: any;
  llms?: any[];
}

// ============ Constants ============

const BUILDER_BLUEPRINT_NAME = 'Workflow Builder';
const BUILDER_NODE_TYPE = 'builder_node';

// ============ API Functions ============

/**
 * Check if user has a Builder Agent in their inventory
 */
export async function checkBuilderAgentExists(
  userId: string
): Promise<BuilderAgentCheckResult> {
  try {
    const allResources = await fetchAllResources(userId);
    
    const builderAgent = allResources?.find((r: any) => {
      const resourceType = r.type?.toLowerCase();
      return resourceType === BUILDER_NODE_TYPE || resourceType === 'builder_node';
    });
    
    const llmResources = allResources?.filter((r: any) => {
      const category = r.category?.toLowerCase();
      return category === 'llm' || category === 'llms';
    });
    
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

/**
 * Build the builder blueprint spec with a specific builder agent reference
 */
function buildBuilderBlueprintSpec(builderAgentRid: string, builderAgentConfig: any) {
  const llmRef = builderAgentConfig?.cfg_dict?.llm || 
                 builderAgentConfig?.config?.llm || 
                 builderAgentConfig?.llm;
  
  if (!llmRef) {
    throw new Error(
      'Builder agent does not have an LLM configured. ' +
      'Please edit the Builder Agent in your inventory and assign an LLM.'
    );
  }
  
  return {
    name: BUILDER_BLUEPRINT_NAME,
    description: "An intelligent agent that creates workflows based on your requirements.",
    is_system: true, // Mark as system blueprint - hidden from regular workflow listings
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

/**
 * Create a session for the Smart Builder agent
 */
export async function createBuilderSession(
  userId: string, 
  builderAgent: any
): Promise<BuilderSession> {
  const builderAgentRid = builderAgent?.rid;
  
  // Check if builder blueprint already exists
  const existingBlueprints = await fetchBlueprints(userId);
  const existingBuilder = existingBlueprints.find(
    bp => bp.name === BUILDER_BLUEPRINT_NAME
  );
  
  if (existingBuilder) {
    try {
      const response = await axios.post('/sessions/user.session.create', {
        blueprintId: existingBuilder.blueprint_id,
        userId: userId,
      });
      
      return {
        sessionId: response.data,
        blueprintId: existingBuilder.blueprint_id,
      };
    } catch (sessionError: any) {
      throw new Error(
        `Session creation failed: ${sessionError.response?.data?.error || sessionError.message}`
      );
    }
  }
  
  // Blueprint doesn't exist - create it
  const blueprintSpec = buildBuilderBlueprintSpec(builderAgentRid, builderAgent);
  const yamlContent = JSON.stringify(blueprintSpec);
  
  let saveResponse;
  try {
    saveResponse = await axios.post('/blueprints/blueprint.save', 
      { blueprintRaw: yamlContent, userId: userId },
      { headers: { 'Content-Type': 'application/json' } }
    );
  } catch (saveError: any) {
    throw new Error(
      `Failed to save blueprint: ${saveError.response?.data?.error || saveError.message}`
    );
  }
  
  const blueprintId = saveResponse.data?.blueprint_id;
  
  if (!blueprintId) {
    throw new Error('Blueprint saved but no ID returned');
  }
  
  // Create the session
  let sessionResponse;
  try {
    sessionResponse = await axios.post('/sessions/user.session.create', {
      blueprintId: blueprintId,
      userId: userId,
    });
  } catch (sessionError: any) {
    throw new Error(
      `Blueprint saved (ID: ${blueprintId}) but session creation failed: ` +
      `${sessionError.response?.data?.error || sessionError.message}`
    );
  }
  
  return {
    sessionId: sessionResponse.data,
    blueprintId: blueprintId,
  };
}

/**
 * Execute the Smart Builder with user request
 */
export async function executeBuilderRequest(
  sessionId: string,
  userPrompt: string
): Promise<BuilderExecuteResponse> {
  const response = await axios.post('/sessions/user.session.execute', {
    sessionId: sessionId,
    inputs: { user_prompt: userPrompt },
  });
  
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
      success: data.success !== false,
      output: data.output || '',
      error: data.error,
      metadata: data.metadata || {}
    };
  }
  
  // Fallback
  return {
    success: true,
    output: JSON.stringify(data),
    metadata: {}
  };
}

/**
 * Get builder session state
 */
export async function getBuilderSessionState(sessionId: string): Promise<any> {
  const response = await axios.get(`/sessions/session.state.get?sessionId=${sessionId}`);
  return response.data;
}

