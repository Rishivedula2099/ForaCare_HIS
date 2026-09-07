/**
 * Standard API Response and Error Types
 *
 * Mirrors the envelope produced by `app/core/responses.py` on the backend:
 * `{success, data, error, meta: {request_id, timestamp}}`.
 */

export interface ResponseMeta {
  request_id: string | null;
  timestamp: string;
}

export interface ApiErrorDetail {
  field?: string | null;
  message: string;
}

export interface ApiErrorModel {
  code: string;
  message: string;
  details: ApiErrorDetail[];
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T | null;
  error: ApiErrorModel | null;
  meta: ResponseMeta;
}

/**
 * Normalized shape thrown by the `apiClient` response interceptor for any
 * failed request (network error, timeout, or a backend error envelope).
 */
export interface ApiError {
  success: false;
  code: string;
  message: string;
  details: ApiErrorDetail[];
  status_code?: number;
  request_id?: string | null;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
