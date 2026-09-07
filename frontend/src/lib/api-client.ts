import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import { API_BASE_URL } from "@/lib/constants";
import { generateCorrelationId } from "@/lib/utils";
import { ApiError, ApiErrorDetail, ApiResponse } from "@/types/api";

class ApiClient {
  private instance: AxiosInstance;

  constructor() {
    this.instance = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request Interceptor: Injects auth token, tenancy context, and correlation ID
    this.instance.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Set request correlation ID for end-to-end tracing
        const correlationId = generateCorrelationId();
        config.headers.set("X-Request-Id", correlationId);

        // Inject saved auth token if in browser environment
        if (typeof window !== "undefined") {
          const token = localStorage.getItem("foracare_access_token");
          if (token) {
            config.headers.set("Authorization", `Bearer ${token}`);
          }

          // Inject active facility & tenant context headers
          const activeTenantId = localStorage.getItem("foracare_tenant_id");
          const activeFacilityId = localStorage.getItem("foracare_facility_id");

          if (activeTenantId) {
            config.headers.set("X-Tenant-Id", activeTenantId);
          }
          if (activeFacilityId) {
            config.headers.set("X-Facility-Id", activeFacilityId);
          }
        }

        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response Interceptor: Normalizes error responses to standardized ApiError format
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error: AxiosError) => {
        const requestId =
          (error.config?.headers?.["X-Request-Id"] as string) ||
          generateCorrelationId();

        const normalizedError: ApiError = {
          success: false,
          code: "UNKNOWN_ERROR",
          message: "An unexpected error occurred. Please try again.",
          details: [],
          status_code: error.response?.status || 500,
          request_id: requestId,
        };

        const body = error.response?.data as
          | {
              error?: { code?: string; message?: string; details?: ApiErrorDetail[] };
              meta?: { request_id?: string | null };
            }
          | undefined;

        if (body?.error) {
          normalizedError.code = body.error.code || normalizedError.code;
          normalizedError.message = body.error.message || normalizedError.message;
          normalizedError.details = body.error.details || [];
        } else if (error.code === "ECONNABORTED") {
          normalizedError.code = "TIMEOUT";
          normalizedError.message = "Request timed out. Please verify connectivity.";
        } else if (!error.response) {
          normalizedError.code = "NETWORK_ERROR";
          normalizedError.message = "Network error: unable to reach the HIS API server.";
        }

        if (body?.meta?.request_id) {
          normalizedError.request_id = body.meta.request_id;
        }

        // Auto logout on 401 Unauthorized
        if (error.response?.status === 401 && typeof window !== "undefined") {
          localStorage.removeItem("foracare_access_token");
          localStorage.removeItem("foracare_refresh_token");
          if (!window.location.pathname.startsWith("/login")) {
            // Avoid infinite redirect loop if already on login page
            window.location.href = `/login?redirect=${encodeURIComponent(
              window.location.pathname
            )}`;
          }
        }

        return Promise.reject(normalizedError);
      }
    );
  }

  // Type-safe HTTP Methods
  public async get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const res = await this.instance.get<ApiResponse<T>>(url, config);
    return res.data;
  }

  public async post<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const res = await this.instance.post<ApiResponse<T>>(url, data, config);
    return res.data;
  }

  public async put<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const res = await this.instance.put<ApiResponse<T>>(url, data, config);
    return res.data;
  }

  public async patch<T>(
    url: string,
    data?: unknown,
    config?: AxiosRequestConfig
  ): Promise<ApiResponse<T>> {
    const res = await this.instance.patch<ApiResponse<T>>(url, data, config);
    return res.data;
  }

  public async delete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const res = await this.instance.delete<ApiResponse<T>>(url, config);
    return res.data;
  }

  public getAxiosInstance(): AxiosInstance {
    return this.instance;
  }
}

export const apiClient = new ApiClient();
