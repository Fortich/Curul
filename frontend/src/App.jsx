import { useState, useMemo } from "react";
import { useData } from "./useData";
import { fmt, initials, displayName, shortName, avatarCol, fmtDate, ago, tagColors } from "./utils";

// ============================================================
// COMPONENTS
// ============================================================

const Tag = ({ tag, onClick, active, size="sm" }) => {
  const c = tagColors(tag);
  const s = size==="md"?{padding:"6px 16px",fontSize:"13px"}:{padding:"4px 12px",fontSize:"11px"};
  return <span onClick={onClick} style={{display:"inline-flex",alignItems:"center",borderRadius:"100px",cursor:onClick?"pointer":"default",fontFamily:"'DM Sans',sans-serif",fontWeight:500,letterSpacing:"0.01em",whiteSpace:"nowrap",transition:"all 0.2s",background:c.bg,color:c.text,border:active?`2px solid ${c.text}`:"2px solid transparent",opacity:active===false?0.4:1,...s}}>{tag}</span>;
};

const IdeaCard = ({ idea, onSenatorClick, delay=0, youtubeUrl }) => {
  const [open, setOpen] = useState(false);
  const ac = avatarCol(idea.congressman_name);
  return (
    <div style={{background:"var(--card-bg)",borderRadius:"16px",padding:"20px",marginBottom:"12px",border:"1px solid var(--border)",animation:`fadeIn .4s ease ${delay}s both`,transition:"border-color .2s"}}
      onMouseEnter={e=>e.currentTarget.style.borderColor="var(--accent)"} onMouseLeave={e=>e.currentTarget.style.borderColor="var(--border)"}>
      <div style={{display:"flex",alignItems:"center",gap:"12px",marginBottom:"12px"}}>
        <div onClick={()=>onSenatorClick?.(idea.congressman_name)} style={{width:40,height:40,borderRadius:"50%",background:ac,display:"flex",alignItems:"center",justifyContent:"center",color:"#fff",fontWeight:700,fontSize:"13px",fontFamily:"'DM Sans',sans-serif",cursor:onSenatorClick?"pointer":"default",flexShrink:0}}>{initials(idea.congressman_name)}</div>
        <div style={{flex:1,minWidth:0}}>
          <div onClick={()=>onSenatorClick?.(idea.congressman_name)} style={{fontFamily:"'Instrument Serif',serif",fontSize:"16px",color:"var(--text-primary)",cursor:onSenatorClick?"pointer":"default",lineHeight:1.2}}>{displayName(idea.congressman_name)}</div>
          <div style={{fontFamily:"'DM Sans',sans-serif",fontSize:"11px",color:"var(--text-tertiary)",marginTop:"2px"}}>{fmt(idea.start)} – {fmt(idea.end)}</div>
        </div>
        <div style={{width:8,height:8,borderRadius:"50%",flexShrink:0,background:idea.importance>=.7?"#f59e0b":idea.importance>=.5?"var(--text-tertiary)":"var(--border)"}} title={`Relevancia: ${idea.importance}`}/>
      </div>
      <p style={{fontFamily:"'DM Sans',sans-serif",fontSize:"14px",color:"var(--text-primary)",lineHeight:1.6,margin:"0 0 12px"}}>{idea.summary}</p>
      <div style={{display:"flex",flexWrap:"wrap",gap:"6px"}}>{idea.tags.map(t=><Tag key={t} tag={t}/>)}</div>
      <div onClick={()=>setOpen(!open)} style={{marginTop:"12px",cursor:"pointer",fontFamily:"'DM Sans',sans-serif",fontSize:"12px",color:"var(--accent)",fontWeight:500,display:"flex",alignItems:"center",gap:"4px"}}>
        {open?"Ocultar cita":"Ver cita textual"}
        <span style={{display:"inline-block",transition:"transform .2s",transform:open?"rotate(180deg)":"none"}}>▾</span>
      </div>
      {open && (
        <div style={{marginTop:"12px",padding:"16px",background:"var(--quote-bg)",borderRadius:"12px",borderLeft:"3px solid var(--accent)",animation:"fadeIn .3s ease both"}}>
          <p style={{fontFamily:"'Instrument Serif',serif",fontSize:"14px",color:"var(--text-secondary)",lineHeight:1.7,margin:0,fontStyle:"italic"}}>«{idea.quote}»</p>
          {youtubeUrl&&<a href={`${youtubeUrl}&t=${Math.floor(idea.start)}`} target="_blank" rel="noopener noreferrer" style={{display:"inline-flex",alignItems:"center",gap:"5px",marginTop:"12px",fontFamily:"'DM Sans',sans-serif",fontSize:"12px",color:"var(--accent)",fontWeight:500,textDecoration:"none",opacity:.85,transition:"opacity .2s"}} onMouseEnter={e=>e.currentTarget.style.opacity=1} onMouseLeave={e=>e.currentTarget.style.opacity=.85}>▶ Ver en YouTube · {fmt(idea.start)}</a>}
          {idea.mentions.length>0&&<div style={{marginTop:"12px",display:"flex",flexWrap:"wrap",gap:"6px"}}>{idea.mentions.map((m,i)=><span key={i} style={{fontFamily:"'DM Sans',sans-serif",fontSize:"10px",color:"var(--text-tertiary)",background:"var(--border)",padding:"2px 8px",borderRadius:"4px"}}>{m.entity}</span>)}</div>}
        </div>
      )}
    </div>
  );
};

