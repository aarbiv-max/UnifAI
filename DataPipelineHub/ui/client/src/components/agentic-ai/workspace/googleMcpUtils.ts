/**
 * Utility functions for Google MCP Server detection and handling
 */

// Mock Google MCP server URL pattern - will be replaced in the future
// Matches URLs like: https://mock-google-mcp.example.com or https://mock-google-mcp.example.com/
export const GOOGLE_MCP_URL_PATTERN = /https?:\/\/(mock-google-mcp|mcp\.google|google-mcp)\.[^\/\s]*/i;

/**
 * Check if a given URL matches the Google MCP server pattern
 */
export const isGoogleMcpUrl = (url: string): boolean => {
  if (!url || typeof url !== "string") return false;
  // Normalize the URL (remove trailing slash and whitespace) for matching
  const normalizedUrl = url.trim().replace(/\/+$/, "");
  return GOOGLE_MCP_URL_PATTERN.test(normalizedUrl);
};

/**
 * Check if the current element is a Google MCP server based on element type and config
 * This checks for:
 * 1. Element type is mcp_server
 * 2. Either has google_oauth in config, or has pod_url in config (indicating Google MCP setup)
 */
export const isGoogleMcpServer = (
  elementType: string,
  sseEndpoint: string | undefined,
  config?: any
): boolean => {
  if (elementType !== "mcp_server") return false;
  
  // Check if config has google_oauth (existing Google MCP servers)
  if (config?.google_oauth) {
    return true;
  }
  
  // Check if config has pod_url (new Google MCP setup via GoogleMcpForm)
  if (config?.pod_url) {
    return true;
  }
  
  // Legacy check: if sseEndpoint matches Google MCP URL pattern
  if (sseEndpoint && isGoogleMcpUrl(sseEndpoint)) {
    return true;
  }
  
  return false;
};

