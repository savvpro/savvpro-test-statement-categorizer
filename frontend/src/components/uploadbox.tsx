import React, { useState } from 'react'
import { fetchapi } from '../api'

interface Props {
  onuploadsuccess: (id: number) => void
}

export default function Uploadbox({ onuploadsuccess }: Props) {
  const [file, setfile] = useState<File | null>(null)
  const [loading, setloading] = useState(false)
  const [error, seterror] = useState("")
  const [skipped, setskipped] = useState<any[]>([])
  const [expanded, setexpanded] = useState(false)

  const handleupload = async () => {
    if (!file) return
    setloading(true)
    seterror("")
    setskipped([])
    const formdata = new FormData()
    formdata.append("file", file)

    try {
      const data = await fetchapi("/api/uploads", {
        method: "POST",
        body: formdata
      })
      if (data.skippedrows.length > 0) setskipped(data.skippedrows)
      onuploadsuccess(data.uploadid)
    } catch (err: any) {
      seterror(err.message)
    } finally {
      setloading(false)
    }
  }

  return (
    <div className="card">
      <h2>Upload Statement</h2>
      <div className="flex">
        <input type="file" accept=".csv" onChange={(e) => setfile(e.target.files?.[0] || null)} />
        <button onClick={handleupload} disabled={!file || loading}>
          {loading ? "Uploading..." : "Upload"}
        </button>
      </div>
      {error && <div className="red" style={{ marginTop: 10 }}>{error}</div>}
      {skipped.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <strong className="red">{skipped.length} rows skipped</strong>
          <button onClick={() => setexpanded(!expanded)} style={{ marginLeft: 10 }}>
            {expanded ? "Hide" : "Show details"}
          </button>
          {expanded && (
            <ul style={{ fontSize: 12, color: "#4b5563" }}>
              {skipped.map((s, i) => <li key={i}>Row {s.row}: {s.reason}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}