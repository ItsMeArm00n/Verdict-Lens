'use client'

import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, Database, GitCompareArrows, ScanSearch, SlidersHorizontal, UserCheck, Zap } from 'lucide-react'

const checks = [
  { code:'MODEL', title:'Model comparison', note:'LR + RF challengers', Icon:GitCompareArrows },
  { code:'POLICY', title:'Threshold tests', note:'Nearby boundaries', Icon:SlidersHorizontal },
  { code:'INPUT', title:'Input probes', note:'Controlled variations', Icon:Zap },
  { code:'QUALITY', title:'Data quality', note:'Range + completeness', Icon:ScanSearch },
]

export function EvidenceArchitecture(){
  const ref=useRef<HTMLDivElement>(null)
  const [active,setActive]=useState(0)
  const [visible,setVisible]=useState(false)
  const [paused,setPaused]=useState(false)

  useEffect(()=>{const element=ref.current;if(!element)return;const observer=new IntersectionObserver(([entry])=>setVisible(entry.isIntersecting),{threshold:.35});observer.observe(element);return()=>observer.disconnect()},[])
  useEffect(()=>{if(!visible||paused||window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;const timer=setInterval(()=>setActive(value=>(value+1)%checks.length),2100);return()=>clearInterval(timer)},[visible,paused])

  return <div className={`evidence-map ${visible?'is-live':''}`} ref={ref} onMouseEnter={()=>setPaused(true)} onMouseLeave={()=>setPaused(false)}>
    <div className="map-grid" aria-hidden="true"/>
    <div className="map-origin map-card">
      <span className="map-step">01 · SOURCE</span><Database/><strong>Applicant record</strong><small>10 validated features</small>
    </div>
    <div className="map-primary map-card">
      <span className="map-step">02 · ORIGINAL</span><span className="map-model">XG</span><strong>Primary decision</strong><small>Score + fixed threshold</small>
    </div>
    <div className="map-trunk first" aria-hidden="true"><i/></div>
    <div className="map-trunk second" aria-hidden="true"><i/></div>
    <div className="map-hub">
      <span className="hub-orbit orbit-one"/><span className="hub-orbit orbit-two"/>
      <div className="hub-core"><span>03</span><strong>VerdictLens</strong><small>Evidence engine</small></div>
    </div>
    <div className="map-branches" aria-label="Four independent audit checks">
      {checks.map(({code,title,note,Icon},index)=><button type="button" className={`map-check ${active===index?'is-active':''}`} key={code} onClick={()=>{setActive(index);setPaused(true)}}>
        <span className="check-index">0{index+1}</span><Icon/><span><strong>{title}</strong><small>{note}</small></span><i className="check-signal" aria-hidden="true"/>
      </button>)}
    </div>
    <div className="map-review map-card">
      <span className="map-step">04 · OUTCOME</span><UserCheck/><strong>Human review</strong><small>Evidence-informed, never overridden</small><CheckCircle2 className="review-check"/>
    </div>
    <div className="map-status" aria-live="polite"><span>INSPECTING</span><strong>{checks[active].title}</strong><i><b style={{width:`${(active+1)*25}%`}}/></i><small>0{active+1} / 04</small></div>
  </div>
}

