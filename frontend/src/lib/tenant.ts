const TENANT_ID_STORAGE_KEY = "resumeforge_tenant_id";
const API_KEY_STORAGE_KEY = "resumeforge_api_key";

function canUseBrowserStorage(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  try {
    return typeof window.localStorage?.getItem === "function";
  } catch {
    return false;
  }
}

export function getStoredTenantId(): string {
  if (canUseBrowserStorage()) {
    const storedTenantId = window.localStorage.getItem(TENANT_ID_STORAGE_KEY);
    if (storedTenantId) {
      return storedTenantId;
    }
  }
  return process.env.NEXT_PUBLIC_TENANT_ID ?? "00000000-0000-0000-0000-000000000001";
}

export function getStoredApiKey(): string {
  if (canUseBrowserStorage()) {
    return window.localStorage.getItem(API_KEY_STORAGE_KEY) ?? "";
  }
  return process.env.NEXT_PUBLIC_API_KEY ?? "";
}

export function setStoredTenantCredentials(tenantId: string, apiKey: string): void {
  if (!canUseBrowserStorage()) {
    return;
  }
  window.localStorage.setItem(TENANT_ID_STORAGE_KEY, tenantId);
  window.localStorage.setItem(API_KEY_STORAGE_KEY, apiKey);
}

export function buildTenantHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "X-Tenant-ID": getStoredTenantId(),
  };
  const apiKey = getStoredApiKey();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  return headers;
}
