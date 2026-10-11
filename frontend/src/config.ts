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
}

export const config: AppConfig = {
  apiBaseUrl: required("VITE_API_BASE_URL").replace(/\/$/, ""),
  cognito: {
    region: required("VITE_COGNITO_REGION"),
    userPoolId: required("VITE_COGNITO_USER_POOL_ID"),
    clientId: required("VITE_COGNITO_CLIENT_ID"),
    domain: required("VITE_COGNITO_DOMAIN").replace(/\/$/, ""),
    redirectUri: required("VITE_REDIRECT_URI"),
  },
  features: {
    search: flag("VITE_FEATURE_SEARCH"),
    images: flag("VITE_FEATURE_IMAGES"),
  },
};
