import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, LineChart, Line,
} from 'recharts'
import { Plus } from 'lucide-react'
import { macro } from '@/lib/api'
import { formatMonthYear, formatNumber, formatUSD, cn } from '@/lib/utils'
import { Card, CardHeader, CardTitle } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { SectionAnalysis } from '@/components/ui/SectionAnalysis'
import { EconometricPanel } from '@/components/macro/EconometricPanel'
import { toast } from 'sonner'

export function MacroPage() {
  const [showCestaForm, setShowCestaForm] = useState(false)
  const [cestaForm, setCestaForm] = useState({ year: new Date().getFullYear(), month: new Date().getMonth() + 1, total_bs: '', total_usd: '' })

  const { data: ipcData = [], isLoading: ipcLoading } = useQuery({
    queryKey: ['macro-ipc'],
    queryFn: macro.ipc,
  })

  const { data: liquidityData = [], isLoading: liquidityLoading } = useQuery({
    queryKey: ['macro-liquidity'],
    queryFn: macro.liquidity,
  })

  const { data: gdpData = [], isLoading: gdpLoading } = useQuery({
    queryKey: ['macro-gdp'],
    queryFn: macro.gdp,
  })

  const { data: oilData = [], isLoading: oilLoading } = useQuery({
    queryKey: ['macro-oil'],
    queryFn: macro.oil,
  })

  const { data: cestaData = [] } = useQuery({
    queryKey: ['macro-cesta'],
    queryFn: macro.cestaBasica,
  })

  const { data: parallelData = [] } = useQuery({
    queryKey: ['macro-parallel'],
    queryFn: macro.parallelRate,
  })

  const { data: macroSummary } = useQuery({
    queryKey: ['macro-summary'],
    queryFn: macro.summary,
    staleTime: 10 * 60_000,
  })

  const addCestaMutation = useMutation({
    mutationFn: (data: any) => macro.addCesta(data),
    onSuccess: () => {
      toast.success('Cesta Básica entry added')
      setShowCestaForm(false)
    },
    onError: (err: Error) => toast.error(err.message),
  })

  const chartIPC = (ipcData as any[]).slice(-24).map((d: any) => ({
    name: formatMonthYear(d.year, d.month),
    'Var %': d.var_pct ?? 0,
  }))

  const chartLiquidity = (liquidityData as any[]).slice(-24).map((d: any) => ({
    name: formatMonthYear(d.year, d.month),
    M2: (d.m2 ?? 0) / 1e9,
  }))

  const chartGDP = (gdpData as any[]).slice(-20).map((d: any) => ({
    name: d.year ?? d.period,
    GDP: d.gdp_usd_bn ?? d.value,
  }))

  const chartOil = (oilData as any[]).slice(-24).map((d: any) => ({
    name: formatMonthYear(d.year, d.month),
    'Revenue': d.revenue_usd_mn ?? d.value,
  }))

  const chartCesta = (cestaData as any[]).slice(-24).map((d: any) => ({
    name: formatMonthYear(d.year, d.month),
    'USD': d.total_usd,
    'Bs': d.total_bs != null ? d.total_bs / 1000 : null,
  }))

  const chartParallel = (parallelData as any[]).slice(-24).map((d: any) => ({
    name: formatMonthYear(d.year, d.month),
    'Rate': d.rate,
  }))

  const latestIPC = (ipcData as any[]).at(-1)
  const latestCesta = (cestaData as any[]).at(-1)

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-primary">Macroeconomic Analysis</h1>
        <p className="text-sm text-secondary mt-1">Venezuela macro indicators from BCV official data</p>
      </div>

      {/* Macro summary strip */}
      {macroSummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {macroSummary.ipc_latest != null && (
            <Card padding="md">
              <p className="text-xs text-tertiary uppercase tracking-wider mb-2">IPC (latest)</p>
              <p className={cn('mono text-xl font-semibold', macroSummary.ipc_latest > 10 ? 'text-accent-red' : macroSummary.ipc_latest > 5 ? 'text-accent-amber' : 'text-accent-green')}>
                {formatNumber(macroSummary.ipc_latest, 1)}%
              </p>
              <p className="text-xs text-tertiary mt-1">Monthly change</p>
            </Card>
          )}
          {macroSummary.cesta_usd != null && (
            <Card padding="md">
              <p className="text-xs text-tertiary uppercase tracking-wider mb-2">Cesta Básica</p>
              <p className="mono text-xl font-semibold text-primary">{formatUSD(macroSummary.cesta_usd)}</p>
              <p className="text-xs text-tertiary mt-1">Latest basket (USD)</p>
            </Card>
          )}
          {macroSummary.gdp_usd_bn != null && (
            <Card padding="md">
              <p className="text-xs text-tertiary uppercase tracking-wider mb-2">GDP</p>
              <p className="mono text-xl font-semibold text-primary">{formatNumber(macroSummary.gdp_usd_bn, 0)}B</p>
              <p className="text-xs text-tertiary mt-1">USD billion (latest)</p>
            </Card>
          )}
          {macroSummary.oil_revenue_usd_mn != null && (
            <Card padding="md">
              <p className="text-xs text-tertiary uppercase tracking-wider mb-2">Oil Revenue</p>
              <p className="mono text-xl font-semibold text-primary">{formatNumber(macroSummary.oil_revenue_usd_mn, 0)}M</p>
              <p className="text-xs text-tertiary mt-1">USD million (latest)</p>
            </Card>
          )}
        </div>
      )}

      {/* IPC Chart */}
      <Card padding="md">
        <CardHeader>
          <CardTitle>IPC Monthly Change (%)</CardTitle>
          <span className="text-xs text-tertiary">Source: BCV</span>
        </CardHeader>
        {ipcLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : chartIPC.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartIPC} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="ipcGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-amber)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="var(--accent-amber)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} interval={3} />
              <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} width={40} />
              <Tooltip formatter={(v: any) => [`${Number(v).toFixed(1)}%`, 'IPC Var']} contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }} />
              <Area type="monotone" dataKey="Var %" stroke="var(--accent-amber)" strokeWidth={1.5} fill="url(#ipcGrad)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-48 flex items-center justify-center text-tertiary text-sm">
            Upload IPC.xlsx to see inflation data
          </div>
        )}
      </Card>

      {/* Liquidity + GDP side by side */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card padding="md">
          <CardHeader>
            <CardTitle>Monetary Liquidity M2</CardTitle>
            <span className="text-xs text-tertiary">Billions Bs · BCV</span>
          </CardHeader>
          {liquidityLoading ? (
            <Skeleton className="h-44 w-full" />
          ) : chartLiquidity.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={chartLiquidity} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="m2Grad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} interval={3} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v.toFixed(0)}B`} width={40} />
                <Tooltip formatter={(v: any) => [`${Number(v).toFixed(1)}B Bs`, 'M2']} contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }} />
                <Area type="monotone" dataKey="M2" stroke="var(--accent-blue)" strokeWidth={1.5} fill="url(#m2Grad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-44 flex items-center justify-center text-tertiary text-sm">
              Upload liquidez_monetaria_mensual.xlsx
            </div>
          )}
        </Card>

        <Card padding="md">
          <CardHeader>
            <CardTitle>GDP (USD Billions)</CardTitle>
            <span className="text-xs text-tertiary">Annual · BCV</span>
          </CardHeader>
          {gdpLoading ? (
            <Skeleton className="h-44 w-full" />
          ) : chartGDP.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={chartGDP} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}B`} width={40} />
                <Tooltip formatter={(v: any) => [`$${Number(v).toFixed(1)}B`, 'GDP']} contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }} />
                <Bar dataKey="GDP" fill="var(--accent-green)" opacity={0.7} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-44 flex items-center justify-center text-tertiary text-sm">
              Upload PIB.xlsx to see GDP data
            </div>
          )}
        </Card>
      </div>

      {/* Oil Revenue + Parallel Rate */}
      <div className="grid md:grid-cols-2 gap-4">
        <Card padding="md">
          <CardHeader>
            <CardTitle>Oil Revenue (USD M)</CardTitle>
            <span className="text-xs text-tertiary">Monthly · PDVSA / BCV</span>
          </CardHeader>
          {oilLoading ? (
            <Skeleton className="h-44 w-full" />
          ) : chartOil.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={chartOil} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} interval={3} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} width={40} />
                <Tooltip formatter={(v: any) => [`$${Number(v).toFixed(0)}M`, 'Oil Revenue']} contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }} />
                <Bar dataKey="Revenue" fill="var(--accent-amber)" opacity={0.7} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-44 flex items-center justify-center text-tertiary text-sm">
              Upload ingresos_petroleo.xlsx to see oil revenue
            </div>
          )}
        </Card>

        <Card padding="md">
          <CardHeader>
            <CardTitle>Reconstructed Parallel Rate</CardTitle>
            <span className="text-xs text-tertiary">Monthly avg · VES/USD</span>
          </CardHeader>
          {chartParallel.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <LineChart data={chartParallel} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} interval={3} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => formatNumber(v, 0)} width={50} />
                <Tooltip formatter={(v: any) => [formatNumber(Number(v), 2) + ' Bs', 'Parallel']} contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }} />
                <Line type="monotone" dataKey="Rate" stroke="var(--accent-red)" strokeWidth={1.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-44 flex items-center justify-center text-tertiary text-sm">
              Upload tasa_paralela.xlsx to see parallel rate history
            </div>
          )}
        </Card>
      </div>

      {/* Cesta Básica */}
      <Card padding="md">
        <CardHeader>
          <div>
            <CardTitle>Cesta Básica Alimentaria</CardTitle>
            <p className="text-xs text-tertiary mt-0.5">Basic food basket cost — BCV / CENDAS</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            icon={<Plus className="w-3.5 h-3.5" />}
            onClick={() => setShowCestaForm((v) => !v)}
          >
            Manual entry
          </Button>
        </CardHeader>

        {showCestaForm && (
          <div className="mb-4 p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-elevated)]">
            <p className="text-xs text-secondary mb-3">Add Cesta Básica data manually</p>
            <div className="grid grid-cols-4 gap-2">
              <Input
                label="Year"
                type="number"
                value={String(cestaForm.year)}
                onChange={(e) => setCestaForm({ ...cestaForm, year: parseInt(e.target.value) })}
              />
              <Input
                label="Month"
                type="number"
                min="1"
                max="12"
                value={String(cestaForm.month)}
                onChange={(e) => setCestaForm({ ...cestaForm, month: parseInt(e.target.value) })}
              />
              <Input
                label="Total Bs"
                type="number"
                placeholder="optional"
                value={cestaForm.total_bs}
                onChange={(e) => setCestaForm({ ...cestaForm, total_bs: e.target.value })}
              />
              <Input
                label="Total USD"
                type="number"
                placeholder="optional"
                value={cestaForm.total_usd}
                onChange={(e) => setCestaForm({ ...cestaForm, total_usd: e.target.value })}
              />
            </div>
            <div className="flex justify-end gap-2 mt-3">
              <Button variant="ghost" size="sm" onClick={() => setShowCestaForm(false)}>Cancel</Button>
              <Button
                variant="primary"
                size="sm"
                loading={addCestaMutation.isPending}
                onClick={() => addCestaMutation.mutate({
                  year: cestaForm.year,
                  month: cestaForm.month,
                  total_bs: cestaForm.total_bs ? parseFloat(cestaForm.total_bs) : undefined,
                  total_usd: cestaForm.total_usd ? parseFloat(cestaForm.total_usd) : undefined,
                })}
              >
                Save
              </Button>
            </div>
          </div>
        )}

        {chartCesta.length > 0 ? (
          <>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={chartCesta} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="cestaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-green)" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="var(--accent-green)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" strokeOpacity={0.5} vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} interval={3} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-tertiary)', fontFamily: 'JetBrains Mono, monospace' }} axisLine={false} tickLine={false} tickFormatter={(v) => `$${v}`} width={40} />
                <Tooltip
                  formatter={(v: any, name: string) => [name === 'USD' ? `$${Number(v).toFixed(0)}` : `${Number(v).toFixed(0)}kBs`, name]}
                  contentStyle={{ background: 'var(--surface-elevated)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '12px' }}
                />
                <Area type="monotone" dataKey="USD" stroke="var(--accent-green)" strokeWidth={1.5} fill="url(#cestaGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
            {latestCesta && (
              <SectionAnalysis
                text={`Latest Cesta Básica: ${latestCesta.total_usd != null ? formatUSD(latestCesta.total_usd) : '—'} (${formatMonthYear(latestCesta.year, latestCesta.month)}). ${latestCesta.total_bs != null ? `In bolivars: Bs ${formatNumber(latestCesta.total_bs, 0)}.` : ''}`}
                label="Cesta Básica"
                className="mt-4 pt-4 border-t border-[var(--border)]"
              />
            )}
          </>
        ) : (
          <div className="h-40 flex flex-col items-center justify-center text-tertiary text-sm gap-2">
            <p>No Cesta Básica data yet</p>
            <p className="text-xs">Use "Manual entry" above or upload via cloud automation</p>
          </div>
        )}
      </Card>

      {/* Phase 3: Econometric Analysis */}
      <EconometricPanel horizon={7} />
    </div>
  )
}
