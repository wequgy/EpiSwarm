import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';

import { Home } from './pages/Home';
import { Runs } from './pages/Runs';
import { ResultsOverview } from './pages/ResultsOverview';
import { Regions } from './pages/Regions';
import { Diseases } from './pages/Diseases';
import { Scenarios } from './pages/Scenarios';
import { Behaviors } from './pages/Behaviors';
import { QuickRegionBuilder } from './pages/QuickRegionBuilder';
import { Capacity } from './pages/Capacity';
import { SpatialDiorama } from './pages/SpatialDiorama';
import { Equity } from './pages/Equity';
import { BehaviorAnalysis } from './pages/BehaviorAnalysis';
import { Compare } from './pages/Compare';
import { Optimization } from './pages/Optimization';
import { AdvisorChat } from './pages/AdvisorChat';
import { Validation } from './pages/Validation';
import { Evidence } from './pages/Evidence';
import { Settings } from './pages/Settings';

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
            <Route index element={<Home />} />
            <Route path="runs" element={<Runs />} />
            <Route path="results/:id" element={<ResultsOverview />} />
            <Route path="regions" element={<Regions />} />
            <Route path="diseases" element={<Diseases />} />
            <Route path="scenarios" element={<Scenarios />} />
            <Route path="behaviors" element={<Behaviors />} />
            <Route path="builder" element={<QuickRegionBuilder />} />
            <Route path="capacity" element={<Capacity />} />
            <Route path="spatial" element={<SpatialDiorama />} />
            <Route path="equity" element={<Equity />} />
            <Route path="behavior-analysis" element={<BehaviorAnalysis />} />
            <Route path="compare" element={<Compare />} />
            <Route path="optimization" element={<Optimization />} />
            <Route path="advisor" element={<AdvisorChat />} />
            <Route path="validation" element={<Validation />} />
            <Route path="evidence" element={<Evidence />} />
            <Route path="settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};
