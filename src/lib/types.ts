// ---- Transaction ----
export interface Transaction {
  id: number
  fecha: string
  hora: string
  tipo: 'Gasto' | 'Ingreso' | 'Transferencia'
  categoria: string
  subcategoria: string | null
  descripcion: string
  cuenta: string
  monto_bs: number
  monto_usd: number
  tasa: number
  moneda: 'USD' | 'VES'
  import_batch_id: string | null
}

// ---- Exchange Rates ----
export interface ExchangeRate {
  id: number
  fecha: string
  tasa_binance: number | null
  tasa_bcv: number | null
  dif_pct_paralelo: number | null
  dif_pct_oficial: number | null
  log_return_binance: number | null
  log_return_bcv: number | null
}

// ---- Macro ----
export interface MacroIPC {
  id: number
  year: number
  month: number
  indice: number
  var_pct: number | null
}

export interface MacroLiquidity {
  id: number
  year: number
  month: number
  m1: number | null
  m2: number | null
  billetes_monedas: number | null
  depositos_vista: number | null
  depositos_ahorro: number | null
}

export interface MacroGDP {
  id: number
  year: number
  quarter: number
  gdp_value: number | null
  pct_change: number | null
}

export interface MacroOil {
  id: number
  year: number
  revenue_usd_bn: number | null
  status: string | null
}

export interface CestaBasica {
  id: number
  year: number
  month: number
  total_bs: number | null
  total_usd: number | null
  food_bs: number | null
  services_bs: number | null
  source_url: string | null
  fetched_at: string | null
}

// ---- Income ----
export interface IncomeSource {
  id: number
  name: string
  amount: number
  currency: 'USD' | 'VES'
  frequency: 'monthly' | 'biweekly' | 'weekly' | 'annual' | 'one-time'
  start_date: string | null
  indexed_to_inflation: boolean
  active: boolean
}

// ---- Subscriptions ----
export interface Subscription {
  id: number
  name: string
  amount: number
  currency: 'USD' | 'VES'
  frequency: 'monthly' | 'annual' | 'quarterly'
  category: string | null
  account: string | null
  active: boolean
  next_payment_date: string | null
  essential: boolean
  notes: string | null
}

// ---- Saving Goals ----
export interface SavingGoal {
  id: number
  name: string
  target_amount: number
  target_currency: 'USD' | 'VES'
  target_date: string | null
  monthly_contribution: number | null
  priority: number
  active: boolean
}

// ---- Narrative Engine ----
export interface VerdictExplanation {
  type?: string
  verdict: string
  because?: string
  deep_dive?: string
  severity?: 'excellent' | 'good' | 'moderate' | 'concerning' | 'critical' | 'informational'
  color?: 'green' | 'amber' | 'red' | 'neutral'
  raw?: unknown
}

export interface ForecastPipelineResult {
  horizon: number
  generated_at: string
  pipeline: Record<string, unknown>
  explanations: Record<string, VerdictExplanation | VerdictExplanation[]>
  registry?: {
    recent_runs: unknown[]
    best_binance: unknown
    best_bcv: unknown
  }
  error?: string
}

export interface MacroImpactResult {
  elasticities: { category: string; ipc_elasticity: number; interpretation: string; n_obs: number }[]
  correlations: { category: string; macro_variable: string; correlation: number; strength: string }[]
  risk_score: number | null
  risk_level: string
  categories_analyzed: number
  error?: string
}

export interface NarrativeResult {
  executive_summary: string
  sections: Record<string, string>
  alerts: NarrativeAlert[]
  insight_count: number
  top_insights: InsightData[]
  generated_at: string
}

export interface NarrativeAlert {
  severity: 'critical' | 'warning' | 'notice' | 'info'
  subject: string
  text: string
  insight_id: string
}

export interface InsightData {
  id: string
  detector: string
  subject: string
  type: string
  direction: 'up' | 'down' | 'steady'
  magnitude: string
  severity: 'critical' | 'warning' | 'notice' | 'info'
  priority_score: number
  evidence: Record<string, unknown>
  tags: string[]
}

// ---- Purchasing Power ----
export interface PurchasingPowerResult {
  monthly_income_usd: number
  current_binance_rate: number
  lens_spending: {
    series: { year: number; month: number; total_usd: number }[]
    total_depreciation_pct: number | null
    depreciation_6m_pct: number | null
    description: string
  }
  lens_subscriptions: {
    monthly_subs_usd: number
    usd_subs_count: number
    subs_pct_of_income: number | null
    fx_depreciation_6m_pct: number | null
    description: string
  }
  lens_cesta_basica: {
    series: { year: number; month: number; total_usd: number | null; total_bs: number | null }[]
    income_vs_cesta: { year: number; month: number; baskets_covered: number }[]
    baskets_covered: number | null
    basket_depreciation_pct: number | null
    description: string
  }
  real_income_series: { year: number; month: number; nominal_income_usd: number; real_income_usd: number }[]
  projections: {
    avg_monthly_inflation_pct: number | null
    real_income_3m_usd: number | null
    real_income_6m_usd: number | null
    real_income_12m_usd: number | null
  }
}

