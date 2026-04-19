/** TypeScript mirror of controlbridge_core.config.ControlBridgeConfig. */

export interface LLMConfig {
  model?: string | null;
  temperature?: number | null;
  [key: string]: unknown;
}

export interface ControlBridgeConfig {
  organization?: string | null;
  system_name?: string | null;
  frameworks: string[];
  llm: LLMConfig;
  source_path?: string | null;
  [key: string]: unknown;
}
