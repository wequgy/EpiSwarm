import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';

import { CaseFile } from './pages/CaseFile';
import { SimulateStage } from './pages/SimulateStage';
import { Insights } from './pages/Insights';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            {/* 3 Core Modes of EpiSwarm Studio v2 */}
            <Route index element={<Navigate to="/case-file" replace />} />
            <Route path="case-file" element={<CaseFile />} />
            <Route path="simulate" element={<SimulateStage />} />
            <Route path="insights" element={<Insights />} />

            {/* Seamless Legacy Parity Aliases */}
            <Route path="runs" element={<Navigate to="/simulate" replace />} />
            <Route path="results/:id" element={<Navigate to="/insights" replace />} />
            <Route path="capacity" element={<Navigate to="/insights?tab=capacity" replace />} />
            <Route path="spatial" element={<Navigate to="/insights?tab=spatial" replace />} />
            <Route path="equity" element={<Navigate to="/insights?tab=equity" replace />} />
            <Route path="compare" element={<Navigate to="/insights?tab=compare" replace />} />
            <Route path="optimization" element={<Navigate to="/insights?tab=pareto" replace />} />
            <Route path="advisor" element={<Navigate to="/insights?tab=advisor" replace />} />
            <Route path="validation" element={<Navigate to="/insights?tab=calibration" replace />} />
            <Route path="evidence" element={<Navigate to="/insights?tab=calibration" replace />} />
            <Route path="regions" element={<Navigate to="/case-file" replace />} />
            <Route path="diseases" element={<Navigate to="/case-file" replace />} />
            <Route path="scenarios" element={<Navigate to="/case-file" replace />} />
            <Route path="behaviors" element={<Navigate to="/case-file" replace />} />
            <Route path="builder" element={<Navigate to="/case-file" replace />} />

            {/* Default Catch-all */}
            <Route path="*" element={<Navigate to="/case-file" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};
