import { Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/layout/AppLayout";
import { DashboardPage } from "@/routes/DashboardPage";
import { FrameworkDetailPage } from "@/routes/FrameworkDetailPage";
import { FrameworksPage } from "@/routes/FrameworksPage";
import { HomePage } from "@/routes/HomePage";
import { SettingsPage } from "@/routes/SettingsPage";

/**
 * ControlBridge web UI root.
 *
 * v0.4.0-alpha.1: Home / Dashboard / Frameworks (list + detail) / Settings.
 * v0.4.0-alpha.2 adds: Onboarding wizard, Gap Analyze, Gap Diff, Risk Generate.
 */
export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<HomePage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="frameworks" element={<FrameworksPage />} />
        <Route path="frameworks/:id" element={<FrameworkDetailPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route
          path="*"
          element={
            <div className="space-y-3">
              <h1 className="text-3xl font-semibold tracking-tight">
                Page not found
              </h1>
              <p className="text-muted-foreground">
                That route isn't implemented yet. Check the sidebar for
                available pages.
              </p>
            </div>
          }
        />
      </Route>
    </Routes>
  );
}
