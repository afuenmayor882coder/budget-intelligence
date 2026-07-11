import { useState, useRef, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Upload as UploadIcon, FileText, AlertCircle, CheckCircle, X, ChevronRight } from 'lucide-react'
import { upload } from '@/lib/api'
import { formatDate, cn } from '@/lib/utils'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Skeleton } from '@/components/ui/Skeleton'
import { toast } from 'sonner'

interface FilePreview {
  filename: string
  fileType: string
  rowCount: number
  columns: string[]
  preview: Record<string, string>[]
  dateRange?: { start: string; end: string }
  warnings: string[]
  duplicates?: number
}

export function UploadPage() {
  const [dragging, setDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<FilePreview | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [importing, setImporting] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ['upload-history'],
    queryFn: upload.history,
  })

  const handleFile = useCallback(async (file: File) => {
    setSelectedFile(file)
    setPreview(null)
    setPreviewing(true)
    try {
      const result = await upload.preview(file)
      setPreview(result)
    } catch (err: any) {
      toast.error(err.message || 'Failed to preview file')
    } finally {
      setPreviewing(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  const handleImport = async () => {
    if (!selectedFile || !preview) return
    setImporting(true)
    try {
      const isCsv = selectedFile.name.toLowerCase().endsWith('.csv')
      let result: any
      if (isCsv) {
        result = await upload.csv(selectedFile)
      } else {
        result = await upload.xlsx(selectedFile, preview.fileType)
      }
      toast.success(`Imported ${result.imported} rows${result.skipped ? `, ${result.skipped} duplicates skipped` : ''}`)
      setSelectedFile(null)
      setPreview(null)
      queryClient.invalidateQueries({ queryKey: ['kpis'] })
      queryClient.invalidateQueries({ queryKey: ['monthly-series'] })
      queryClient.invalidateQueries({ queryKey: ['summary'] })
      queryClient.invalidateQueries({ queryKey: ['runway'] })
      queryClient.invalidateQueries({ queryKey: ['upload-history'] })
    } catch (err: any) {
      toast.error(err.message || 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-primary">Upload Data</h1>
        <p className="text-sm text-secondary mt-1">Import your Rial CSV exports or macro Excel files</p>
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          'border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200',
          dragging
            ? 'border-[var(--accent-green)] bg-[var(--accent-green-muted)]'
            : 'border-[var(--border)] hover:border-[var(--text-tertiary)] hover:bg-[var(--surface)]'
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />
        <UploadIcon className={cn('w-10 h-10 mx-auto mb-4 transition-colors', dragging ? 'text-accent-green' : 'text-tertiary')} />
        <p className="text-sm font-medium text-primary mb-1">
          {dragging ? 'Drop to upload' : 'Drop files here or click to browse'}
        </p>
        <p className="text-xs text-tertiary">Supports .csv (Rial transactions) and .xlsx (macro data, rates)</p>
      </div>

      {/* Preview */}
      {(previewing || preview) && (
        <Card padding="md">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <FileText className="w-5 h-5 text-secondary" />
              <div>
                <p className="text-sm font-medium text-primary">{selectedFile?.name}</p>
                {preview && (
                  <p className="text-xs text-tertiary mt-0.5">
                    {preview.rowCount.toLocaleString()} rows · {preview.fileType === 'rates' ? 'Exchange Rates' : preview.fileType === 'transactions' ? 'Transactions' : 'Unknown type'}
                    {preview.dateRange && ` · ${formatDate(preview.dateRange.start)} – ${formatDate(preview.dateRange.end)}`}
                  </p>
                )}
              </div>
            </div>
            <button
              onClick={() => { setSelectedFile(null); setPreview(null) }}
              className="w-7 h-7 rounded-lg flex items-center justify-center text-tertiary hover:text-primary hover:bg-[var(--surface-elevated)] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {previewing ? (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          ) : preview ? (
            <>
              {/* Warnings */}
              {preview.warnings?.length > 0 && (
                <div className="bg-[var(--accent-amber-muted)] border border-[var(--accent-amber)] border-opacity-20 rounded-lg p-3 mb-4 space-y-1">
                  {preview.warnings.map((w, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <AlertCircle className="w-3.5 h-3.5 text-accent-amber flex-shrink-0" />
                      <p className="text-xs text-accent-amber">{w}</p>
                    </div>
                  ))}
                </div>
              )}

              {preview.fileType === 'rates' && (
                <div className="bg-[var(--accent-blue-muted)] border border-[var(--accent-blue)] border-opacity-20 rounded-lg p-3 mb-4">
                  <div className="flex items-center gap-2 mb-1">
                    <AlertCircle className="w-3.5 h-3.5 text-accent-blue" />
                    <p className="text-xs font-medium text-accent-blue">Exchange Rate File Detected</p>
                  </div>
                  <p className="text-xs text-secondary ml-5">
                    This will <strong>replace</strong> your current exchange rate history with {preview.rowCount} entries from this file.
                  </p>
                </div>
              )}

              {/* Data preview table */}
              {preview.preview?.length > 0 && (
                <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-[var(--surface-elevated)]">
                        {preview.columns?.slice(0, 6).map((col) => (
                          <th key={col} className="px-3 py-2 text-left text-tertiary font-medium whitespace-nowrap">
                            {col}
                          </th>
                        ))}
                        {(preview.columns?.length ?? 0) > 6 && (
                          <th className="px-3 py-2 text-left text-tertiary font-medium">+{preview.columns.length - 6} more</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.preview.slice(0, 4).map((row, i) => (
                        <tr key={i} className="border-t border-[var(--border)] hover:bg-[var(--surface-elevated)] transition-colors">
                          {preview.columns?.slice(0, 6).map((col) => (
                            <td key={col} className="px-3 py-2 text-secondary mono whitespace-nowrap max-w-[140px] overflow-hidden text-ellipsis">
                              {row[col] ?? '—'}
                            </td>
                          ))}
                          {(preview.columns?.length ?? 0) > 6 && <td className="px-3 py-2 text-tertiary">...</td>}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Import button */}
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-[var(--border)]">
                <div className="flex items-center gap-2">
                  {preview.duplicates !== undefined && preview.duplicates > 0 && (
                    <Badge variant="amber">{preview.duplicates} duplicates will be skipped</Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" onClick={() => { setSelectedFile(null); setPreview(null) }}>
                    Cancel
                  </Button>
                  <Button variant="primary" size="sm" loading={importing} onClick={handleImport}>
                    <CheckCircle className="w-3.5 h-3.5" />
                    Import {preview.rowCount.toLocaleString()} rows
                  </Button>
                </div>
              </div>
            </>
          ) : null}
        </Card>
      )}

      {/* Import history */}
      <div>
        <h2 className="text-sm font-medium text-secondary mb-3 uppercase tracking-wider">Import History</h2>
        {historyLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <Skeleton key={i} className="h-14 w-full rounded-xl" />)}
          </div>
        ) : history?.length > 0 ? (
          <div className="space-y-2">
            {history.map((h: any) => (
              <Card key={h.id} padding="sm" hoverable>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-[var(--surface-elevated)] flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-tertiary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-primary truncate">{h.filename}</p>
                    <p className="text-xs text-tertiary">
                      {h.row_count?.toLocaleString()} rows · {formatDate(h.imported_at)}
                      {h.date_range_start && ` · ${formatDate(h.date_range_start)} – ${formatDate(h.date_range_end)}`}
                    </p>
                  </div>
                  <Badge variant={h.file_type === 'transactions' ? 'blue' : h.file_type === 'rates' ? 'amber' : 'default'}>
                    {h.file_type}
                  </Badge>
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-tertiary text-sm">
            <FileText className="w-8 h-8 mx-auto mb-2 opacity-30" />
            No imports yet
          </div>
        )}
      </div>
    </div>
  )
}
