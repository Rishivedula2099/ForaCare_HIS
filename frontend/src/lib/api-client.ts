import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";
import { API_BASE_URL } from "@/lib/constants";
import { generateCorrelationId } from "@/lib/utils";
import { ApiError, ApiResponse } from "@/types/api";

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
        const correlationId =
          (error.config?.headers?.["X-Request-Id"] as string) ||
          generateCorrelationId();

        const normalizedError: ApiError = {
          success: false,
          detail: "An unexpected error occurred. Please try again.",
          status_code: error.response?.status || 500,
          correlation_id: correlationId,
          timestamp: new Date().toISOString(),
        };

        if (error.response?.data) {
          const data = error.response.data as Record<string, unknown>;

          if (typeof data.detail === "string") {
            normalizedError.detail = data.detail;
          } else if (Array.isArray(data.detail)) {
            // Pydantic validation errors array
            normalizedError.detail = "Validation failed on request inputs.";
            normalizedError.errors = data.detail;
          }

          if (typeof data.error_code === "string") {
            normalizedError.error_code = data.error_code;
          }
        } else if (error.code === "ECONNABORTED") {
          normalizedError.detail = "Request timed out. Please verify connectivity.";
        } else if (!error.response) {
          normalizedError.detail = "Network error: unable to reach the HIS API server.";
        }

        // Auto logout on 401 Unauthorized
        if (error.response?.status === 401 && typeof window !== "undefined") {
          localStorage.removeItem("foracare_access_token");
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
