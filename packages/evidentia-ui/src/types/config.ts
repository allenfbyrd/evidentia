/** TypeScript mirror of evidentia_core.config.EvidentiaConfig. */

export interface LLMConfig {
  model?: string | null;
  temperature?: number | null;
  [key: string]: unknown;
}

export interface EvidentiaConfig {
  organization?: string | null;
  system_name?: string | null;
  frameworks: string[];
  llm: LLMConfig;
  source_path?: string | null;
  [key: string]: unknown;
}
