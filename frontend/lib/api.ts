/**
 * API client for backend communication
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    user_id: string;
    username: string;
    role: string;
    permissions: {
      can_search_local: boolean;
      can_search_internet: boolean;
      can_access_classified: boolean;
      can_upload_documents: boolean;
    };
  };
}

export interface UserResponse {
  user_id: string;
  username: string;
  role: string;
  permissions: {
    can_search_local: boolean;
    can_search_internet: boolean;
    can_access_classified: boolean;
    can_upload_documents: boolean;
  };
}

export interface QueryRequest {
  query: string;
  mode: 'auto' | 'local' | 'internet' | 'hybrid';
  top_k?: number;
  include_images?: boolean;
}

export interface Source {
  doc_name: string;
  doc_id: string;
  chunk_text: string;
  page?: number;
  score: number;
  image_url?: string;
}

export interface ContextQuality {
  overall_score: number;
  vector_score: number;
  coverage: number;
  llm_confidence: number;
  is_sufficient: boolean;
  reason: string;
}

export interface PerformanceBreakdown {
  total_ms: number;
  cache_check_ms?: number;
  embedding_ms?: number;
  qdrant_search_ms?: number;
  context_eval_ms?: number;
  internet_search_ms?: number;
  llm_generation_ms?: number;
  cache_store_ms?: number;
}

export interface QueryResponse {
  query_id: string;
  query: string;
  answer: string;
  sources: Source[];
  mode: string;
  timestamp: string;
  // Agent metadata
  cached?: boolean;
  cache_score?: number;
  context_quality?: ContextQuality;
  agent_decision?: string;
  decision_log?: string[];
  processing_time_ms?: number;
  performance_breakdown?: PerformanceBreakdown;
}

export interface DocumentUploadResponse {
  doc_id: string;
  filename: string;
  status: string;
  message: string;
}

class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor() {
    this.baseUrl = API_URL;
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('access_token');
    }
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
    }
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth endpoints
  async login(data: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(response.access_token);
    return response;
  }

  async getCurrentUser(): Promise<UserResponse> {
    return this.request<UserResponse>('/auth/me');
  }

  logout() {
    this.clearToken();
  }

  // Query endpoints
  async query(data: QueryRequest): Promise<QueryResponse> {
    return this.request<QueryResponse>('/query/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Document endpoints
  async uploadDocument(file: File, tags: string): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('tags', tags);

    const headers: HeadersInit = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}/kb/documents/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async getDocumentStatus(docId: string) {
    return this.request(`/kb/documents/${docId}/status`);
  }

  async listDocuments() {
    return this.request('/kb/documents');
  }

  async deleteDocument(docId: string) {
    return this.request(`/kb/documents/${docId}`, {
      method: 'DELETE',
    });
  }

  // Health check
  async healthCheck() {
    return this.request('/health');
  }
}

export const apiClient = new ApiClient();


