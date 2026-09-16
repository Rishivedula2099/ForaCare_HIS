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

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

class ApiClient {
  private instance: AxiosInstance;
  // Single-flight guard: concurrent 401s share one in-flight refresh call
  // instead of each triggering their own (S1-F04).
  private refreshPromise: Promise<void> | null = null;

  constructor() {
    this.instance = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      // Access/refresh tokens live only in HttpOnly cookies set by the
      // backend (S1-F01) - never in JS-readable storage - so every request
      // must carry the browser's cookie jar for the backend to authenticate it.
      withCredentials: true,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request Interceptor: attaches a correlation ID for end-to-end tracing.
    this.instance.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const correlationId = generateCorrelationId();
        config.headers.set("X-Request-Id", correlationId);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response Interceptor: Normalizes error responses to standardized ApiError format
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => response,
      async (error: AxiosError) => {
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

        if (error.response?.status === 401 && typeof window !== "undefined") {
          const originalRequest = error.config as RetryableRequestConfig | undefined;
          const requestUrl = originalRequest?.url || "";
          const isAuthEndpoint =
            requestUrl.includes("/auth/refresh") || requestUrl.includes("/auth/login");
          const canAttemptRefresh =
            !isAuthEndpoint && !!originalRequest && !originalRequest._retry;

          if (canAttemptRefresh) {
            originalRequest._retry = true;
            try {
              await this.refreshSession();
              return this.instance(originalRequest);
            } catch {
              const sessionExpiredError: ApiError = {
                success: false,
                code: "SESSION_EXPIRED",
                message: "Your session has expired. Please sign in again.",
                details: [],
                status_code: 401,
                request_id: requestId,
              };
              this.redirectToLogin();
              return Promise.reject(sessionExpiredError);
            }
          } else if (!isAuthEndpoint) {
            // Refresh already attempted for this request (or nothing to
            // retry) - end the session.
            this.redirectToLogin();
          }
        }

        // Redirect to the shared "access restricted" page on 403 Forbidden
        if (
          error.response?.status === 403 &&
          typeof window !== "undefined" &&
          !window.location.pathname.startsWith("/forbidden")
        ) {
          window.location.href = "/forbidden";
        }

        return Promise.reject(normalizedError);
      }
    );
  }

  // Ensures concurrent 401s share a single in-flight /auth/refresh call
  // (S1-F04): the first caller starts the request, later callers await the
  // same promise instead of triggering their own refresh. The refresh
  // cookie is sent automatically by the browser - there is no token to
  // read or pass here.
  private refreshSession(): Promise<void> {
    if (!this.refreshPromise) {
      this.refreshPromise = axios
        .post<ApiResponse<unknown>>(`${API_BASE_URL}/auth/refresh`, null, {
          withCredentials: true,
        })
        .then(() => undefined)
        .finally(() => {
          this.refreshPromise = null;
        });
    }
    return this.refreshPromise;
  }

  private redirectToLogin(): void {
    if (!window.location.pathname.startsWith("/login")) {
      // Avoid infinite redirect loop if already on login page
      window.location.href = `/login?redirect=${encodeURIComponent(
        window.location.pathname
      )}`;
    }
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
