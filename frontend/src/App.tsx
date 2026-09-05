import { BrowserRouter, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import OverviewPage from "./pages/OverviewPage";
import UploadPage from "./pages/UploadPage";
import HistoryPage from "./pages/HistoryPage";
import BatchDashboardPage from "./pages/BatchDashboardPage";
import BatchReportPage from "./pages/BatchReportPage";
import RealCorpusPage from "./pages/RealCorpusPage";
import RealReportPage from "./pages/RealReportPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<OverviewPage />} />
          <Route path="upload" element={<UploadPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="batch" element={<BatchDashboardPage />} />
          <Route path="batch/:runId" element={<BatchReportPage />} />
          <Route path="real" element={<RealCorpusPage />} />
          <Route path="real/:runId" element={<RealReportPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
