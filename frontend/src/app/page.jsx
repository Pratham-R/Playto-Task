'use client'

import { useState, useEffect } from 'react'
import { getMerchants } from '../api'
import BalanceCard from '../components/BalanceCard'
import LedgerTable from '../components/LedgerTable'
import PayoutForm from '../components/PayoutForm'
import PayoutHistory from '../components/PayoutHistory'

export default function Page() {
  const [merchants, setMerchants] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getMerchants()
      .then(data => {
        setMerchants(data)
        if (data.length > 0) setSelectedId(data[0].merchant_id)
      })
      .catch(err => {
        console.error(err)
        setError(err.message)
      })
  }, [])

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b px-6 py-4 flex items-center gap-4">
        <h1 className="text-lg font-semibold text-gray-900">Playto Pay — Payout Engine</h1>
        <select
          className="ml-auto border rounded px-3 py-1.5 text-sm bg-white"
          value={selectedId ?? ''}
          onChange={e => setSelectedId(e.target.value)}
        >
          {merchants.map(m => (
            <option key={m.merchant_id} value={m.merchant_id}>
              {m.name}
            </option>
          ))}
        </select>
      </header>

      {error && (
        <div className="max-w-5xl mx-auto px-6 py-4">
          <div className="bg-red-50 border border-red-200 rounded p-4 text-sm text-red-700">
            <strong>API error:</strong> {error} — is Django running on port 8000?
          </div>
        </div>
      )}

      {!error && merchants.length === 0 && (
        <div className="max-w-5xl mx-auto px-6 py-4 text-sm text-gray-400">
          Loading merchants…
        </div>
      )}

      {selectedId && (
        <main className="max-w-5xl mx-auto px-6 py-8 space-y-8">
          <BalanceCard merchantId={selectedId} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <PayoutForm merchantId={selectedId} />
            <LedgerTable merchantId={selectedId} />
          </div>
          <PayoutHistory merchantId={selectedId} />
        </main>
      )}
    </div>
  )
}
