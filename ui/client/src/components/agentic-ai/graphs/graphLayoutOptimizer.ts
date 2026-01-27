/**
 * Graph Layout Optimizer
 * 
 * This file re-exports from the modular layout system.
 * The actual implementation is in the ./layout/ directory.
 * 
 * Module Structure:
 * - layout/types.ts       - Type definitions
 * - layout/graphAnalysis.ts - Edge extraction, role classification, SCC detection
 * - layout/constraints.ts  - Hard constraints (entry top, exit bottom)
 * - layout/layering.ts    - Layer assignment, cycle breaking
 * - layout/ordering.ts    - Crossing minimization, barycenter sweeps
 * - layout/positioning.ts - Final X/Y computation, spacing
 * - layout/index.ts       - Orchestration
 */

// Re-export everything from the layout module
export * from "./layout";

// For backwards compatibility, also export commonly used types directly
export type {
  LayoutConfig,
  LayoutResult,
  Position,
  NodeRole,
  GraphStructure,
} from "./layout/types";