const SessionCard = ({ session, count, senators, onClick, delay=0, isLatest=false }) => {
  const title = "Sesión Plenaria";
  const date = session.date ?? "";
  const recent = isLatest || (date && (new Date()-new Date(date+"T12:00:00"))<7*864e5);
  return (
    <div onClick={onClick} style={{background:"var(--card-bg)",borderRadius:"16px",padding:"20px",marginBottom:"12px",border:"1px solid var(--border)",cursor:"pointer",transition:"all .2s",animation:`fadeIn .4s ease ${delay}s both`,position:"relative",overflow:"hidden"}}
      onMouseEnter={e=>{e.currentTarget.style.borderColor="var(--accent)";e.currentTarget.style.transform="translateY(-2px)";}}
      onMouseLeave={e=>{e.currentTarget.style.borderColor="var(--border)";e.currentTarget.style.transform="none";}}>
      <div style={{position:"absolute",top:0,left:0,right:0,height:"3px",background:recent?"var(--accent)":"var(--border)"}}/>
      <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:"8px"}}>
        <div style={{display:"flex",alignItems:"center",gap:"8px"}}>
          {recent&&<span style={{fontSize:"9px",fontWeight:700,color:"#0D0D0F",background:"var(--accent)",padding:"2px 8px",borderRadius:"4px",textTransform:"uppercase",letterSpacing:".08em"}}>Nueva</span>}
          {date&&<span style={{fontSize:"11px",color:"var(--text-tertiary)"}}>{ago(date)}</span>}
        </div>
        <span style={{color:"var(--text-tertiary)",fontSize:"18px"}}>›</span>
      </div>
      <h3 style={{fontFamily:"'Instrument Serif',serif",fontSize:"20px",color:"var(--text-primary)",marginBottom:"4px",lineHeight:1.3}}>{title}</h3>
      {date&&<p style={{fontSize:"13px",color:"var(--accent)",fontWeight:600,marginBottom:"10px",opacity:.9}}>{fmtDate(date)}</p>}
      <p style={{fontSize:"13px",color:"var(--text-secondary)",lineHeight:1.6,marginBottom:"14px",display:"-webkit-box",WebkitLineClamp:3,WebkitBoxOrient:"vertical",overflow:"hidden"}}>{session.summary}</p>
      <div style={{display:"flex",gap:"16px",fontSize:"12px",color:"var(--text-tertiary)"}}>
        <span>{senators} senadores</span><span>·</span><span>{count} intervenciones</span>
      </div>
    </div>
  );
};

const SenatorRow = ({ name, count, sessions, onClick, delay=0 }) => (
  <div onClick={onClick} style={{display:"flex",alignItems:"center",gap:"14px",padding:"14px 16px",background:"var(--card-bg)",borderRadius:"14px",cursor:"pointer",border:"1px solid var(--border)",transition:"all .2s",animation:`fadeIn .35s ease ${delay}s both`}}
    onMouseEnter={e=>{e.currentTarget.style.borderColor="var(--accent)";e.currentTarget.style.transform="translateX(4px)";}}
    onMouseLeave={e=>{e.currentTarget.style.borderColor="var(--border)";e.currentTarget.style.transform="none";}}>
    <div style={{width:42,height:42,borderRadius:"50%",background:avatarCol(name),display:"flex",alignItems:"center",justifyContent:"center",color:"#fff",fontWeight:700,fontSize:"14px",fontFamily:"'DM Sans',sans-serif",flexShrink:0}}>{initials(name)}</div>
    <div style={{flex:1}}>
      <div style={{fontFamily:"'Instrument Serif',serif",fontSize:"16px",color:"var(--text-primary)"}}>{displayName(name)}</div>
      {sessions>1&&<div style={{fontSize:"11px",color:"var(--text-tertiary)",marginTop:"2px"}}>en {sessions} sesiones</div>}
    </div>
    <div style={{fontSize:"12px",color:"var(--text-tertiary)",background:"var(--border)",padding:"4px 10px",borderRadius:"100px"}}>{count}</div>
    <span style={{color:"var(--text-tertiary)",fontSize:"16px"}}>›</span>
  </div>
);

