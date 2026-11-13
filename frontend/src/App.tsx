import { Link, Route, Routes } from "react-router";
import { HomeProvider } from "./hooks/useHome";
import { AppLayout } from "./layouts/AppLayout";
import { DashboardPage, RoomsPage, DevicesPage } from "./pages/HomePages";
import { AutomationsPage } from "./pages/AutomationsPage";
import { SchedulesPage } from "./pages/SchedulesPage";

export function App() {
  return (
    <HomeProvider>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/rooms" element={<RoomsPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/automations" element={<AutomationsPage />} />
          <Route path="/schedules" element={<SchedulesPage />} />
          <Route
            path="*"
            element={
              <main className="mx-auto max-w-lg p-10">
                <h1 className="mb-4 text-2xl">Страница не найдена</h1>
                <Link className="text-violet-300 underline" to="/">
                  На главную
                </Link>
              </main>
            }
          />
        </Route>
      </Routes>
    </HomeProvider>
  );
}
