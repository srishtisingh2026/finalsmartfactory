import axios from "axios";

const API_BASE_URL ="https://smart-factory-backend-code-bfhma8cmf4ghesee.eastus2-01.azurewebsites.net";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface Trace {
  trace_id: string;
  trace_name: string;

  session_id: string;
  user_id?: string;

  input: string;
  output?: string;

  timestamp: string;

  provider?: string;
  model?: string;
  temperature?: number;

  latency_ms?: number;
  status?: string;

  // Usage tokens
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;

  // Cost fields from backend
  input_cost_usd?: number;
  output_cost_usd?: number;
  total_cost_usd?: number;
  currency?: string;

  // Retrieval metadata
  retrieval?: any;

  // Evaluator scores
  scores?: Record<string, number>;

  [key: string]: any;
}

export interface Session {
  session_id: string;

  user_id?: string;
  environment?: string;

  trace_count: number;
  total_tokens: number;

  total_cost_usd: number;
  total_cost_micro_usd: number;

  avg_latency_ms?: number;

  // Raw timestamps from backend
  created?: number | string;
  last_activity?: number | string;

  // ISO formatted timestamps
  session_start?: string;
  session_end?: string;

  // Duration in milliseconds
  session_duration_ms?: number;

  // Only available in GET /sessions/{session_id}
  traces?: any[];

  [key: string]: any;
}

export interface Evaluator {
  id: string;                     // conciseness-v1 (versioned id)

  name?: string;                  // 🔥 NEW (human readable name)
  score_name: string;             // metric key

  description?: string;

  template: {
    id: string;
    provider?: string;
    model?: string;
    prompt_version?: string;
    [key: string]: any;
  };

  target: string;                 // "trace"
  status: "active" | "inactive";

  execution?: {
    sampling_rate?: number;
    timeout_ms?: number;
    retry?: {
      max_attempts?: number;
      backoff_ms?: number;
    };
    [key: string]: any;
  };

  thresholds?: {
    pass?: number;
    warn?: number;
  };

  tags?: string[];

  created_at?: string;
  updated_at?: string;

  [key: string]: any;
}


export interface Template {
  template_id: string;
  name: string;
  description: string;
  template: string;
  model: string;
  inputs: string[];
  version: string;
  updated_at: string;
}

export interface EvaluationLog {
  timestamp?: string;
  evaluator_name?: string;
  trace_id?: string;
  score?: number | null;
  duration_ms?: number;
  status?: string;
}

export interface RCAResult {
  findings: string[];
  evidence: string[];
  suggestions: string[];
}