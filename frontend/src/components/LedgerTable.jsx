'use client'

import { useState, useEffect } from 'react'
import { getLedger } from '../api'

const KIND_STYLE = {
  CREDIT:  'bg-green-50 text-green-700',
  HOLD:    'bg-yellow-50 text-yellow-700',
  RELEASE: 'bg-blue-50 text-blue-700',
}

export default function LedgerTable({ merchantId }) {
  const [entries, setEntries] = useState([])

  useEffect(() => {
    let cancelled = false

    function poll() {
      getLedger(merchantId)
        .then(d => { if (!cancelled) setEntries(d) })
        .catch(console.error)
    }

    poll()
    const id = setInterval(poll, 5000)
    return () => { cancelled = true; clearInterval(id) }
  }, [merchantId])

  return (
    <div className="bg-white rounded-xl border">
      <div className="px-4 py-3 border-b text-sm font-medium text-gray-700">
        Recent Activity
      </div>
      <div className="divide-y max-h-72 overflow-y-auto">
        {entries.length === 0 && (
          <p className="text-sm text-gray-400 p-4">No entries yet.</p>
        )}
        {entries.map(e => (
          <div key={e.id} className="flex items-center justify-between px-4 py-2.5 text-sm">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${KIND_STYLE[e.kind] ?? ''}`}>
              {e.kind}
            </span>
            <span className="font-mono text-gray-800">
              ₹{(e.amount_paise / 100).toFixed(2)}
            </span>
            <span className="text-gray-400 text-xs">
              {new Date(e.created_at).toLocaleDateString('en-IN')}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
