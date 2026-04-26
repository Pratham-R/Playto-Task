'use client'

import { useState, useEffect } from 'react'
import { getBankAccounts, createPayout } from '../api'

export default function PayoutForm({ merchantId }) {
  const [accounts, setAccounts] = useState([])
  const [amount, setAmount] = useState('')
  const [bankId, setBankId] = useState('')
  const [msg, setMsg] = useState(null)   // { ok: bool, text: string }
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setMsg(null)
    setAmount('')
    getBankAccounts(merchantId)
      .then(data => {
        setAccounts(data)
        if (data.length > 0) setBankId(data[0].id)
      })
      .catch(console.error)
  }, [merchantId])

  async function handleSubmit(e) {
    e.preventDefault()
    const rupees = parseFloat(amount)
    if (!rupees || rupees <= 0) {
      setMsg({ ok: false, text: 'Enter a valid amount.' })
      return
    }
    // Convert rupees → paise as integer (Math.round avoids float precision issues)
    const amountPaise = Math.round(rupees * 100)

    setLoading(true)
    setMsg(null)
    try {
      const { data, status } = await createPayout(merchantId, amountPaise, bankId)
      if (status === 201) {
        setMsg({ ok: true, text: 'Payout requested — processing shortly.' })
        setAmount('')
      } else {
        const detail = data.detail ?? data.error ?? 'Request failed.'
        setMsg({ ok: false, text: detail })
      }
    } catch {
      setMsg({ ok: false, text: 'Network error. Try again.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border p-6">
      <h2 className="text-sm font-medium text-gray-700 mb-4">Request Payout</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Amount (₹)</label>
          <input
            type="number"
            min="1"
            step="0.01"
            value={amount}
            onChange={e => setAmount(e.target.value)}
            placeholder="e.g. 500"
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Bank Account</label>
          <select
            value={bankId}
            onChange={e => setBankId(e.target.value)}
            className="w-full border rounded px-3 py-2 text-sm bg-white"
          >
            {accounts.map(a => (
              <option key={a.id} value={a.id}>
                {a.account_holder_name} ****{a.account_number_last4}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={loading || accounts.length === 0}
          className="w-full bg-blue-600 text-white rounded px-4 py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Submitting…' : 'Request Payout'}
        </button>
        {msg && (
          <p className={`text-xs ${msg.ok ? 'text-green-600' : 'text-red-600'}`}>
            {msg.text}
          </p>
        )}
      </form>
    </div>
  )
}
