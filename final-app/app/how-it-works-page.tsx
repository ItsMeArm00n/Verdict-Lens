'use client'

import { useEffect, useRef, useState } from 'react'
import { AlertTriangle, ArrowRight, Check, CircleGauge, Database, GitCompareArrows, Pause, Play, ScanSearch, SlidersHorizontal, UserCheck, Zap } from 'lucide-react'

type PageKey='overview'|'new'|'decision'|'audit'|'cases'|'how'|'about'
const checks=[
  {code:'01',label:'Model comparison',short:'Two independent challengers test whether model choice changes the outcome.',Icon:GitCompareArrows,tags:['LOGISTIC','RANDOM FOREST']},
  {code:'02',label:'Threshold stability',short:'Nearby policy cutoffs reveal decisions that sit close to the boundary.',Icon:SlidersHorizontal,tags:['−2%','−1%','BASE','+1%','+2%']},
  {code:'03',label:'Input sensitivity',short:'Small controlled probes test whether the primary decision flips.',Icon:Zap,tags:['UTILIZATION','DEBT','INCOME','AGE']},
  {code:'04',label:'Input quality',short:'Missing, ambiguous, and unusual values are surfaced for review.',Icon:ScanSearch,tags:['MISSING','RANGE','AMBIGUOUS']},
]

