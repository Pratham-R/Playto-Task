const BASE = (process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000') + '/api/v1'

export async function getMerchants() {
  const res = await fetch(`${BASE}/merchants/`)
  if (!res.ok) throw new Error('Failed to fetch merchants')
  return res.json()
}

export async function getBalance(merchantId) {
  const res = await fetch(`${BASE}/merchants/${merchantId}/balance/`)
  if (!res.ok) throw new Error('Failed to fetch balance')
  return res.json()
}

export async function getLedger(merchantId) {
  const res = await fetch(`${BASE}/merchants/${merchantId}/ledger/`)
  if (!res.ok) throw new Error('Failed to fetch ledger')
  return res.json()
}

export async function getBankAccounts(merchantId) {
  const res = await fetch(`${BASE}/merchants/${merchantId}/bank-accounts/`)
  if (!res.ok) throw new Error('Failed to fetch bank accounts')
  return res.json()
}

export async function getPayouts(merchantId) {
  const res = await fetch(`${BASE}/merchants/${merchantId}/payouts/`)
  if (!res.ok) throw new Error('Failed to fetch payouts')
  return res.json()
}

export async function createPayout(merchantId, amountPaise, bankAccountId) {
  // crypto.randomUUID() — built into all modern browsers, no library needed
  const idempotencyKey = crypto.randomUUID()
  const res = await fetch(`${BASE}/merchants/${merchantId}/payouts/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Idempotency-Key': idempotencyKey,
    },
    body: JSON.stringify({ amount_paise: amountPaise, bank_account_id: bankAccountId }),
  })
  const data = await res.json()
  return { data, status: res.status }
}
