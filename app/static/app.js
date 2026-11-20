/* Alignly is a zero-build, framework-free frontend. All resume contents are treated as text. */
const SECTION_NAMES = {summary:'Professional summary',experience:'Work experience',skills:'Skills & tools',projects:'Projects',education:'Education',achievements:'Achievements',certifications:'Certifications',additional:'Additional info'};
const SECTION_ORDER = ['summary','skills','experience','projects','education','achievements','certifications','additional'];
const CONTACT_NAMES = {name:'Full name',headline:'Professional headline',email:'Email address',phone:'Phone number',location:'Location',links:'LinkedIn / GitHub / website'};
const $ = id => document.getElementById(id);
const esc = value => String(value??'').replace(/[&<>"']/g, x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x]));
const createResume = () => ({name:'',headline:'',email:'',phone:'',location:'',links:'',sections:Object.fromEntries(Object.keys(SECTION_NAMES).map(x=>[x,'']))});
const state = {view:'tailor', resume:createResume(), template:'modern', selected:new Set(['summary','experience','skills','projects','achievements']), provider:'gemini', analysis:null, proposed:{}, warnings:{}, decided:{}, wizardStep:0, builderAnswers:{}, versions:[], hasGemini:false, jd:'', filename:''};

const WIZARD = [
 {title:'First, the essentials.',sub:'How would you like employers to know and reach you?',fields:[['name','Your full name','text','e.g. Jordan Lee'],['headline','Your professional headline','text','e.g. Backend Software Engineer'],['email','Email address','email','jordan@example.com'],['phone','Phone number','text','+1 (555) 010-1234'],['location','Location','text','e.g. Phoenix, AZ'],['links','Links / portfolio','text','linkedin.com/in/... · github.com/...']]},
 {title:'Tell your professional story.',sub:'A brief summary of what you do well and where you want to grow.',fields:[['summary','About you / professional summary','textarea','e.g. Software engineer with hands-on experience building API integrations and data workflows.'],['specialty','What do you want to be known for?','text','e.g. Strong problem solving, frontend development (only if true)']]},
 {title:'Showcase your real work.',sub:'Add employers, role titles, dates, responsibilities, and results. Use one line per item.',fields:[['experience','Work history / job titles / dates','textarea','Example:\nSoftware Engineer | Company | May 2024 – Present\n- Built REST APIs for internal dashboards\n- Reduced page load time by 20% (if measured)'],['impact','More experience details (optional)','textarea','Add additional jobs or bullet points. Keep exact dates and metrics.']]},
 {title:'What tools are in your toolkit?',sub:'List the technical and interpersonal skills you can genuinely demonstrate.',fields:[['technical','Technical skills','textarea','e.g. Python, JavaScript, SQL, REST APIs, Git, Salesforce Apex'],['soft','Collaboration and other skills','textarea','e.g. Agile delivery, documentation, stakeholder communication']]},
 {title:'Tell us about your projects.',sub:'Personal, academic, volunteer, or professional projects all count when accurate.',fields:[['projects','Project details','textarea','Example:\nCustomer Support Chatbot | Python, FastAPI\n- Created a retrieval assistant using local embeddings\n\nAnother project | React, Firebase\n- Built a mobile-responsive interface']]},
 {title:'Add your education.',sub:'Include degrees, schools, graduation dates, and relevant coursework if helpful.',fields:[['education','Education history','textarea','e.g. Master of Science in Business Analytics | Arizona State University | 2024']]},
 {title:'Highlight the extras.',sub:'Recognitions, certificates, or trainings can strengthen your story.',fields:[['achievements','Awards and achievements','textarea','e.g. Team recognition for delivering a critical integration'],['certifications','Certifications','textarea','e.g. Salesforce Platform Developer I — 2025']]},
 {title:'Anything else worth sharing?',sub:'Add optional languages, volunteering, or other information.',fields:[['additional','Additional information','textarea','e.g. Languages: English, Spanish\nVolunteer: Coding club mentor']]},
];

function toast(message, kind='info'){
  const box=document.createElement('div'); box.className='toast '+(kind==='error'?'error':kind==='success'?'success':''); box.textContent=message;
  $('toastContainer').appendChild(box); setTimeout(()=>box.remove(),4800);
}
async function api(path,options={}){
  let res; try {res=await fetch('/api/'+path,options)} catch(e){throw new Error('Cannot reach the server. Make sure python run.py is running.');}
  let data; try{data=await res.json()}catch(e){data=null;}
  if(!res.ok){let d=data?.detail; if(Array.isArray(d))d=d.map(e=>e.msg).join('; ');throw new Error(d||('Request failed ('+res.status+')'));}
  return data;
}
function body(resume=state.resume){return {resume,job_description:$('jobDescription').value.trim()};}
function meaningfulResume(resume=state.resume){return !!(resume.name.trim() || Object.values(resume.sections).some(s=>s.trim()));}
function busy(btn,working,verb){if(working){btn.dataset.oldText=btn.innerHTML;btn.innerHTML='◌ &nbsp; '+verb+'…';btn.disabled=true;}else{btn.disabled=false;btn.innerHTML=btn.dataset.oldText||btn.innerHTML;}}

function init(){
  try{const v=JSON.parse(localStorage.getItem('alignly_versions_v1')||'[]');state.versions=Array.isArray(v)?v:[]}catch(e){}
  populateChoices();populateTemplates();renderPreview();renderWizard();renderVersions();bindEvents();getHealth();
}
async function getHealth(){try{const data=await api('health');state.hasGemini=data.gemini_configured;$('apiStatus').innerHTML='<span class="status-dot '+(data.gemini_configured?'ready':'')+'"></span> '+(data.gemini_configured?'Gemini connected':'Gemini key needed');$('providerNote').textContent=data.gemini_configured?'Ready to enhance using '+data.gemini_model+'.':'Add GEMINI_API_KEY in .env; or use local Ollama.'}catch(e){$('apiStatus').textContent='Server unavailable';}}
function view(mode){
  state.view=mode;
  ['tailor','builder','versions'].forEach(name=>{$('view'+name[0].toUpperCase()+name.slice(1)).classList.toggle('hidden',name!==mode);});
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===mode));
  $('topBreadcrumb').textContent={tailor:'Tailor to a job',builder:'Build from scratch',versions:'Saved versions'}[mode];
  if(mode==='builder')renderWizard();if(mode==='versions')renderVersions();renderPreview();
  window.scrollTo({top:0,behavior:'smooth'});
}
function populateChoices(){
  $('sectionPicker').innerHTML=Object.entries(SECTION_NAMES).map(([key,label])=>`<label class="section-choice ${state.selected.has(key)?'selected':''}"><input type="checkbox" data-section="${key}" ${state.selected.has(key)?'checked':''} /><span>${esc(label)}</span></label>`).join('');
}
function setChoice(key,checked){if(checked)state.selected.add(key);else state.selected.delete(key);populateChoices();}
function templateHTML(template,big=false){const label={modern:'Modern',classic:'Classic',compact:'Compact'}[template];const subtitle={modern:'Clean & balanced',classic:'Timeless & simple',compact:'Space-saving'}[template];return big?`<button class="template-option ${state.template===template?'active':''}" data-template="${template}"><span class="template-mini"><b></b><i></i><i></i><i></i></span><span><strong>${label}</strong><small>${subtitle}</small></span></button>`:`<button class="template-swatch ${state.template===template?'active':''}" data-template="${template}"><span class="swatch-drawing"><b></b><i></i><i></i><i></i></span>${label}</button>`;}
function populateTemplates(){for(const dest of ['previewTemplates','builderTemplates'])$(dest).innerHTML=['modern','classic','compact'].map(x=>templateHTML(x,dest==='builderTemplates')).join('');}
function setTemplate(template){state.template=template;populateTemplates();renderPreview();}
function currentPreviewResume(){return state.view==='builder'?buildFromAnswers():state.resume;}
function renderPreview(){
  const resume=currentPreviewResume();const paper=$('resumePreview'); paper.className='resume-paper '+state.template;
  $('previewDraftBadge').textContent=meaningfulResume(resume)?'· Editing':'· Draft';
  if(!meaningfulResume(resume)) {paper.innerHTML='<div class="paper-empty"><div class="paper-empty-icon">▤</div><strong>Your story goes here</strong><p>Upload a resume or answer the guided questions to see a live preview.</p></div>';return;}
  const contact=[resume.email,resume.phone,resume.location,resume.links].filter(Boolean).map(esc).join(' · ');
  const sections=SECTION_ORDER.filter(key=>resume.sections[key]?.trim()).map(key=>{
    const lines=resume.sections[key].split('\n').map(x=>x.trim()).filter(Boolean);
    return `<section class="paper-section"><h4>${esc(SECTION_NAMES[key]).toUpperCase()}</h4>${lines.map(l=>`<p class="${/^[-*•]\s/.test(l)?'bullet':''}">${esc(l)}</p>`).join('')}</section>`;
  }).join('');
  paper.innerHTML=`<div class="paper-name">${esc(resume.name||'YOUR NAME')}</div>${resume.headline?`<div class="paper-headline">${esc(resume.headline)}</div>`:''}${contact?`<div class="paper-contact">${contact}</div>`:''}<div class="paper-divider"></div>${sections}`;
}
async function parseFile(file,kind){
  if(!file)return;if(file.size>5*1024*1024){toast('Files must be 5 MB or smaller.','error');return;}
  const form=new FormData();form.append('file',file);
  try{
    const result=await api(kind==='resume'?'parse':'extract-jd',{method:'POST',body:form});
    if(kind==='resume'){
      state.resume=result.resume;state.filename=file.name; state.proposed={};state.analysis=null;$('analysisCard').classList.add('hidden');$('reviewCard').classList.add('hidden');
      $('resumeDropzone').classList.add('hidden');$('resumeUploaded').classList.remove('hidden');$('resumeUploadedName').textContent=file.name;$('resumeUploadedSub').textContent=result.characters.toLocaleString()+' text characters extracted';
      toast('Resume imported. Review parsed sections in the editor.','success');renderPreview();
    } else {$('jobDescription').value=result.text;state.jd=result.text;updateJDCount();toast('Job description imported.','success');}
  }catch(e){toast(e.message,'error');}
}
function updateJDCount(){$('jdCount').textContent=$('jobDescription').value.length.toLocaleString()+' characters';}
function fileDrop(target,fileInput,kind){const d=$(target);const inp=$(fileInput);d.addEventListener('click',()=>inp.click());d.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();inp.click();}});d.addEventListener('dragover',e=>{e.preventDefault();d.classList.add('dragover');});d.addEventListener('dragleave',()=>d.classList.remove('dragover'));d.addEventListener('drop',e=>{e.preventDefault();d.classList.remove('dragover');parseFile(e.dataTransfer.files[0],kind);});inp.addEventListener('change',()=>{parseFile(inp.files[0],kind);inp.value='';});}
function analysisHTML(result){
  $('analysisCard').classList.remove('hidden');$('scoreValue').textContent=result.score+'%';$('scoreRing').style.background=`conic-gradient(#2bb88c ${result.score}%,#e8f5ef ${result.score}%)`;
  $('matchedCount').textContent='('+result.matched.length+')';$('missingCount').textContent='('+result.missing.length+')';
  $('matchedKeywords').innerHTML=result.matched.length?result.matched.map(t=>`<span class="chip known">${esc(t)}</span>`).join(''):'<span class="chip none">No matched terms yet</span>';
  $('missingKeywords').innerHTML=result.missing.length?result.missing.map(t=>`<span class="chip missing">${esc(t)}</span>`).join(''):'<span class="chip none">None detected</span>';
  $('analysisTips').innerHTML=result.tips.map(t=>`<div class="tip">${esc(t)}</div>`).join('');
  state.analysis=result;
}
async function analyze(){const req=body();if(!meaningfulResume()){toast('First upload, build, or edit a resume.','error');return;}if(req.job_description.length<30){toast('Paste at least 30 characters of the job description.','error');return;}
  const b=$('analyzeButton');busy(b,true,'Analyzing');try{analysisHTML(await api('analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(req)}));toast('Analysis complete.','success');$('analysisCard').scrollIntoView({behavior:'smooth',block:'nearest'});}catch(e){toast(e.message,'error');}finally{busy(b,false);}
}
async function enhance(){const req=body();if(!meaningfulResume()){toast('Import or create your resume first.','error');return;}if(req.job_description.length<30){toast('Add the job description first (at least 30 characters).','error');return;}if(!state.selected.size){toast('Choose at least one section to enhance.','error');return;}
  const b=$('enhanceButton');busy(b,true,'Generating');try{
    const data=await api('enhance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...req,sections_to_change:[...state.selected],provider:state.provider,custom_instructions:$('customInstructions').value})});
    state.proposed=data.proposed_sections;state.warnings=data.risk_warnings||{};state.decided={};renderReview();analysisHTML(data.updated_alignment);toast('Draft generated. Review each section before accepting.','success');$('reviewCard').scrollIntoView({behavior:'smooth',block:'start'});
  }catch(e){toast(e.message,'error');if(e.message.includes('API key'))openModal('settingsModal');}finally{busy(b,false);}
}
function renderReview(){const keys=Object.keys(state.proposed);if(!keys.length){$('reviewCard').classList.add('hidden');return;}$('reviewCard').classList.remove('hidden');
  $('reviewItems').innerHTML=keys.map(key=>{const status=state.decided[key];return `<article class="review-item"><div class="review-item-title"><strong>${esc(SECTION_NAMES[key])}</strong><span class="review-state">${status==='accepted'?'✓ Accepted':status==='rejected'?'Not applied':'Awaiting your decision'}</span></div><div class="comparison"><div><label>YOUR ORIGINAL</label><pre>${esc(state.originalSections?.[key]??'')}</pre></div><div class="proposed"><label>AI SUGGESTION</label><pre>${esc(state.proposed[key]||'(Empty — no facts to add)')}</pre></div></div><div class="risk-warnings">${(state.warnings[key]||[]).map(w=>`<div class="risk-warning">⚠ ${esc(w)}</div>`).join('')}</div><div class="review-item-footer">${status?`<button class="button light" data-review="reset" data-key="${key}">Reconsider</button>`:`<button class="button secondary" data-review="reject" data-key="${key}">Keep original</button><button class="button primary" data-review="accept" data-key="${key}">✓ Accept edit</button>`}</div></article>`}).join('');
}
function decide(key,decision){if(!state.proposed[key] && state.proposed[key]!=='')return;if(decision==='accepted'){state.resume.sections[key]=state.proposed[key]}else if(decision==='rejected'){state.resume.sections[key]=state.originalSections[key]??'';}else {state.resume.sections[key]=state.originalSections[key]??'';delete state.decided[key];renderReview();renderPreview();return;}state.decided[key]=decision;renderReview();renderPreview();}
function editor(){
  if(state.view==='builder'){state.resume=buildFromAnswers();view('tailor');}
  const c=$('editContact'); c.innerHTML=Object.entries(CONTACT_NAMES).map(([key,label])=>`<div class="edit-field"><label for="e-${key}">${esc(label)}</label><input id="e-${key}" data-contact="${key}" value="${esc(state.resume[key])}" /></div>`).join('');
  $('editSections').innerHTML=Object.entries(SECTION_NAMES).map(([key,label])=>`<div class="edit-section"><label for="e-${key}">${esc(label)}</label><textarea id="e-${key}" data-edit-section="${key}" rows="4" placeholder="Add your ${label.toLowerCase()} here...">${esc(state.resume.sections[key]||'')}</textarea></div>`).join('');
  openModal('editModal');
}
function openModal(id){$(id).classList.remove('hidden');const first=$(id).querySelector('input,button');first?.focus();}
function closeModal(id){$(id).classList.add('hidden');}
function getAnswer(key){return String(state.builderAnswers[key]||'').trim();}
function buildFromAnswers(){const a=getAnswer;const r=createResume();for(const key of Object.keys(CONTACT_NAMES))r[key]=a(key);r.sections.summary=[a('summary'),a('specialty')].filter(Boolean).join('\n');r.sections.experience=[a('experience'),a('impact')].filter(Boolean).join('\n\n');r.sections.skills=[a('technical')?'Technical: '+a('technical'):'',a('soft')?'Additional: '+a('soft'):''].filter(Boolean).join('\n');for(const key of ['projects','education','achievements','certifications','additional'])r.sections[key]=a(key);return r;}
function renderWizard(){const step=WIZARD[state.wizardStep];$('wizardTitle').textContent=step.title;$('wizardSubtitle').textContent=step.sub;$('wizardStepText').textContent='QUESTION '+(state.wizardStep+1)+' OF '+WIZARD.length;const pct=Math.round((state.wizardStep+1)/WIZARD.length*100);$('wizardPct').textContent=pct+'%';$('wizardProgress').style.width=pct+'%';
  $('wizardFields').innerHTML=step.fields.map(([key,label,type,placeholder])=>`<div class="wizard-field"><label for="q-${key}">${esc(label)}</label>${type==='textarea'?`<textarea id="q-${key}" data-answer="${key}" placeholder="${esc(placeholder)}">${esc(getAnswer(key))}</textarea>`:`<input id="q-${key}" data-answer="${key}" type="${type}" value="${esc(getAnswer(key))}" placeholder="${esc(placeholder)}" />`}</div>`).join('');$('wizardBack').disabled=state.wizardStep===0;$('wizardNext').textContent=state.wizardStep===WIZARD.length-1?'✓ Create my resume':'Continue →';
}
function moveWizard(dir){if(dir>0 && state.wizardStep===WIZARD.length-1){const resume=buildFromAnswers();if(!meaningfulResume(resume)){toast('Enter your details before creating your resume.','error');return;}state.resume=resume;state.proposed={};state.analysis=null;$('analysisCard').classList.add('hidden');$('reviewCard').classList.add('hidden');view('tailor');toast('Resume created! Use the editor to refine details or tailor it to a job.','success');return;}
  state.wizardStep=Math.max(0,Math.min(WIZARD.length-1,state.wizardStep+dir));renderWizard();renderPreview();
}
function persistVersions(){try{localStorage.setItem('alignly_versions_v1',JSON.stringify(state.versions));}catch(e){toast('Browser storage is full or unavailable. Export a backup instead.','error');}}
function saveDialog(){if(!meaningfulResume()){toast('Add a resume before saving a version.','error');return;}$('versionName').value=state.resume.headline?state.resume.headline+' — tailored resume':(state.resume.name||'My resume');$('versionNotes').value='';openModal('saveModal');}
function saveVersion(){const name=$('versionName').value.trim();if(!name){toast('Please name the version.','error');return;}state.versions.unshift({id:Date.now().toString()+'-'+Math.floor(Math.random()*100000),name,notes:$('versionNotes').value.trim(),date:new Date().toISOString(),resume:structuredClone(state.resume),template:state.template});state.versions=state.versions.slice(0,20);persistVersions();closeModal('saveModal');renderVersions();toast('Saved in your browser.','success');}
function downloadJSON(v){const blob=new Blob([JSON.stringify({resume:v.resume,template:v.template,saved_at:v.date},null,2)],{type:'application/json'});downloadBlob(blob,(v.name||'resume').replace(/[^a-z0-9-_]+/gi,'_').slice(0,50)+'.json');}
function renderVersions(){const elem=$('versionList');if(!state.versions.length){elem.innerHTML='<div class="empty-versions"><div style="font-size:29px">◷</div><strong>No saved versions yet</strong><p>Make edits, then save a version. You can keep up to 20 snapshots.</p></div>';return;}
  elem.innerHTML=state.versions.map(v=>`<article class="version-row"><div><h3>${esc(v.name)}</h3><p>${esc(new Date(v.date).toLocaleString())} · ${esc(v.notes||'No notes')}</p></div><div class="row-actions"><button class="button primary" data-version="restore" data-id="${esc(v.id)}">↺ Restore</button><button class="button secondary" data-version="json" data-id="${esc(v.id)}">JSON</button><button class="button light" data-version="delete" data-id="${esc(v.id)}">Delete</button></div></article>`).join('');
}
function versionAction(action,id){const idx=state.versions.findIndex(v=>v.id===id);if(idx<0)return;const v=state.versions[idx];if(action==='restore'){state.resume=structuredClone(v.resume);state.template=v.template;state.proposed={};state.analysis=null;populateTemplates();$('reviewCard').classList.add('hidden');$('analysisCard').classList.add('hidden');view('tailor');toast('Version restored.','success');}else if(action==='json'){downloadJSON(v);}else if(action==='delete'){state.versions.splice(idx,1);persistVersions();renderVersions();toast('Saved version deleted.');}}
function downloadBlob(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1200);}
async function exportResume(format){const resume=currentPreviewResume();if(!meaningfulResume(resume)){toast('Create or upload a resume before exporting.','error');return;}const b=$(format==='pdf'?'downloadPDF':'downloadDOCX');busy(b,true,'Exporting');try{const res=await fetch('/api/export',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({resume,template:state.template,format})});if(!res.ok){let m='Export failed.';try{m=(await res.json()).detail||m;}catch(e){}throw new Error(m);}const blob=await res.blob();const file=(resume.name||'My_Resume').replace(/[^a-z0-9_-]+/gi,'_')+'_'+state.template+'.'+format;downloadBlob(blob,file);toast('Your '+format.toUpperCase()+' is ready.','success');}catch(e){toast(e.message,'error');}finally{busy(b,false);}}
function bindEvents(){
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>view(b.dataset.view)));
  for(const b of ['editResumeButton','editResumeSide'])$(b).addEventListener('click',editor);
  for(const b of ['topHelp','settingsSide'])$(b).addEventListener('click',()=>openModal('settingsModal'));
  document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>closeModal(b.dataset.close)));
  document.querySelectorAll('.modal-backdrop').forEach(b=>b.addEventListener('mousedown',e=>{if(e.target===b)closeModal(b.id)}));
  document.addEventListener('keydown',e=>{if(e.key==='Escape')document.querySelectorAll('.modal-backdrop:not(.hidden)').forEach(b=>closeModal(b.id));});
  $('editModal').addEventListener('input',e=>{const contact=e.target.dataset.contact;const section=e.target.dataset.editSection;if(contact)state.resume[contact]=e.target.value;if(section)state.resume.sections[section]=e.target.value;renderPreview();});
  $('wizardFields').addEventListener('input',e=>{if(e.target.dataset.answer){state.builderAnswers[e.target.dataset.answer]=e.target.value;renderPreview();}});
  $('wizardBack').addEventListener('click',()=>moveWizard(-1));$('wizardNext').addEventListener('click',()=>moveWizard(1));
  $('previewTemplates').addEventListener('click',e=>{const button=e.target.closest('[data-template]');if(button)setTemplate(button.dataset.template);});
  $('builderTemplates').addEventListener('click',e=>{const button=e.target.closest('[data-template]');if(button)setTemplate(button.dataset.template);});
  $('sectionPicker').addEventListener('change',e=>{if(e.target.dataset.section)setChoice(e.target.dataset.section,e.target.checked);});
  $('selectAllSections').addEventListener('click',()=>{state.selected=new Set(Object.keys(SECTION_NAMES));populateChoices()});
  $('clearSections').addEventListener('click',()=>{state.selected.clear();populateChoices()});
  $('provider').addEventListener('change',e=>{state.provider=e.target.value;$('providerNote').textContent=e.target.value==='gemini'?(state.hasGemini?'Ready to enhance with Gemini.':'Add GEMINI_API_KEY to .env first.'):'Uses a model running on your computer; start Ollama first.';});
  $('jobDescription').addEventListener('input',()=>{updateJDCount();state.jd=$('jobDescription').value;});
  $('analyzeButton').addEventListener('click',analyze);
  $('enhanceButton').addEventListener('click',()=>{state.originalSections=structuredClone(state.resume.sections);enhance();});
  $('reviewItems').addEventListener('click',e=>{const button=e.target.closest('[data-review]');if(button)decide(button.dataset.key,button.dataset.review==='reset'?'reset':button.dataset.review==='accept'?'accepted':'rejected');});
  $('acceptAll').addEventListener('click',()=>{Object.keys(state.proposed).filter(k=>!state.decided[k]).forEach(k=>decide(k,'accepted'));toast('Accepted the remaining suggestions. Review resume accuracy before exporting.','success');});
  $('dismissReview').addEventListener('click',()=>$('reviewCard').classList.add('hidden'));
  fileDrop('resumeDropzone','resumeFile','resume');
  $('tryDemo').addEventListener('click',()=>{state.resume={name:'Alex Morgan',headline:'Software Engineer',email:'alex.morgan@example.com',phone:'+1 555 010 2024',location:'Austin, TX',links:'github.com/example',sections:{summary:'Software engineer with hands-on experience building internal services, automation scripts, and API integrations.',experience:'Software Engineer | Example Systems | 2023 - Present\n- Built Python automation scripts to simplify recurring data imports\n- Collaborated with engineers on REST API integrations\n- Wrote unit tests for business-critical workflows',skills:'Python, SQL, Git, REST APIs, Agile, Testing',projects:'Issue Tracker Dashboard | Python, HTML, CSS\n- Created a reporting interface for internal issue tracking',education:'B.S. in Computer Science | Example University | 2023',achievements:'',certifications:'',additional:''}};state.filename='Sample resume (fictional)';$('resumeDropzone').classList.add('hidden');$('resumeUploaded').classList.remove('hidden');$('resumeUploadedName').textContent='Sample resume · fictional';$('resumeUploadedSub').textContent='For exploring features only';$('analysisCard').classList.add('hidden');$('reviewCard').classList.add('hidden');renderPreview();toast('Sample loaded. Replace it with your real resume.','success');});
  $('replaceResume').addEventListener('click',()=>$('resumeFile').click());
  $('jdFile').addEventListener('change',()=>{parseFile($('jdFile').files[0],'jd');$('jdFile').value='';});
  $('jdUploadButton').addEventListener('click',()=>$('jdFile').click());
  $('jdSampleButton').addEventListener('click',()=>{$('jobDescription').value='We are hiring a Software Engineer to develop backend features and automation. Required: Python, SQL, Git, REST APIs, unit testing and Agile teamwork. Preferred: AWS, Docker, PostgreSQL and CI/CD. You will work with cross-functional teams, write maintainable code and solve performance challenges.';updateJDCount();toast('Example job description loaded.','success');});
  $('downloadPDF').addEventListener('click',()=>exportResume('pdf'));
  $('downloadDOCX').addEventListener('click',()=>exportResume('docx'));
  for(const id of ['saveVersion','saveQuickVersion'])$(id).addEventListener('click',saveDialog);
  $('confirmSave').addEventListener('click',saveVersion);
  $('versionList').addEventListener('click',e=>{const btn=e.target.closest('[data-version]');if(btn)versionAction(btn.dataset.version,btn.dataset.id);});
  $('clearSavedData').addEventListener('click',()=>{if(confirm('Delete all saved versions from this browser? This cannot be undone.')){state.versions=[];persistVersions();renderVersions();toast('Browser-saved versions deleted.','success');}});
}
window.addEventListener('DOMContentLoaded',init);
