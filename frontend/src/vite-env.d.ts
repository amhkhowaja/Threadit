/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_WRITE_BASE_URL?: string;
  readonly VITE_DEV_USER_ID?: string;
  readonly VITE_COGNITO_REGION: string;
  readonly VITE_COGNITO_USER_POOL_ID: string;
  readonly VITE_COGNITO_CLIENT_ID: string;
  readonly VITE_COGNITO_DOMAIN: string;
  readonly VITE_REDIRECT_URI: string;
  readonly VITE_FEATURE_SEARCH?: string;
  readonly VITE_FEATURE_IMAGES?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
