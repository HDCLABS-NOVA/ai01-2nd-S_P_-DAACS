/**
 * Authentication hook - Simplified for DAACS integration
 * Bypasses auth to allow immediate access to workspace
 */

export function useAuth() {
  // Bypass authentication for local DAACS usage
  return {
    user: { id: 1, username: "local-user" },
    isLoading: false,
    isAuthenticated: true,
  };
}
