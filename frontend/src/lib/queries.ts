import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

import { apiGet, apiPost } from './api';
import {
  companyDetailSchema,
  dataQualitySchema,
  metricSchema,
  pagedCompaniesSchema,
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

export function useDataQuality() {
  return useQuery({
    queryKey: ['data-quality'],
    queryFn: () => apiGet('/api/v1/data-quality', dataQualitySchema),
    staleTime: 300_000,
  });
}

export function useSectors() {
  return useQuery({
    queryKey: ['sectors'],
    queryFn: () => apiGet('/api/v1/sectors', sectorCountsSchema),
  });
}
