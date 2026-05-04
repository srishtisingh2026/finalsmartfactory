import { useMsal } from "@azure/msal-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { InteractionStatus } from "@azure/msal-browser";

export default function LoginPage() {
  const { instance, accounts, inProgress } = useMsal();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  // 👇 FIX: If already logged in → send to dashboard
  useEffect(() => {
    const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    if (isLocal || accounts.length > 0) {
      navigate("/dashboard", { replace: true });
    }
  }, [accounts, navigate]);

  const handleLogin = () => {
    if (inProgress === InteractionStatus.None) {
      setError(null);
      instance.loginRedirect().catch((err) => {
        console.error("Login failed:", err);
        setError(err.message || "Login failed. Please check your credentials and try again.");
      });
    }
  };

  const isInteractionInProgress = inProgress !== InteractionStatus.None;

  return (
    <div className="h-screen flex items-center justify-center bg-[#0e1117] text-white">
      <div className="bg-[#161a23] p-10 rounded-2xl border border-gray-800 w-[400px] text-center">

        <h1 className="text-2xl font-bold text-[#4db6ac] mb-4">
          Smart Factory Admin Login
        </h1>

        <p className="text-gray-400 mb-6">
          Sign in with your corporate Microsoft account.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-xs text-left">
            {error}
          </div>
        )}

        <button
          onClick={handleLogin}
          disabled={isInteractionInProgress}
          className={`w-full py-3 rounded-lg font-semibold text-sm transition-colors ${isInteractionInProgress
            ? "bg-gray-700 text-gray-400 cursor-not-allowed"
            : "bg-[#13bba4] text-black hover:bg-[#0fae98]"
            }`}
        >
          {isInteractionInProgress ? "Authenticating..." : "Sign in with Microsoft"}
        </button>
      </div>
    </div>
  );
}
