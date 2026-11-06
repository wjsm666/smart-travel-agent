/** Public HTTP contracts; field names follow docs/api.md and backend/app/contracts.py. */
export type Category = '自然' | '人文' | '休闲'
export type PlanMode = 'rules' | 'agent'

export interface Attraction {
  id: string
  city: string
  name: string
  category: Category
  description: string
  ticket_cny: number | null
  area: string
  duration_min: number | null
  source_url: string | null
  ticket_source_url: string | null
  ticket_checked_at: string | null
  ticket_note: string | null
}

export interface GenerationRequest {
  city: string
  day_count: number
  preferences: Category[]
  budget_cny: number
  mode: PlanMode
}

export interface CandidateDay {
  day: number
  attraction_ids: string[]
  note?: string | null
}

export interface AgentCandidate { days: CandidateDay[] }
export interface PlanInput extends GenerationRequest { days: CandidateDay[] }

export interface PlanDay {
  day: number
  attractions: Attraction[]
  subtotal_cny: number
  note?: string | null
}

interface PlanSummary extends GenerationRequest {
  days: PlanDay[]
  total_cny: number
  has_unknown_prices: boolean
  over_budget: boolean | null
  warnings: string[]
}

export interface PlanView extends PlanSummary { status: 'draft' }
export interface SavedTrip extends PlanSummary {
  status: 'saved'
  trip_id: string
  created_at: string
}

export interface ApiError { code: string; message: string }
