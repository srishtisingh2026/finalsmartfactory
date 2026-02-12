// src/auth/RequireAuth.tsx
import { useMsal } from "@azure/msal-react";
import { Navigate } from "react-router-dom";

const REQUIRED_ROLE = "SmartFactory.Admin";

export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { accounts, instance } = useMsal();

  // -------------------------------------------------------
  // 1. User NOT logged in → redirect to login page
  // -------------------------------------------------------
  if (!accounts || accounts.length === 0) {
    return <Navigate to="/login" replace />;
  }

  const account = accounts[0];
  const userEmail = account?.username?.toLowerCase();
  const roles = (account?.idTokenClaims as any)?.roles || [];

  // -------------------------------------------------------
  // 2. Check if user has required App Role
  // -------------------------------------------------------
  const hasAccess = roles.includes(REQUIRED_ROLE);

  if (!hasAccess) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#0e1117] text-white">
        <div className="bg-[#161a23] p-10 rounded-2xl border border-gray-800 w-[500px] text-center">
          <div className="mb-6">
            <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
              <svg className="w-10 h-10 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-red-500 mb-2">Access Denied</h1>
            <p className="text-gray-400 mb-2">
              You are not authorized to access this application.
            </p>
            <p className="text-sm text-gray-500 mb-6">
              Logged in as: <span className="text-gray-300">{userEmail}</span>
            </p>
            <p className="text-xs text-gray-600">
              This system is restricted to SmartFactory.Admin users only.
            </p>
          </div>

          <button
            onClick={() => instance.logoutRedirect()}
            className="w-full py-3 rounded-lg font-semibold text-sm bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
          >
            Sign Out
          </button>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------
  // 3. Authorized → Render protected content
  // -------------------------------------------------------
  return children;
}
