import { AnalysisResponse, HealthResponse } from '../types/pipeline';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export async function checkApiHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }
  return response.json();
}

export async function analyzeMultimodal(formData: FormData): Promise<AnalysisResponse> {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = `Analysis failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorDetail);
  }

  return response.json();
}
