// src/auth/msalConfig.ts
import { PublicClientApplication } from "@azure/msal-browser";

// Auto-select redirect URI (local vs production)
const getRedirectUri = () => {
  const hostname = window.location.hostname;

  // Production static site
  if (hostname === "gentle-mud-0f818720f.1.azurestaticapps.net") {
    return "https://gentle-mud-0f818720f.1.azurestaticapps.net/login";
  }

  // Local dev
  return "http://localhost:5173/login";
};

export const msalConfig = {
  auth: {
    clientId: "c96d832d-9afe-4715-ae65-764283074a3d",
    authority: "https://login.microsoftonline.com/4ac50105-0c66-404e-a107-7cbd8a9a6442/v2.0",
    redirectUri: getRedirectUri(),
    postLogoutRedirectUri: getRedirectUri(),
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);
