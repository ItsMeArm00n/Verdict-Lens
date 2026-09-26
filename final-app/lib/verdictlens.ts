const API_BASE = process.env.NEXT_PUBLIC_VERDICTLENS_API_URL || 'http://127.0.0.1:8000'

export type Applicant = Record<string, number | null>
export type Primary = { risk_estimate:number; threshold:number; decision:'APPROVE'|'REJECT'; signed_margin:number }
export type Challenger = { model:string; risk_estimate:number; own_policy_threshold:number; own_policy_decision:'APPROVE'|'REJECT'; at_primary_threshold_decision:'APPROVE'|'REJECT'; signed_difference_from_primary:number }
export type Audit = { schema_version:string; audit_version:string; primary:Primary; status:'REVIEW'|'NO_FLAGS_IN_CHECKS'; flags:string[]; input_quality:{code:string;feature:string}[]; challengers:Challenger[]; threshold_sensitivity:{threshold:number;decision:'APPROVE'|'REJECT'}[]; input_sensitivity:{scenario:string;kind:string;changes:Record<string,number>;risk_estimate:number;risk_delta:number;decision:'APPROVE'|'REJECT';decision_flipped:boolean}[]; limitations:string[]; explanation:string }
export type CaseRecord = { case_ref:string; created_at:string; stage:string; applicant:Applicant; primary:Primary|null; audit:Audit|null }
export type CaseSummary = { case_ref:string; created_at:string; stage:string; decision:Primary['decision']|null; risk_estimate:number|null; threshold:number|null; signed_margin:number|null; status:Audit['status']|null; flags:string[]; flag_count:number }

async function request<T>(path:string, options?:RequestInit):Promise<T>{
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...options, headers:{'Content-Type':'application/json',...(options?.headers||{})} })
    const body = await response.json().catch(()=>({detail:`Local API returned ${response.status}.`}))
    if(!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail))
    return body as T
  } catch(error) {
    if(error instanceof TypeError) throw new Error('Cannot reach the local VerdictLens engine. Start the Python backend on port 8000, then try again.')
    throw error
  }
}

export const api = {
  validateGemini:(api_key:string)=>request<{valid:boolean;model:string}>('/api/gemini/validate',{method:'POST',body:JSON.stringify({api_key})}),
  predict:(applicant:Applicant)=>request<CaseRecord & {primary:Primary}>('/api/predict',{method:'POST',body:JSON.stringify({applicant})}),
  audit:(case_ref:string)=>request<CaseRecord>('/api/audit',{method:'POST',body:JSON.stringify({case_ref})}),
  importJson:(raw:string)=>request<{count:number;cases:Applicant[]}>('/api/import',{method:'POST',body:JSON.stringify({raw})}),
  explain:(case_ref:string,api_key:string)=>request<{source:'template'|'gemini';markdown:string;model:string|null;error:string|null}>('/api/explain',{method:'POST',body:JSON.stringify({case_ref,api_key})}),
  explainPrimary:(case_ref:string,api_key:string)=>request<{source:'gemini';markdown:string;model:string|null;error:null}>('/api/explain-primary',{method:'POST',body:JSON.stringify({case_ref,api_key})}),
  cases:(search='')=>request<{total:number;cases:CaseSummary[]}>(`/api/cases?search=${encodeURIComponent(search)}`),
  case:(case_ref:string)=>request<CaseRecord>(`/api/cases/${encodeURIComponent(case_ref)}`),
}
