import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { apiGet, apiPost } from './api';
import {
  companyDetailSchema,
  dataQualitySchema,
  metricSchema,
  pagedCompaniesSchema,
  screenStateSchema,
  sectorCountsSchema,
  type ScreenRequest,
} from './schemas';

export function useMetrics() {
  return useQuery({
    queryKey: ['metrics'],
    queryFn: () => apiGet('/api/v1/metrics', z.array(metricSchema)),
  });
}

export function useScreen(request: ScreenRequest) {
  return useQuery({
    queryKey: ['screen', JSON.stringify(request)],
    queryFn: () => apiPost('/api/v1/screen', pagedCompaniesSchema, request),
  });
}

export function useCompany(ticker: string) {
  return useQuery({
    queryKey: ['company', ticker],
    queryFn: () => apiGet(`/api/v1/companies/${ticker}`, companyDetailSchema),
    enabled: ticker.length > 0,
  });
}

export function usePeers(ticker: string) {
  return useQuery({
    queryKey: ['peers', ticker],
    queryFn: () => apiGet(`/api/v1/companies/${ticker}/peers`, pagedCompaniesSchema),
    enabled: ticker.length > 0,
  });
}

export function useSavedScreen(token: string | null) {
  return useQuery({
    queryKey: ['saved-screen', token],
    queryFn: () => apiGet(`/api/v1/screens/${token}`, screenStateSchema),
    enabled: token !== null,
  });
}

export function useDataQuality() {
  return useQuery({
    queryKey: ['data-quality'],
    queryFn: () => apiGet('/api/v1/data-quality', dataQualitySchema),
  });
}

export function useSectors() {
  return useQuery({
    queryKey: ['sectors'],
    queryFn: () => apiGet('/api/v1/sectors', sectorCountsSchema),
  });
}
