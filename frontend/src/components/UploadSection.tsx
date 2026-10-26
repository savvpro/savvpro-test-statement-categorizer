import { useRef } from 'react'
import { formatFileSize } from '../utils/format'

type UploadSectionProps = Readonly<{
  loading: boolean
  fileName: string | null
  fileSize: number | null
  itemCount: number
  error: string | null
  onFile: (file: File | undefined) => void
  onSample: () => void
  onClear: () => void
}>

export function UploadSection({
  loading,
  fileName,
  fileSize,
  itemCount,
  error,
  onFile,
  onSample,
  onClear,
}: UploadSectionProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <div className="rounded-xl bg-surface-container-lowest p-space-xl shadow-md">
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-space-lg">
        <label className="flex-1 flex flex-col sm:flex-row items-start sm:items-center gap-space-lg p-space-lg rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors cursor-pointer">
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            className="hidden"
            disabled={loading}
            onChange={(e) => {
              onFile(e.target.files?.[0])
              e.target.value = ''
            }}
          />
          <div
            className="w-12 h-12 rounded-xl bg-surface-container-highest flex items-center justify-center text-primary shrink-0 shadow-inner"
            onClick={() => inputRef.current?.click()}
            onKeyDown={() => {}}
            role="presentation"
          >
            <span className="material-symbols-outlined text-[28px]">cloud_upload</span>
          </div>
          <div className="flex flex-col gap-0.5 min-w-0">
            <div className="flex flex-wrap items-center gap-space-xs">
              <span className="font-mono text-label-md text-on-surface font-semibold">
                Drop banking statement CSV here
              </span>
              <span className="text-outline-variant font-mono text-label-sm">or</span>
              <button
                type="button"
                className="font-mono text-label-md text-primary underline underline-offset-2 hover:text-primary-fixed"
                onClick={(e) => {
                  e.preventDefault()
                  inputRef.current?.click()
                }}
              >
                Choose CSV statement
              </button>
            </div>
            <p className="font-geist text-body-sm text-on-surface-variant">
              Chase, Amex, Mercury, Brex, and Apple Card CSV exports supported.
            </p>
          </div>
        </label>

        <div className="flex flex-col sm:flex-row lg:flex-col xl:flex-row items-stretch sm:items-center gap-space-md shrink-0">
          {fileName && (
            <div className="flex items-center justify-between sm:justify-start gap-space-md px-space-lg py-2.5 rounded-lg bg-surface-container text-on-surface">
              <div className="flex items-center gap-space-sm min-w-0">
                <span className="material-symbols-outlined text-[18px] text-primary">description</span>
                <div className="flex flex-col">
                  <span className="font-mono text-financial-md truncate max-w-[200px]">{fileName}</span>
                  <span className="font-mono text-label-sm text-on-surface-variant">
                    {fileSize != null ? formatFileSize(fileSize) : '—'} · {itemCount} items
                  </span>
                </div>
              </div>
              <button
                type="button"
                title="Remove statement"
                className="material-symbols-outlined text-[16px] text-outline hover:text-error cursor-pointer bg-transparent border-0"
                onClick={onClear}
              >
                close
              </button>
            </div>
          )}
          <button
            type="button"
            id="btn-sample-data"
            disabled={loading}
            onClick={onSample}
            className="inline-flex items-center justify-center gap-space-xs px-space-lg py-2.5 rounded-lg bg-primary-container hover:bg-primary text-on-primary font-mono text-label-md transition-all shadow-sm disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[16px]">play_circle</span>
            Load Sample CSV
          </button>
        </div>
      </div>
      {error && <p className="mt-space-md font-geist text-body-sm text-error">{error}</p>}
    </div>
  )
}
