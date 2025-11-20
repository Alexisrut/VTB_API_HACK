import { TooltipProvider } from "./ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "./ui/sonner";
import Home from "./pages/home";
import Profile from "./pages/Profile";
import Health from "./pages/Health";
import Receivables from "./pages/Receivables";
import Payments from "./pages/Payments";
import Settings from "./pages/Settings";
import OAuthSuccess from "./pages/Auth/OAuthSuccess";
import NotFound from "./pages/NotFound";
import { AppContextProvider } from "./hooks/context";
import { BankDataProvider } from "./hooks/BankDataContext";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AppContextProvider>
      <BankDataProvider>
        <TooltipProvider>
          <Toaster 
            position="top-center"
            richColors
            closeButton={false}
            duration={1500}
            toastOptions={{
              style: {
                minWidth: '400px',
                fontSize: '16px',
                padding: '16px 20px',
              },
              className: 'custom-toast',
            }}
            />
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/cash-flow" element={<Navigate to="/health" replace />} />
              <Route path="/health" element={<Health />} />
              <Route path="/receivables" element={<Receivables />} />
              <Route path="/payments" element={<Payments />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/auth/success" element={<OAuthSuccess />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </BankDataProvider>
    </AppContextProvider>
  </QueryClientProvider>
);

export default App;