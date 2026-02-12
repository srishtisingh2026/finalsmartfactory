import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface Trace {
  trace_id: string;
  session_id: string;
  timestamp: string;
  question: string;         // Backend returns this
  input?: string;          // Optional alias
  latency_ms: number;      // Backend returns this
  latency?: number;        // Optional alias
  tokens: number;
  cost: number;
  scores?: Record<string, number>; // Backend returns this
  [key: string]: any;      // Allow loose indexing for other fields like context, answer
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
  id: string;
  score_name: string;
  template: { id: string;[key: string]: any };
  target: string;
  status: string;
  execution?: { sampling_rate?: number;[key: string]: any };
  created_at: string;
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
  timestamp: string;
  evaluator_name: string;
  trace_id: string;
  score: number;
  duration_ms: number;
  status: string;
}
