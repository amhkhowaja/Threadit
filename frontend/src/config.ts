// Single runtime-config source. Plug in env values and the app runs.
// Required values fail fast at startup so misconfiguration is obvious.

function required(name: keyof ImportMetaEnv): string {
  const v = import.meta.env[name];
  if (!v) throw new Error(`Missing required config: ${name}`);
  return v;
}

function flag(name: keyof ImportMetaEnv, def = true): boolean {
  const v = import.meta.env[name];
  if (v === undefined) return def;
  return v === "true";
}

export interface AppConfig {
  apiBaseUrl: string;
  writeBaseUrl: string;
  cognito: {
    region: string;
    userPoolId: string;
    clientId: string;
    domain: string;
    redirectUri: string;
  };
  features: {
    search: boolean;
    images: boolean;
  };
  // Local dev only: when set, skip Cognito and send this as x-user-id on writes.
  devUserId?: string;
}

function optional(name: keyof ImportMetaEnv): string | undefined {
  return import.meta.env[name] || undefined;
}

const devUserId = optional("VITE_DEV_USER_ID");

// In dev mode (devUserId set) Cognito values are not required.
function cognitoVal(name: keyof ImportMetaEnv): string {
  return devUserId ? (import.meta.env[name] ?? "") : required(name);
}

export const config: AppConfig = {
  apiBaseUrl: required("VITE_API_BASE_URL").replace(/\/$/, ""),
  // Writes default to the same base; split for local (read :8080 / write :8081).
  writeBaseUrl: (optional("VITE_WRITE_BASE_URL") ?? required("VITE_API_BASE_URL")).replace(/\/$/, ""),
  cognito: {
    region: cognitoVal("VITE_COGNITO_REGION"),
    userPoolId: cognitoVal("VITE_COGNITO_USER_POOL_ID"),
    clientId: cognitoVal("VITE_COGNITO_CLIENT_ID"),
    domain: cognitoVal("VITE_COGNITO_DOMAIN").replace(/\/$/, ""),
    redirectUri: cognitoVal("VITE_REDIRECT_URI"),
  },
  features: {
    search: flag("VITE_FEATURE_SEARCH"),
    images: flag("VITE_FEATURE_IMAGES"),
  },
  devUserId,
};
