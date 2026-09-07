/**
 * Standard API Response and Error Types
 */

export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T;
  message?: string;
  correlation_id?: string;
  timestamp: string;
}

export interface ApiErrorDetail {
  loc?: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiError {
  success: false;
  detail: string;
  error_code?: string;
  correlation_id?: string;
  timestamp?: string;
  errors?: ApiErrorDetail[];
  status_code?: number;
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
