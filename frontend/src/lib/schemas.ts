import { z } from 'zod';

export const metricDirectionSchema = z.enum(['high', 'low', 'neutral', 'none']);

export const metricSchema = z.object({
  key: z.string(),
  label: z.string(),
  category: z.string(),
  unit: z.string(),
  direction: metricDirectionSchema,
  formula: z.string(),
  description: z.string(),
  is_derived: z.boolean(),
});
export type Metric = z.infer<typeof metricSchema>;

const metricValueSchema = z.union([z.number(), z.string(), z.null()]);

export const companySummarySchema = z.object({
  ticker: z.string(),
  name: z.string(),
  exchange: z.string().nullable(),
  sector: z.string().nullable(),
  industry: z.string().nullable(),
  metrics: z.record(z.string(), metricValueSchema),
  score: z.number().nullable(),
  score_components: z.record(z.string(), z.number()),
  missing_metrics: z.array(z.string()),
});
export type CompanySummary = z.infer<typeof companySummarySchema>;

export const pagedCompaniesSchema = z.object({
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  items: z.array(companySummarySchema),
});
export type PagedCompanies = z.infer<typeof pagedCompaniesSchema>;

const datedMetricSchema = z.object({
  metric_key: z.string(),
  label: z.string(),
  value: metricValueSchema,
  unit: z.string(),
  direction: metricDirectionSchema,
  period: z.string(),
  source: z.string(),
  as_of_date: z.string(),
});

const factPointSchema = z.object({
  metric_key: z.string(),
  period: z.string(),
  value: metricValueSchema,
  as_of_date: z.string(),
  source: z.string(),
});

export const companyDetailSchema = z.object({
  ticker: z.string(),
  name: z.string(),
  cik: z.string().nullable(),
  exchange: z.string().nullable(),
  sector: z.string().nullable(),
  industry: z.string().nullable(),
  country: z.string(),
  currency: z.string(),
  latest_metrics: z.array(datedMetricSchema),
  history: z.array(factPointSchema),
});
export type CompanyDetail = z.infer<typeof companyDetailSchema>;
export type FactPoint = z.infer<typeof factPointSchema>;

export const sectorCountsSchema = z.object({
  sectors: z.array(z.string()),
  industries: z.array(z.string()),
});

export const filterOpSchema = z.enum([
  'eq',
  'neq',
  'gt',
  'gte',
  'lt',
  'lte',
  'between',
  'in',
  'is_null',
]);
export type FilterOp = z.infer<typeof filterOpSchema>;

export const filterConditionSchema = z.object({
  metric: z.string(),
  op: filterOpSchema,
  value: z.union([
    z.number(),
    z.string(),
    z.boolean(),
    z.null(),
    z.array(z.union([z.number(), z.string()])),
  ]),
});
export type FilterCondition = z.infer<typeof filterConditionSchema>;

export const sortSpecSchema = z.object({
  metric: z.string(),
  dir: z.enum(['asc', 'desc']),
});
export type SortSpec = z.infer<typeof sortSpecSchema>;

export const screenRequestSchema = z.object({
  filters: z.array(filterConditionSchema),
  sort: z.array(sortSpecSchema),
  columns: z.array(z.string()),
  ranking: z.object({ weights: z.record(z.string(), z.number()) }).nullable(),
  limit: z.number(),
  offset: z.number(),
});
export type ScreenRequest = z.infer<typeof screenRequestSchema>;