const Back = ({ label, onClick }) => <button onClick={onClick} style={{display:"flex",alignItems:"center",gap:"6px",background:"none",border:"none",cursor:"pointer",fontFamily:"'DM Sans',sans-serif",fontSize:"13px",color:"var(--accent)",fontWeight:600,padding:0,marginBottom:"16px"}}>‹ {label||"Volver"}</button>;

// ============================================================
// APP
// ============================================================

export default function CurulApp() {
  const { sessions, ideas: ideasData, loading } = useData();
  const [nav, setNav] = useState([{ view:"home" }]);
  const current = nav[nav.length-1];

  const push = (v) => { setNav(prev=>[...prev,v]); window.scrollTo({top:0}); };
  const pop = () => { setNav(prev=>prev.length>1?prev.slice(0,-1):[{view:"home"}]); window.scrollTo({top:0}); };

  const allSenators = useMemo(() => {
    const m={};
    ideasData.forEach(i=>{if(!m[i.congressman_name])m[i.congressman_name]={count:0,sessions:new Set()};m[i.congressman_name].count++;m[i.congressman_name].sessions.add(i.session);});
    return Object.entries(m).map(([n,d])=>({name:n,count:d.count,sessions:d.sessions.size})).sort((a,b)=>b.count-a.count);
  },[ideasData]);

  const globalTags = useMemo(() => {
    const m={}; ideasData.forEach(i=>i.tags.forEach(t=>{m[t]=(m[t]||0)+1;}));
    return Object.entries(m).sort((a,b)=>b[1]-a[1]);
  },[ideasData]);

  const getIdeas = (opts={}) => {
    let ideas = ideasData;
    if(opts.session) ideas = ideas.filter(i=>i.session===opts.session);
    if(opts.senator) ideas = ideas.filter(i=>i.congressman_name===opts.senator);
    if(opts.tag) ideas = ideas.filter(i=>i.tags.includes(opts.tag));
    return ideas;
  };

  if(loading) return <div style={{minHeight:"100vh",background:"#0D0D0F",display:"flex",alignItems:"center",justifyContent:"center",fontFamily:"'DM Sans',sans-serif",color:"#6B6B76",fontSize:"14px"}}>Cargando…</div>;

  return (
    <div style={{minHeight:"100vh",background:"var(--bg)",fontFamily:"'DM Sans',sans-serif"}}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Instrument+Serif:ital@0;1&display=swap');
        :root{--bg:#0D0D0F;--card-bg:#16161A;--border:#2A2A30;--accent:#F5C518;--text-primary:#EAEAEC;--text-secondary:#B0B0B8;--text-tertiary:#6B6B76;--quote-bg:#1C1C22;}
        @keyframes fadeIn{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
        *{box-sizing:border-box;margin:0;padding:0}body{background:var(--bg)}
        ::-webkit-scrollbar{width:6px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}
      `}</style>

      <header style={{padding:"20px 20px 0",maxWidth:"640px",margin:"0 auto"}}>
        <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginBottom:"6px"}}>
          <h1 onClick={()=>setNav([{view:"home"}])} style={{fontFamily:"'Instrument Serif',serif",fontSize:"32px",color:"var(--accent)",cursor:"pointer",letterSpacing:"-0.02em",lineHeight:1}}>Curul</h1>
          <span style={{fontSize:"10px",color:"var(--text-tertiary)",textTransform:"uppercase",letterSpacing:".1em",fontWeight:600,background:"var(--card-bg)",padding:"4px 10px",borderRadius:"4px",border:"1px solid var(--border)"}}>Senado de Colombia</span>
        </div>
        <p style={{fontSize:"13px",color:"var(--text-tertiary)",lineHeight:1.5,paddingBottom:"16px",borderBottom:"1px solid var(--border)"}}>Lo que dicen tus senadores, en sus propias palabras.</p>
      </header>

      <main style={{maxWidth:"640px",margin:"0 auto",padding:"20px"}}>

        {/* HOME */}
        {current.view==="home"&&(<>
          <div style={{marginBottom:"28px"}}>
            <h3 style={{fontFamily:"'Instrument Serif',serif",fontSize:"20px",color:"var(--text-primary)",marginBottom:"14px",display:"flex",alignItems:"center",gap:"8px"}}><span style={{color:"var(--accent)",fontSize:"16px"}}>■</span>Sesiones plenarias</h3>
            {sessions.map((s,i)=>{const ideas=getIdeas({session:s.session});return<SessionCard key={s.session} session={s} count={ideas.length} senators={new Set(ideas.map(x=>x.congressman_name)).size} onClick={()=>push({view:"session",session:s.session})} delay={.06*i} isLatest={i===0}/>;
            })}
            <div style={{textAlign:"center",padding:"16px",fontSize:"12px",color:"var(--text-tertiary)",fontStyle:"italic",animation:"fadeIn .4s ease .3s both"}}>Más sesiones pronto — procesando el archivo histórico</div>
          </div>

          <div style={{marginBottom:"28px"}}>
            <h3 style={{fontFamily:"'Instrument Serif',serif",fontSize:"20px",color:"var(--text-primary)",marginBottom:"14px",display:"flex",alignItems:"center",gap:"8px"}}><span style={{color:"var(--accent)",fontSize:"16px"}}>■</span>Senadores</h3>
            <div style={{display:"flex",flexDirection:"column",gap:"8px"}}>
              {allSenators.map((s,i)=><SenatorRow key={s.name} name={s.name} count={s.count} sessions={s.sessions} onClick={()=>push({view:"senator",senator:s.name})} delay={.04*i}/>)}
            </div>
          </div>

          <div>
            <h3 style={{fontFamily:"'Instrument Serif',serif",fontSize:"20px",color:"var(--text-primary)",marginBottom:"14px",display:"flex",alignItems:"center",gap:"8px"}}><span style={{color:"var(--accent)",fontSize:"16px"}}>■</span>Temas</h3>
            <div style={{display:"flex",flexWrap:"wrap",gap:"8px"}}>
              {globalTags.map(([t,c],i)=><span key={t} onClick={()=>push({view:"theme",tag:t})} style={{cursor:"pointer",animation:`fadeIn .35s ease ${.03*i}s both`}}><Tag tag={t} size="md"/></span>)}
            </div>
          </div>
        </>)}

        {/* SESSION */}
        {current.view==="session"&&(()=>{
          const s=sessions.find(x=>x.session===current.session);
          const title = "Sesión Plenaria";
          const date = s?.date ?? "";
          const ideas=getIdeas({session:current.session}).sort((a,b)=>a.start-b.start);
          const tags={}; ideas.forEach(i=>i.tags.forEach(t=>{tags[t]=(tags[t]||0)+1;}));
          return<>
            <Back label="Sesiones" onClick={pop}/>
            <h2 style={{fontFamily:"'Instrument Serif',serif",fontSize:"24px",color:"var(--text-primary)",marginBottom:"4px"}}>{title}</h2>
            {date&&<p style={{fontSize:"14px",color:"var(--accent)",fontWeight:600,marginBottom:"8px"}}>{fmtDate(date)}</p>}
            <p style={{fontSize:"13px",color:"var(--text-secondary)",lineHeight:1.6,marginBottom:"16px"}}>{s?.summary}</p>
            <div style={{display:"flex",flexWrap:"wrap",gap:"6px",marginBottom:"20px"}}>{Object.entries(tags).sort((a,b)=>b[1]-a[1]).map(([t])=><Tag key={t} tag={t} size="sm" onClick={()=>push({view:"theme",tag:t,session:current.session})}/>)}</div>
            <div style={{fontSize:"12px",color:"var(--text-tertiary)",marginBottom:"16px"}}>{ideas.length} intervenciones · orden cronológico</div>
            {ideas.map((idea,i)=><IdeaCard key={i} idea={idea} onSenatorClick={n=>push({view:"senator",senator:n})} delay={.04*i} youtubeUrl={s?.youtube_url}/>)}
          </>;
        })()}

        {/* SENATOR */}
        {current.view==="senator"&&(()=>{
          const ideas=getIdeas({senator:current.senator}).sort((a,b)=>a.start-b.start);
          const sessionIds=[...new Set(ideas.map(i=>i.session))];
          return<>
            <Back label="Volver" onClick={pop}/>
            <div style={{display:"flex",alignItems:"center",gap:"14px",marginBottom:"20px"}}>
              <div style={{width:52,height:52,borderRadius:"50%",background:avatarCol(current.senator),display:"flex",alignItems:"center",justifyContent:"center",color:"#fff",fontWeight:700,fontSize:"18px",fontFamily:"'DM Sans',sans-serif"}}>{initials(current.senator)}</div>
              <div>
                <h2 style={{fontFamily:"'Instrument Serif',serif",fontSize:"22px",color:"var(--text-primary)",lineHeight:1.2}}>{displayName(current.senator)}</h2>
                <p style={{fontSize:"12px",color:"var(--text-tertiary)",marginTop:"4px"}}>{ideas.length} intervención{ideas.length!==1?"es":""}{sessionIds.length>1?` en ${sessionIds.length} sesiones`:""}</p>
              </div>
            </div>
            {sessionIds.length>1?sessionIds.map(sid=>{
              const si=ideas.filter(i=>i.session===sid);
              const date=sessions.find(x=>x.session===sid)?.date ?? "";
              return<div key={sid} style={{marginBottom:"24px"}}>
                <div onClick={()=>push({view:"session",session:sid})} style={{fontSize:"12px",fontWeight:600,color:"var(--accent)",marginBottom:"12px",paddingBottom:"8px",borderBottom:"1px solid var(--border)",textTransform:"uppercase",letterSpacing:".06em",cursor:"pointer"}}>{date?fmtDate(date):sid}</div>
                {si.map((idea,i)=><IdeaCard key={i} idea={idea} delay={.04*i} youtubeUrl={sessions.find(x=>x.session===sid)?.youtube_url}/>)}
              </div>;
            }):ideas.map((idea,i)=><IdeaCard key={i} idea={idea} delay={.05*i} youtubeUrl={sessions.find(x=>x.session===idea.session)?.youtube_url}/>)}
          </>;
        })()}

        {/* THEME */}
        {current.view==="theme"&&(()=>{
          const ideas=getIdeas({tag:current.tag,session:current.session}).sort((a,b)=>b.importance-a.importance);
          const who={}; ideas.forEach(i=>{who[i.congressman_name]=(who[i.congressman_name]||0)+1;});
          return<>
            <Back label="Volver" onClick={pop}/>
            <div style={{marginBottom:"20px"}}>
              <Tag tag={current.tag} size="md"/>
              <p style={{fontSize:"13px",color:"var(--text-tertiary)",marginTop:"10px"}}>{ideas.length} intervención{ideas.length!==1?"es":""}{current.session?"":" en todas las sesiones"}</p>
              {Object.keys(who).length>1&&<div style={{marginTop:"12px",display:"flex",flexWrap:"wrap",gap:"6px"}}>
                {Object.entries(who).sort((a,b)=>b[1]-a[1]).map(([n])=><span key={n} onClick={()=>push({view:"senator",senator:n})} style={{fontSize:"11px",color:"var(--text-secondary)",background:"var(--card-bg)",border:"1px solid var(--border)",padding:"4px 10px",borderRadius:"100px",cursor:"pointer",transition:"border-color .2s"}}
                  onMouseEnter={e=>e.currentTarget.style.borderColor="var(--accent)"} onMouseLeave={e=>e.currentTarget.style.borderColor="var(--border)"}>{shortName(n)}</span>)}
              </div>}
            </div>
            {ideas.map((idea,i)=><IdeaCard key={i} idea={idea} onSenatorClick={n=>push({view:"senator",senator:n})} delay={.04*i} youtubeUrl={sessions.find(x=>x.session===idea.session)?.youtube_url}/>)}
          </>;
        })()}

        <footer style={{marginTop:"40px",paddingTop:"20px",borderTop:"1px solid var(--border)",textAlign:"center"}}>
          <p style={{fontSize:"11px",color:"var(--text-tertiary)",lineHeight:1.6}}>Curul — Transparencia legislativa para Colombia<br/>Datos extraídos de sesiones plenarias del Senado</p>
        </footer>
      </main>
    </div>
  );
}