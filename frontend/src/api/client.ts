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
  session_id: string;
  user_id?: string;

  trace_name: string;     // ✅ matches backend
  input: string;
  output?: string;

  timestamp: string;

  latency_ms: number;
  tokens: number;
  tokens_in?: number;
  tokens_out?: number;

  cost: number;
  model?: string;

  scores?: Record<string, number>; 

  [key: string]: any;
}

export interface Session {
  session_id: string;
  user: string; // Backend sends "user"
  user_id?: string; // Frontend alias if needed
  trace_count: number;
  total_tokens: number;
  total_cost: number;
  created_at: string;
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
