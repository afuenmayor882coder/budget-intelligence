import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail || err.message || 'Unknown error'
    return Promise.reject(new Error(msg))
  }
)

// ---- Transactions ----
export const transactions = {
  list: (params?: { skip?: number; limit?: number; tipo?: string; categoria?: string; month?: number; year?: number }) =>
    api.get('/transactions', { params }).then((r) => r.data),
  summary: (params?: { year?: number; month?: number }) =>
    api.get('/transactions/summary', { params }).then((r) => r.data),
  monthlySeries: () =>
    api.get('/transactions/monthly-series').then((r) => r.data),
  categories: () =>
    api.get('/transactions/categories').then((r) => r.data),
  delete: (id: number) =>
    api.delete(`/transactions/${id}`).then((r) => r.data),
}

// ---- Upload ----
export const upload = {
  csv: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/upload/csv', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data)
  },
  xlsx: (file: File, fileType?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (fileType) form.append('file_type', fileType)
    return api.post('/upload/xlsx', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data)
  },
  preview: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/upload/preview', form, { headers: { 'Content-Type': 'multipart/form-data' } }).then((r) => r.data)
  },
  history: () =>
    api.get('/upload/history').then((r) => r.data),
}

// ---- Exchange Rates ----
export const rates = {
  list: (params?: { limit?: number }) =>
    api.get('/rates', { params }).then((r) => r.data),
  latest: () =>
    api.get('/rates/latest').then((r) => r.data),
  gap: (months?: number) =>
    api.get('/rates/gap', { params: { months } }).then((r) => r.data),
  volatility: (window?: number) =>
    api.get('/rates/volatility', { params: { window } }).then((r) => r.data),
  sync: () =>
    api.post('/rates/sync').then((r) => r.data),
  syncStatus: () =>
    api.get('/rates/sync-status').then((r) => r.data),
  addCestaManual: (data: { year: number; month: number; total_bs?: number; total_usd?: number }) =>
    api.post('/rates/cesta-basica/manual', null, { params: data }).then((r) => r.data),
}

// ---- Income ----
export const income = {
  list: () => api.get('/income').then((r) => r.data),
  create: (data: object) => api.post('/income', data).then((r) => r.data),
  update: (id: number, data: object) => api.put(`/income/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/income/${id}`).then((r) => r.data),
}

// ---- Subscriptions ----
export const subscriptions = {
  list: () => api.get('/subscriptions').then((r) => r.data),
  create: (data: object) => api.post('/subscriptions', data).then((r) => r.data),
  update: (id: number, data: object) => api.put(`/subscriptions/${id}`, data).then((r) => r.data),
  delete: (id: number) => api.delete(`/subscriptions/${id}`).then((r) => r.data),
  optimize: () => api.get('/subscriptions/optimize').then((r) => r.data),
}

// ---- Dashboard / Analysis ----
export const analysis = {
  kpis: () => api.get('/analysis/kpis').then((r) => r.data),
  runway: (projection_days?: number) =>
    api.get('/analysis/runway', { params: { projection_days } }).then((r) => r.data),
  monthlySeries: (months?: number) =>
    api.get('/analysis/monthly-series', { params: { months } }).then((r) => r.data),
  monthlySummary: (year?: number, month?: number) =>
    api.get('/analysis/monthly-summary', { params: { year, month } }).then((r) => r.data),
  purchasingPower: () =>
    api.get('/analysis/purchasing-power').then((r) => r.data),
  narrative: () =>
    api.get('/analysis/narrative').then((r) => r.data),
  sectionNarrative: (section: string) =>
    api.get(`/analysis/narrative/${section}`).then((r) => r.data),
  clickInsight: (id: string) =>
    api.post(`/analysis/narrative/insight/${id}/click`).then((r) => r.data),
  dismissInsight: (id: string) =>
    api.post(`/analysis/narrative/insight/${id}/dismiss`).then((r) => r.data),
}

// ---- Macro ----
export const macro = {
  ipc: () => api.get('/macro/ipc').then((r) => r.data),
  ipcLatest: () => api.get('/macro/ipc/latest').then((r) => r.data),
  liquidity: () => api.get('/macro/liquidity').then((r) => r.data),
  gdp: () => api.get('/macro/gdp').then((r) => r.data),
  oil: () => api.get('/macro/oil').then((r) => r.data),
  parallelRate: () => api.get('/macro/parallel-rate').then((r) => r.data),
  cestaBasica: () => api.get('/macro/cesta-basica').then((r) => r.data),
  cestaLatest: () => api.get('/macro/cesta-basica/latest').then((r) => r.data),
  addCesta: (data: { year: number; month: number; total_bs?: number; total_usd?: number }) =>
    api.post('/macro/cesta-basica/manual', data).then((r) => r.data),
  summary: () => api.get('/macro/summary').then((r) => r.data),
}

// ---- Scenarios / What-If ----
export const scenarios = {
  presets: () => api.get('/scenarios/presets').then((r) => r.data),
  savingGoal: (data: {
    target_usd: number
    target_name?: string
    target_months?: number
    monthly_contribution?: number
    cancel_sub_ids?: number[]
  }) => api.post('/scenarios/saving-goal', data).then((r) => r.data),
  goals: () => api.get('/scenarios/goals').then((r) => r.data),
  subToggle: (data: { sub_ids: number[]; toggle_state?: boolean }) =>
    api.post('/scenarios/sub-toggle', data).then((r) => r.data),
  macroShock: (data: {
    ipc_monthly_change_pct?: number
    fx_devaluation_pct?: number
    income_change_pct?: number
    horizon_months?: number
  }) => api.post('/scenarios/macro-shock', data).then((r) => r.data),
  timeline: (months?: number) =>
    api.get('/scenarios/timeline', { params: { months } }).then((r) => r.data),
}

// ---- Forecasts / Econometrics (Phase 3) ----
export const forecasts = {
  fx: (horizon?: number) =>
    api.get('/forecasts/fx', { params: { horizon } }).then((r) => r.data),
  fxLatest: (horizon?: number) =>
    api.get('/forecasts/fx/latest', { params: { horizon } }).then((r) => r.data),
  macroImpact: () =>
    api.get('/forecasts/macro-impact').then((r) => r.data),
  registry: (params?: { target?: string; layer?: string }) =>
    api.get('/forecasts/registry', { params }).then((r) => r.data),
  bestModels: () =>
    api.get('/forecasts/registry/best').then((r) => r.data),
}

// ---- Reports ----
export const reports = {
  exportMarkdown: () =>
    api.post('/reports/monthly/markdown').then((r) => r.data),
  exportPdf: () =>
    api.post('/reports/monthly/pdf').then((r) => r.data),
}

// ---- Chat (Phase 5) ----
export const chat = {
  sendMessage: (data: {
    message: string
    conversation_id?: string
    anthropic_api_key?: string
    openai_api_key?: string
  }) => api.post('/chat/message', data).then((r) => r.data),
  getHistory: (conversationId?: string) =>
    api.get(`/chat/history/${conversationId ?? 'default'}`).then((r) => r.data),
  clearHistory: (conversationId?: string) =>
    api.delete(`/chat/history/${conversationId ?? 'default'}`).then((r) => r.data),
  getSuggestions: () =>
    api.get('/chat/suggestions').then((r) => r.data),
  getStatus: () =>
    api.get('/chat/status').then((r) => r.data),
}

export default api