export function HowItWorksPage({onNavigate}:{onNavigate:(page:PageKey)=>void}){
 const [active,setActive]=useState(0),[paused,setPaused]=useState(false),[visible,setVisible]=useState(false)
 const mapRef=useRef<HTMLDivElement>(null)
 useEffect(()=>{const element=mapRef.current;if(!element)return;const observer=new IntersectionObserver(([entry])=>setVisible(entry.isIntersecting),{threshold:.2});observer.observe(element);return()=>observer.disconnect()},[])
 useEffect(()=>{if(!visible||paused||window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;const timer=setInterval(()=>setActive(value=>(value+1)%checks.length),2400);return()=>clearInterval(timer)},[visible,paused])
 const selected=checks[active],SelectedIcon=selected.Icon
 return <div className="page-content how-v2-page">
   <section className="how-v2-hero" data-reveal="stagger">
     <div><span className="eyebrow">METHOD / SYSTEM MAP</span><h2>One decision.<br/><em>Four independent checks.</em></h2><p>VerdictLens keeps the original model result visible, tests how stable it is, and sends the evidence to a human reviewer.</p></div>
     <div className="how-v2-summary"><span>CORE PRINCIPLE</span><strong>Inspect the decision.<br/>Never silently replace it.</strong><small>Local · deterministic · traceable</small></div>
   </section>

   <section className={`system-map organic-map ${visible?'is-running':''} ${paused?'is-paused':''}`} ref={mapRef} aria-label="VerdictLens audit process">
     <div className="system-map-grid" aria-hidden="true"/>
     <svg className="organic-connectors" viewBox="0 0 1200 500" preserveAspectRatio="none" aria-hidden="true">
       <path className="route route-main" d="M150 255 C205 255 220 142 290 142 S465 145 555 232"/>
       <path className="route route-one" d="M645 225 C700 165 720 82 775 82"/>
       <path className="route route-two" d="M650 230 C735 205 785 170 860 170"/>
       <path className="route route-three" d="M648 238 C710 275 725 300 775 315"/>
       <path className="route route-four" d="M640 244 C710 330 785 400 865 400"/>
       <path className="route route-review" d="M920 82 C1010 92 995 222 1050 250 M1008 170 C1040 185 1025 230 1050 250 M920 315 C1000 310 1005 270 1050 250 M1012 400 C1050 365 1028 290 1050 250"/>
       <circle className="route-packet packet-main" r="4"><animateMotion dur="3.2s" repeatCount="indefinite" path="M150 255 C205 255 220 142 290 142 S465 145 555 232"/></circle>
       <circle className="route-packet packet-one" r="3"><animateMotion begin="1.6s" dur="2.4s" repeatCount="indefinite" path="M645 225 C700 165 720 82 775 82"/></circle>
       <circle className="route-packet packet-two" r="3"><animateMotion begin="2.1s" dur="2.4s" repeatCount="indefinite" path="M650 230 C735 205 785 170 860 170"/></circle>
       <circle className="route-packet packet-three" r="3"><animateMotion begin="2.6s" dur="2.4s" repeatCount="indefinite" path="M648 238 C710 275 725 300 775 315"/></circle>
       <circle className="route-packet packet-four" r="3"><animateMotion begin="3.1s" dur="2.4s" repeatCount="indefinite" path="M640 244 C710 330 785 400 865 400"/></circle>
       <circle className="route-packet packet-outcome" r="3.5"><animateMotion begin="3.8s" dur="2.1s" repeatCount="indefinite" path="M920 82 C1010 92 995 222 1050 250"/></circle>
       <circle className="route-packet packet-outcome" r="3.5"><animateMotion begin="4.25s" dur="2.1s" repeatCount="indefinite" path="M1008 170 C1040 185 1025 230 1050 250"/></circle>
       <circle className="route-packet packet-outcome" r="3.5"><animateMotion begin="4.7s" dur="2.1s" repeatCount="indefinite" path="M920 315 C1000 310 1005 270 1050 250"/></circle>
       <circle className="route-packet packet-outcome" r="3.5"><animateMotion begin="5.15s" dur="2.1s" repeatCount="indefinite" path="M1012 400 C1050 365 1028 290 1050 250"/></circle>
     </svg>
     <div className="system-lane-label"><span>LIVE SYSTEM WALKTHROUGH</span><i/><button onClick={()=>setPaused(value=>!value)}>{paused?<Play/>:<Pause/>}{paused?'Resume':'Pause'}</button></div>
     <div className="system-source system-node"><span>01 · INPUT</span><Database/><strong>Applicant</strong><small>10 validated features</small></div>
     <div className="system-path path-a"><i/></div>
     <div className="system-primary system-node"><span>02 · DECISION</span><CircleGauge/><strong>Primary model</strong><small>Risk compared with threshold</small><b>APPROVE / REJECT</b></div>
     <div className="system-path path-b"><i/></div>
     <div className="system-core"><div className="core-radar"><i/><i/><i/></div><span>03</span><strong>VerdictLens</strong><small>Runs evidence checks</small></div>
     <div className="system-checks">{checks.map(({code,label,Icon},index)=><button key={code} className={active===index?'is-active':''} onClick={()=>{setActive(index);setPaused(true)}} aria-pressed={active===index}><span>{code}</span><Icon/><strong>{label}</strong><i/></button>)}</div>
     <div className="system-path path-c"><i/></div>
     <div className="system-review system-node"><span>04 · OUTCOME</span><UserCheck/><strong>Stable or review</strong><small>Human review when signals are found</small><b>DECISION UNCHANGED</b></div>
     <div className="system-readout" key={selected.code}><div className="readout-icon"><SelectedIcon/></div><div><span>NOW CHECKING · {selected.code} / 04</span><h3>{selected.label}</h3><p>{selected.short}</p><div>{selected.tags.map(tag=><small key={tag}>{tag}</small>)}</div></div><strong>{paused?'SELECTED':'AUTO LOOP'}</strong></div>
   </section>

   <section className="deep-dive">
     <div className="deep-dive-heading"><div><span className="eyebrow">INSIDE ONE AUDIT</span><h3>From model output to reviewable evidence</h3><p>The complete data path, including what each stage adds to the final result.</p></div><span className="deep-badge">DETERMINISTIC PIPELINE</span></div>
     <div className="audit-anatomy">
       <article className="anatomy-row"><div className="anatomy-index"><span>01</span><i/></div><div className="anatomy-copy"><small>PRIMARY RECORD</small><h4>Preserve exactly what the original model decided.</h4><p>Before VerdictLens performs any check, it captures the XGBoost output unchanged. This becomes the reference point for every comparison that follows.</p></div><div className="anatomy-data primary-data"><div><span>Risk estimate</span><strong>Model probability</strong></div><div><span>Policy threshold</span><strong>Decision boundary</strong></div><div><span>Decision</span><strong>APPROVE / REJECT</strong></div><div><span>Signed margin</span><strong>Distance from cutoff</strong></div></div></article>
       <article className="anatomy-row"><div className="anatomy-index"><span>02</span><i/></div><div className="anatomy-copy"><small>EVIDENCE COLLECTION</small><h4>Ask four different questions about stability.</h4><p>The checks run independently around the primary result. Each one tests a different source of uncertainty without altering the original score.</p></div><div className="anatomy-checks"><div><GitCompareArrows/><span><strong>Would another model agree?</strong><small>Logistic regression and random forest</small></span></div><div><SlidersHorizontal/><span><strong>Would a nearby threshold change it?</strong><small>Five policy-boundary probes</small></span></div><div><Zap/><span><strong>Would a small input change flip it?</strong><small>Controlled local sensitivity tests</small></span></div><div><ScanSearch/><span><strong>Can the inputs be trusted?</strong><small>Missing, unusual, and ambiguous values</small></span></div></div></article>
       <article className="anatomy-row"><div className="anatomy-index"><span>03</span><i/></div><div className="anatomy-copy"><small>RULE EVALUATION</small><h4>Convert observed evidence into named signals.</h4><p>The rule layer is explicit and traceable. A flag identifies which configured check raised concern; it does not claim that the decision is wrong.</p></div><div className="anatomy-flags"><span><i/>MODEL POLICY DISAGREEMENT</span><span><i/>COMMON THRESHOLD DISAGREEMENT</span><span><i/>THRESHOLD SENSITIVE</span><span><i/>INPUT SENSITIVE</span><span><i/>INPUT QUALITY REVIEW</span></div></article>
       <article className="anatomy-row final-row"><div className="anatomy-index"><span>04</span></div><div className="anatomy-copy"><small>REVIEW HANDOFF</small><h4>Return one result that keeps decision and evidence together.</h4><p>A reviewer receives the untouched primary decision, the audit status, every flag, and the evidence behind each signal. Human context remains the final step.</p></div><div className="anatomy-result"><div><span>primary</span><strong>Original output</strong></div><div><span>status</span><strong>REVIEW or STABLE</strong></div><div><span>flags</span><strong>Named signals</strong></div><div><span>evidence</span><strong>Complete trace</strong></div><footer><UserCheck/><span>Ready for informed human review</span></footer></div></article>
     </div>
   </section>

   <section className="how-v2-boundary"><div><span className="eyebrow">WHAT THE RESULT MEANS</span><h3>A review flag is a question,<br/>not a verdict.</h3></div><div className="boundary-points"><p><Check/><span><strong>VerdictLens can show</strong> disagreement, sensitivity, and questionable inputs.</span></p><p><AlertTriangle/><span><strong>VerdictLens cannot prove</strong> correctness, fairness, causality, or legal compliance.</span></p></div></section>

   <div className="how-v2-actions"><button className="button button-primary" onClick={()=>onNavigate('new')}><Play/>Run an audit</button><button className="button button-ghost" onClick={()=>onNavigate('about')}>Read limitations <ArrowRight/></button></div>
 </div>
}
