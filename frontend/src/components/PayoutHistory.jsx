'use client'

import { useState, useEffect } from 'react'
import { getPayouts } from '../api'

const STATUS_STYLE = {
  PENDING:    'bg-gray-100 text-gray-600',
  PROCESSING: 'bg-yellow-100 text-yellow-700',
  COMPLETED:  'bg-green-100 text-green-700',
  FAILED:     'bg-red-100 text-red-700',
}

export default function PayoutHistory({ merchantId }) {
  const [payouts, setPayouts] = useState([])

  useEffect(() => {
    let cancelled = false

    function poll() {
      getPayouts(merchantId)
        .then(d => { if (!cancelled) setPayouts(d) })
        .catch(console.error)
    }

    poll()
    const id = setInterval(poll, 3000)
    return () => { cancelled = true; clearInterval(id) }
  }, [merchantId])

  return (
    <div className="bg-white rounded-xl border">
      <div className="px-4 py-3 border-b text-sm font-medium text-gray-700 flex items-center">
        Payout History
        <span className="ml-2 text-xs text-gray-400 font-normal">live — refreshes every 3 s</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
            <tr>
              <th className="px-4 py-2 text-left">Payout ID</th>
              <th className="px-4 py-2 text-right">Amount</th>
              <th className="px-4 py-2 text-center">Status</th>
              <th className="px-4 py-2 text-left">Requested At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {payouts.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-400">
                  No payouts yet. Request one above.
                </td>
              </tr>
            )}
            {payouts.map(p => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-mono text-xs text-gray-500">
                  {p.id.slice(0, 8)}…
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-gray-800">
                  ₹{(p.amount_paise / 100).toFixed(2)}
                </td>
                <td className="px-4 py-2.5 text-center">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLE[p.status] ?? ''}`}>
                    {p.status}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-gray-400 text-xs">
                  {new Date(p.created_at).toLocaleString('en-IN')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