// ---- Subscription Optimization ----
export interface SubOptimizationResult {
  total_monthly_usd: number
  total_annual_usd: number
  income_pct_of_subs: number | null
  sub_count: number
  usd_subs_count: number
  ves_subs_count: number
  potential_monthly_savings_usd: number
  potential_annual_savings_usd: number
  ranked_subscriptions: RankedSub[]
  cancel_candidates: RankedSub[]
  binance_rate: number
  fx_change_6m_pct: number | null
}

export interface RankedSub {
  id: number
  name: string
  currency: string
  frequency: string
  essential: boolean
  monthly_usd: number
  income_pct: number
  fx_growth_6m_pct: number | null
  fx_exposure: boolean
  score: number
  action: 'keep' | 'review' | 'monitor'
  reason: string
  annual_savings_if_cancelled_usd: number
}

// ---- Scenarios ----
export interface SavingPlan {
  target_name: string
  target_usd: number
  monthly_surplus_usd: number
  monthly_contribution_usd: number
  months_needed: number | null
  completion_date: string | null
  feasibility_score: number
  current_binance_rate: number
  monthly_fx_drift_pct: number
  fx_adjusted_ves_needed: number | null
  timelines: SavingTimeline[]
}

export interface SavingTimeline {
  months: number
  required_monthly_usd: number
  feasible: boolean
  projected_fx_at_purchase: number
  ves_needed: number
}

export interface MacroShockResult {
  scenario_params: {
    ipc_additional_monthly_pct: number
    fx_devaluation_pct: number
    income_change_pct: number
    horizon_months: number
  }
  baseline: {
    monthly_income_usd: number
    monthly_expenses_usd: number
    annual_net_usd: number
    current_fx_rate: number
  }
  shocked: {
    monthly_income_usd: number
    shocked_fx_rate: number
    total_monthly_inflation_pct: number
  }
  impact: {
    annual_net_change_usd: number
    annual_net_change_pct: number | null
    income_erosion_usd_12m: number
    expense_inflation_usd_12m: number
  }
  monthly_simulation: { month: number; income_usd: number; expenses_usd: number; net_usd: number; cumulative_balance_usd: number; projected_fx_rate: number }[]
}

// ---- Import History ----
export interface ImportBatch {
  id: string
  filename: string
  file_type: 'transactions' | 'rates' | 'macro_ipc' | 'macro_liquidity' | 'macro_gdp' | 'macro_oil'
  date_range_start: string | null
  date_range_end: string | null
  row_count: number
  imported_at: string
}

// ---- Analysis / Calculations ----
export interface MonthlySummary {
  year: number
  month: number
  total_income_usd: number
  total_expenses_usd: number
  net_balance_usd: number
  savings_rate: number
  category_breakdown: CategoryBreakdown[]
}

export interface CategoryBreakdown {
  categoria: string
  total_usd: number
  pct_of_expenses: number
  transaction_count: number
  avg_transaction_usd: number
}

export interface RunwayResult {
  days_no_income: number
  days_with_income: number
  daily_burn_usd: number
  daily_income_usd: number
  current_balance_usd: number
  projection_no_income: ProjectionPoint[]
  projection_with_income: ProjectionPoint[]
}

export interface ProjectionPoint {
  date: string
  balance_usd: number
}

export interface KpiData {
  current_balance_usd: number
  balance_change_pct: number
  runway_days: number
  monthly_burn_usd: number
  burn_change_pct: number
  savings_rate: number
  savings_rate_change: number
  real_income_usd: number
  real_income_change_pct: number
}

// ---- UI State ----
export type Tab = 'dashboard' | 'upload' | 'income' | 'subscriptions' | 'macro' | 'rates' | 'scenarios' | 'chat'

// ---- Chat ----
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  category?: string
  mode?: 'llm' | 'rule_based'
  source?: string
  timestamp: string
}

export type Theme = 'dark' | 'light'

export interface ParsedCSVRow {
  Fecha: string
  Hora: string
  Tipo: string
  Categoria: string
  Subcategoria: string
  Descripcion: string
  Cuenta: string
  'Monto (Bs)': string
  'Monto (USD)': string
  Tasa: string
  Moneda: string
  Comprobante: string
}

export interface FilePreview {
  filename: string
  fileType: 'transactions' | 'rates' | 'unknown'
  rowCount: number
  columns: string[]
  preview: Record<string, string>[]
  dateRange?: { start: string; end: string }
  warnings: string[]
}
