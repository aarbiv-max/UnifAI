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
 * Check if the current element is a Google MCP server based on element type and endpoint URL
 */
export const isGoogleMcpServer = (
  elementType: string,
  sseEndpoint: string | undefined
): boolean => {
  if (elementType !== "mcp_server") return false;
  if (!sseEndpoint) return false;
  return isGoogleMcpUrl(sseEndpoint);
};

