'use client'

import { useState, useEffect } from 'react'
import { getBalance } from '../api'

function formatRupees(paise) {
  return '₹' + (paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })
}

export default function BalanceCard({ merchantId }) {
  const [balance, setBalance] = useState(null)

  useEffect(() => {
    let cancelled = false

    function poll() {
      getBalance(merchantId)
        .then(d => { if (!cancelled) setBalance(d) })
        .catch(console.error)
    }

    poll()
    const id = setInterval(poll, 3000)
    return () => { cancelled = true; clearInterval(id) }
  }, [merchantId])

  if (!balance) {
    return <div className="text-sm text-gray-400">Loading balance…</div>
  }

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-white rounded-xl border p-6">
        <p className="text-sm text-gray-500">Available Balance</p>
        <p className="text-3xl font-bold text-gray-900 mt-1">
          {formatRupees(balance.available_paise)}
        </p>
        <p className="text-xs text-gray-400 mt-1">{balance.available_paise} paise</p>
      </div>
      <div className="bg-white rounded-xl border p-6">
        <p className="text-sm text-gray-500">Held (Pending Payouts)</p>
        <p className="text-3xl font-bold text-yellow-600 mt-1">
          {formatRupees(balance.held_paise)}
        </p>
        <p className="text-xs text-gray-400 mt-1">{balance.held_paise} paise</p>
      </div>
    </div>
  )
}
