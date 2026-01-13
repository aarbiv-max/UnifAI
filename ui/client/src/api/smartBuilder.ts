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
    agents_created?: number;
    agents_reused?: number;
    uses_orchestrator?: boolean;
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
    return { success: true, output: data, metadata: {} };
  }
  
  // If it has 'response' field (from FinalAnswerNode), extract it
  if (data?.response) {
    return {
      success: true,
      output: data.response,
      metadata: data.metadata || {},
    };
  }
  
  // If it has 'output' field already
  if (data?.output !== undefined) {
    return {
      success: data.success !== false,
      output: data.output || '',
      error: data.error,
      metadata: data.metadata || {},
    };
  }
  
  // Fallback
  return {
    success: true,
    output: JSON.stringify(data),
    metadata: {},
  };
}

/**
 * Builder phase event from streaming
 */
export interface BuilderPhaseEvent {
  type: 'builder_phase';
  phase: 'analyze' | 'search' | 'design' | 'validate';
  status: 'started' | 'complete' | 'failed';
  message: string;
}

/**
 * Builder stream event - all event types from streaming
 */
export interface BuilderStreamEvent {
  type: string;
  phase?: string;
  status?: string;
  message?: string;
  chunk?: string;
  tool?: string;
  output?: any;
  data?: any;
}

/**
 * Execute the Smart Builder with streaming for real-time progress
 */
export async function executeBuilderRequestStreaming(
  sessionId: string,
  userPrompt: string,
  onPhaseEvent: (event: BuilderPhaseEvent) => void,
  onComplete: (response: BuilderExecuteResponse) => void,
  onError: (error: string) => void,
  onStreamEvent?: (event: BuilderStreamEvent) => void
): Promise<void> {
  try {
    const response = await fetch('/api2/sessions/user.session.execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId: sessionId,
        inputs: { user_prompt: userPrompt },
        stream: true,
        streamMode: ['custom'],
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalOutput = '';
    let success = true;

    while (true) {
      const { value, done } = await reader.read();
      
      if (value) {
        const decoded = decoder.decode(value, { stream: true });
        buffer += decoded;
        
        // Try to parse complete JSON objects from buffer
        // Each chunk from LangGraph is a complete JSON array
        let startIdx = 0;
        while (startIdx < buffer.length) {
          // Find the start of a JSON array
          const jsonStart = buffer.indexOf('[', startIdx);
          if (jsonStart === -1) break;
          
          // Try to find matching end bracket
          let depth = 0;
          let jsonEnd = -1;
          let inString = false;
          let escape = false;
          
          for (let i = jsonStart; i < buffer.length; i++) {
            const char = buffer[i];
            
            if (escape) {
              escape = false;
              continue;
            }
            
            if (char === '\\' && inString) {
              escape = true;
              continue;
            }
            
            if (char === '"') {
              inString = !inString;
              continue;
            }
            
            if (inString) continue;
            
            if (char === '[') depth++;
            if (char === ']') {
              depth--;
              if (depth === 0) {
                jsonEnd = i;
                break;
              }
            }
          }
          
          if (jsonEnd === -1) break; // Incomplete JSON, wait for more data
          
          const jsonStr = buffer.substring(jsonStart, jsonEnd + 1);
          startIdx = jsonEnd + 1;
          
          try {
            const parsed = JSON.parse(jsonStr);
            
            // LangGraph streams data as tuples: ["custom", {actual_data}]
            const chunk = Array.isArray(parsed) && parsed.length === 2 ? parsed[1] : parsed;
            
            // Forward all stream events to optional handler
            if (onStreamEvent) {
              onStreamEvent(chunk as BuilderStreamEvent);
            }
            
            // Check for builder_phase events
            if (chunk.type === 'builder_phase') {
              onPhaseEvent(chunk as BuilderPhaseEvent);
            }
            
            // Capture final output from agent_finish or complete events
            if (chunk.type === 'agent_finish' && chunk.data?.output) {
              finalOutput = chunk.data.output;
            } else if (chunk.type === 'complete' && chunk.state?.response) {
              finalOutput = chunk.state.response;
            }
          } catch {
            // Ignore JSON parse errors
          }
        }
        
        // Keep unprocessed part in buffer
        buffer = buffer.substring(startIdx);
      }

      if (done) break;
    }

    // Process any remaining buffer (shouldn't be needed with new parsing, but just in case)
    if (buffer.trim()) {
      try {
        const parsed = JSON.parse(buffer);
        const chunk = Array.isArray(parsed) && parsed.length === 2 ? parsed[1] : parsed;
        if (chunk.type === 'builder_phase') {
          onPhaseEvent(chunk as BuilderPhaseEvent);
        }
        if (chunk.type === 'agent_finish' && chunk.data?.output) {
          finalOutput = chunk.data.output;
        } else if (chunk.type === 'complete' && chunk.state?.response) {
          finalOutput = chunk.state.response;
        }
      } catch {
        // Ignore
      }
    }

    onComplete({
      success,
      output: finalOutput,
      metadata: {},
    });
  } catch (error: any) {
    onError(error.message || 'Streaming failed');
  }
}

/**
 * Get builder session state
 */
export async function getBuilderSessionState(sessionId: string): Promise<any> {
  const response = await axios.get(`/sessions/session.state.get?sessionId=${sessionId}`);
  return response.data;
}
