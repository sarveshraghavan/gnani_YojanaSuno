const $ = (id) => document.getElementById(id);
const extraTranslations = {
  en: {source_freshness:"Source registry checked 6 Nov 2026. Official portals are linked above; source documents and current state rules have not been independently verified for this demo.",voice_ready:"Voice is ready. Tap the button to start; tap again to stop.",voice_processing:"Processing your voice message. You can type instead if this takes too long.",voice_recording:"Listening. Tap the button again to stop recording.",transcript_title:"Speech recognized",transcript_hint:"Your recognized words will appear here.",transcript_processing:"Recording complete. Transcribing your speech…",transcript_done:"Speech recognized",transcript_error:"We could not transcribe that clip. Try again or type instead.",brand_subtitle:"Voice support for Indian agriculture",trust_label:"Official agriculture information sources",state_label:"Choose state",region_schemes:"State & Central Schemes"},
  hi: {source_freshness:"स्रोत सूची 6 नवंबर 2026 को जाँची गई। आधिकारिक पोर्टल के लिंक ऊपर हैं; इस डेमो के लिए दस्तावेज़ों और मौजूदा राज्य नियमों की अलग से पुष्टि नहीं हुई है।",voice_ready:"आवाज़ तैयार है। शुरू करने के लिए बटन दबाएँ; रोकने के लिए फिर दबाएँ।",voice_processing:"आपकी आवाज़ पर काम हो रहा है। देर हो तो आप लिखकर पूछ सकते हैं।",voice_recording:"सुन रहे हैं। रिकॉर्डिंग रोकने के लिए बटन फिर दबाएँ।",transcript_title:"पहचानी गई आवाज़",transcript_hint:"आपके बोले हुए शब्द यहाँ दिखेंगे।",transcript_processing:"रिकॉर्डिंग पूरी। आपकी बात लिखी जा रही है…",transcript_done:"आपकी बात लिखी गई",transcript_error:"आवाज़ लिखी नहीं जा सकी। फिर कोशिश करें या लिखकर पूछें।",brand_subtitle:"भारतीय खेती के लिए आवाज़ सहायता",trust_label:"आधिकारिक कृषि जानकारी के स्रोत",state_label:"राज्य चुनें",region_schemes:"राज्य और केंद्र की योजनाएँ"},
  ta: {source_freshness:"ஆதாரப் பட்டியல் 6 நவம்பர் 2026 அன்று சரிபார்க்கப்பட்டது. அதிகாரப்பூர்வ தள இணைப்புகள் மேலே உள்ளன; இந்த டெமோவுக்கான ஆவணங்களும் தற்போதைய மாநில விதிகளும் தனியாக உறுதிப்படுத்தப்படவில்லை.",voice_ready:"குரல் தயார். தொடங்க பொத்தானைத் தொடவும்; நிறுத்த மீண்டும் தொடவும்.",voice_processing:"உங்கள் குரல் செய்தி செயலாக்கப்படுகிறது. தாமதமானால் தட்டச்சு செய்யலாம்.",voice_recording:"கேட்கிறோம். பதிவை நிறுத்த மீண்டும் பொத்தானைத் தொடவும்.",transcript_title:"அடையாளம் கண்ட பேச்சு",transcript_hint:"நீங்கள் பேசிய சொற்கள் இங்கே தோன்றும்.",transcript_processing:"பதிவு முடிந்தது. உங்கள் பேச்சு எழுத்தாக்கப்படுகிறது…",transcript_done:"உங்கள் பேச்சு எழுத்தாக்கப்பட்டது",transcript_error:"பேச்சை எழுத்தாக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது எழுதவும்.",brand_subtitle:"இந்திய வேளாண்மைக்கான குரல் உதவி",trust_label:"அதிகாரப்பூர்வ வேளாண் தகவல் ஆதாரங்கள்",state_label:"மாநிலத்தைத் தேர்ந்தெடுக்கவும்",region_schemes:"மாநில மற்றும் மத்திய திட்டங்கள்"},
  te: {source_freshness:"మూలాల జాబితా 6 నవంబర్ 2026న తనిఖీ చేయబడింది. అధికారిక పోర్టల్ లింకులు పైన ఉన్నాయి; ఈ డెమో కోసం పత్రాలు, ప్రస్తుత రాష్ట్ర నియమాలు విడిగా ధృవీకరించలేదు.",voice_ready:"వాయిస్ సిద్ధంగా ఉంది. మొదలుపెట్టడానికి బటన్ నొక్కండి; ఆపడానికి మళ్లీ నొక్కండి.",voice_processing:"మీ వాయిస్ సందేశం ప్రాసెస్ అవుతోంది. ఆలస్యమైతే టైప్ చేయవచ్చు.",voice_recording:"వింటున్నాం. రికార్డింగ్ ఆపడానికి బటన్‌ను మళ్లీ నొక్కండి.",transcript_title:"గుర్తించిన మాటలు",transcript_hint:"మీరు మాట్లాడిన మాటలు ఇక్కడ కనిపిస్తాయి.",transcript_processing:"రికార్డింగ్ పూర్తయింది. మీ మాటలు వచనంగా మారుతున్నాయి…",transcript_done:"మీ మాటలు వచనంగా మారాయి",transcript_error:"మాటలను వచనంగా మార్చలేకపోయాం. మళ్లీ ప్రయత్నించండి లేదా టైప్ చేయండి.",brand_subtitle:"భారత వ్యవసాయానికి వాయిస్ సహాయం",trust_label:"అధికారిక వ్యవసాయ సమాచార వనరులు",state_label:"రాష్ట్రాన్ని ఎంచుకోండి",region_schemes:"రాష్ట్ర మరియు కేంద్ర పథకాలు"}
};
extraTranslations.en.reply_title="Guidance in your selected language";
extraTranslations.hi.reply_title="आपकी चुनी हुई भाषा में जवाब";
extraTranslations.ta.reply_title="நீங்கள் தேர்ந்தெடுத்த மொழியில் பதில்";
extraTranslations.te.reply_title="మీరు ఎంచుకున్న భాషలో సమాధానం";
const pageText = (key) => {
  const code = ($('language')?.value || 'en-IN').split('-')[0];
  return extraTranslations[code]?.[key] || window.YS_I18N?.[code]?.[key] || extraTranslations.en[key] || window.YS_I18N?.en?.[key] || key;
};
function applyPageLanguage(value) {
  const code = String(value || 'en-IN').split('-')[0];
  const dict = {...(window.YS_I18N?.[code] || window.YS_I18N?.en || {}), ...(extraTranslations[code] || {})};
  document.documentElement.lang = value || 'en-IN';
  document.querySelectorAll('[data-i]').forEach(el => { const v=dict[el.dataset.i]; if(v!==undefined) el.textContent=v; });
  document.querySelectorAll('[data-ip]').forEach(el => { const v=dict[el.dataset.ip]; if(v!==undefined) el.setAttribute('placeholder',v); });
  document.querySelectorAll('[data-ia]').forEach(el => { const v=dict[el.dataset.ia]; if(v!==undefined) el.setAttribute('aria-label',v); });
  document.querySelectorAll('[data-im]').forEach(el => { const v=dict[el.dataset.im]; if(v!==undefined) el.setAttribute('content',v); });
  const title=document.querySelector('[data-ititle]'); if(title){const v=dict[title.dataset.ititle];if(v!==undefined)document.title=v;}
  document.querySelectorAll('[data-prompt-key]').forEach(el => { const v=dict[el.dataset.promptKey]; if(v!==undefined)el.dataset.prompt=v; });
  document.querySelectorAll('[data-language]').forEach(button => button.setAttribute('aria-pressed',String(button.dataset.language===value)));
  document.querySelectorAll('[data-lang]').forEach(button => button.setAttribute('aria-pressed',String(button.dataset.lang===value)));
  $('stateSelect')?.setAttribute('aria-label',pageText('state_label'));
}
document.addEventListener('yojana:lang', event => { const lang=event.detail?.lang; if(lang){$('language').value=lang;applyPageLanguage(lang);} });
document.getElementById('language')?.addEventListener('change', event => {applyPageLanguage(event.target.value);document.dispatchEvent(new CustomEvent('yojana:lang',{detail:{lang:event.target.value}}));});
document.querySelectorAll('[data-language]').forEach(button => button.addEventListener('click', () => {const select=$('language');if(select){select.value=button.dataset.language;select.dispatchEvent(new Event('change',{bubbles:true}));}}));
document.querySelectorAll('[data-lang]').forEach(button => button.addEventListener('click', () => {const select=$('language');if(select){select.value=button.dataset.lang;select.dispatchEvent(new Event('change',{bubbles:true}));}}));
const regionNames={"hi-IN":{"TN":"तमिलनाडु","UP":"उत्तर प्रदेश","PB":"पंजाब","MH":"महाराष्ट्र"},"ta-IN":{"TN":"தமிழ்நாடு","UP":"உத்தரப் பிரதேசம்","PB":"பஞ்சாப்","MH":"மகாராஷ்டிரா"},"te-IN":{"TN":"తమిళనాడు","UP":"ఉత్తరప్రదేశ్","PB":"పంజాబ్","MH":"మహారాష్ట్ర"},"en-IN":{"TN":"Tamil Nadu","UP":"Uttar Pradesh","PB":"Punjab","MH":"Maharashtra"}};
function updateRegionLabel(){const code=$('stateSelect')?.value||'TN',lang=$('language')?.value||'hi-IN';if($('stateSelect'))[...$('stateSelect').options].forEach(option=>{option.textContent=`${regionNames[lang]?.[option.value]||regionNames['en-IN'][option.value]} (${option.value})`});if($('activeRegion'))$('activeRegion').textContent=`📍 ${regionNames[lang]?.[code]||regionNames['en-IN'][code]} (${code}) · ${pageText('region_schemes')}`}
$('stateSelect')?.addEventListener('change',updateRegionLabel);
updateRegionLabel();
applyPageLanguage(document.getElementById('language')?.value || 'en-IN');
let knownSlots = {};
let latestReply = "";
let pendingSlot = null;
let confirmedTurn = false;
let recorder = null;
let mediaStream = null;
let liveSpeechRecognition = null;
let chunks = [];
window.ysHandled = false;
window.showResponse = function(text){latestReply=String(text||'');$('reply').textContent=latestReply;$('reply').hidden=!latestReply;$('speakBtn').hidden=!latestReply};
function makeUuid(){if(globalThis.crypto?.randomUUID)return crypto.randomUUID();return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.random()*16|0;return(c==='x'?r:(r&3|8)).toString(16)})}
const uuidShape=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
let sessionId;
try { const prior=sessionStorage.getItem('yojanasuno-session');sessionId=prior&&uuidShape.test(prior)?prior:makeUuid();sessionStorage.setItem('yojanasuno-session',sessionId); }
catch { sessionId = makeUuid(); }
const labelsByLanguage = {
  en:{eligible:"Potential match · verify",need_more_info:"Need a little more",not_eligible:"May not match",draft:"Unverified draft",notChecked:"What this check did not cover",needed:"Still needed: ",official:"Official scheme portal ↗"},
  hi:{eligible:"संभावित मिलान · पुष्टि करें",need_more_info:"कुछ और जानकारी चाहिए",not_eligible:"शायद मेल न खाए",draft:"असत्यापित मसौदा",notChecked:"इस जाँच में क्या शामिल नहीं था",needed:"अभी चाहिए: ",official:"आधिकारिक योजना पोर्टल ↗"},
  ta:{eligible:"பொருந்தலாம் · உறுதிப்படுத்தவும்",need_more_info:"மேலும் சில விவரங்கள் தேவை",not_eligible:"பொருந்தாமல் இருக்கலாம்",draft:"சரிபார்க்கப்படாத வரைவு",notChecked:"இந்தச் சரிபார்ப்பில் சேராதவை",needed:"இன்னும் தேவை: ",official:"அதிகாரப்பூர்வ திட்டத் தளம் ↗"},
  te:{eligible:"సరిపోవచ్చు · నిర్ధారించండి",need_more_info:"మరికొన్ని వివరాలు కావాలి",not_eligible:"సరిపోకపోవచ్చు",draft:"ధృవీకరించని ముసాయిదా",notChecked:"ఈ పరిశీలనలో లేనివి",needed:"ఇంకా కావలసినవి: ",official:"అధికారిక పథకం వెబ్‌సైట్ ↗"}
};
const hindiResultCopy = {
  pm_kisan:{summary:"पात्र किसान परिवारों के लिए आय सहायता।",guidance:"आधिकारिक PM-KISAN पोर्टल पर परिवार की पूरी पात्रता और भूमि रिकॉर्ड की पुष्टि करें। पंजीकृत किसानों के लिए ई-केवाईसी ज़रूरी है।",not_checked:["सरकारी पद, सेवा, पेंशन और पंजीकृत पेशों से जुड़ी अन्य अपवर्जन श्रेणियाँ।","भूमि रिकॉर्ड की शर्तें, 1 फ़रवरी 2019 की कट-ऑफ तारीख और उत्तराधिकार के अपवाद।","परिवार की परिभाषा और दोहराए गए या पहले से मौजूद लाभार्थियों की जाँच।","ई-केवाईसी, बैंक खाते और आधार जोड़ने की स्थिति।"],source:"स्रोत आधार: PM-KISAN दिशानिर्देश §3, §5.1 और §4.1; जाँच तिथि: "},
  pmfby:{summary:"अधिसूचित मौसम में अधिसूचित फसलों और क्षेत्रों के लिए फसल बीमा।",guidance:"मौजूदा अधिसूचना और नामांकन की अंतिम तारीख आधिकारिक पोर्टल या स्थानीय कृषि कार्यालय से पक्की करें।",not_checked:["मौजूदा राज्य, ज़िला, गाँव, फसल और मौसम की अधिसूचना।","नामांकन की अंतिम तारीख, किसान श्रेणी, प्रीमियम और बीमा में शामिल जोखिम।"],source:"स्रोत आधार: PMFBY संशोधित परिचालन दिशानिर्देश §7; जाँच तिथि: "},
  pm_kusum:{summary:"पात्र स्वतंत्र सौर पंपों और बिजली से जुड़े कृषि पंपों के सौरकरण के लिए सहायता।",guidance:"अपने राज्य की कार्यान्वयन एजेंसी से घटक, आवेदन की स्थिति, किसान अंशदान, पंप क्षमता और ज़रूरी रिकॉर्ड की पुष्टि करें।",not_checked:["राज्य में आवेदन की मौजूदा अवधि, कार्यान्वयन एजेंसी की सूचना और ज़िले का आवंटन।","राज्य के अनुसार क्षमता, आवेदन प्रक्रिया, पंप की सीमा, किसान अंशदान और अतिरिक्त सहायता।","पंप क्षमता, पानी का स्रोत, बिजली कनेक्शन और घटक से जुड़ी तकनीकी शर्तें।"],source:"स्रोत आधार: नवीन और नवीकरणीय ऊर्जा मंत्रालय के PM-KUSUM दिशानिर्देश; जाँच तिथि: "}
};
const hindiSlotNames={state:"राज्य",district:"ज़िला",owns_land:"भूमि का मालिकाना हक",is_institutional_holder:"क्या भूमि संस्था के नाम है",pays_income_tax:"पिछले साल परिवार में किसी ने आयकर दिया था या नहीं",crop:"फसल",season:"फसल का मौसम",area_notified:"क्या गाँव और फसल अधिसूचित हैं",component:"पंप का योजना घटक",has_grid_connected_pump:"पंप में बिजली का कनेक्शन है या नहीं",state_application_open:"क्या राज्य में आवेदन खुले हैं",state_requirements_confirmed:"राज्य की शर्तों की पुष्टि"};
function localizeResult(item){
  if(($('language').value||'').startsWith('hi')){
    const copy=hindiResultCopy[item.scheme_id];
    const names={pm_kisan:"प्रधानमंत्री किसान सम्मान निधि (PM-KISAN)",pmfby:"प्रधानमंत्री फसल बीमा योजना (PMFBY)",pm_kusum:"प्रधानमंत्री कुसुम योजना (PM-KUSUM)"};
    if(names[item.scheme_id])item.name=names[item.scheme_id];
    if(copy){item.summary=copy.summary;item.next_steps=copy.guidance;item.source_basis=copy.source+(item.last_verified||'');item.not_checked=[...copy.not_checked,...(item.not_checked_slots||[]).map(slot=>hindiSlotNames[slot]||slot)];}
    item.missing=(item.missing||[]).map(slot=>hindiSlotNames[slot]||slot);
    if(Array.isArray(item.reasons)&&item.reasons.length)item.reasons=item.reasons.map(reason=>{const slot=String(reason).split(' ')[0];return `${hindiSlotNames[slot]||slot} की शर्त पूरी नहीं हुई`;});
  }
  return item;
}
const boolValue = (value) => value === 'true' ? true : value === 'false' ? false : value || null;
function toast(message){const el=$("toast");el.textContent=message;el.classList.add("show");setTimeout(()=>el.classList.remove("show"),3200)}
function readFormSlots(){
  const values={state:$('slot-state').value.trim(),district:$('slot-district').value.trim(),owns_land:boolValue($('slot-owned').value),is_institutional_holder:boolValue($('slot-institution').value),pays_income_tax:boolValue($('slot-tax').value),crop:$('slot-crop').value.trim()||null,season:$('slot-season').value||null,area_notified:boolValue($('slot-notified').value),has_grid_connected_pump:boolValue($('slot-component').value),state_application_open:boolValue($('slot-open').value),state_requirements_confirmed:boolValue($('slot-state-confirmed').value)};
  for(const [k,v] of Object.entries(values)) if(v!==null&&v!=='') knownSlots[k]=v;
}
function updateFormSlots(slots){
  const map={state:'slot-state',district:'slot-district',owns_land:'slot-owned',is_institutional_holder:'slot-institution',pays_income_tax:'slot-tax',crop:'slot-crop',season:'slot-season',area_notified:'slot-notified',has_grid_connected_pump:'slot-component',state_application_open:'slot-open',state_requirements_confirmed:'slot-state-confirmed'};
  for(const [key,id] of Object.entries(map)){if(slots[key]!==undefined&&slots[key]!==null&&$(id))$(id).value=slots[key]}
}
function startLiveTranscript(){
  const SpeechRecognitionClass=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SpeechRecognitionClass)return;
  try{liveSpeechRecognition=new SpeechRecognitionClass();liveSpeechRecognition.lang=$('language').value;liveSpeechRecognition.continuous=true;liveSpeechRecognition.interimResults=true;liveSpeechRecognition.onresult=event=>{let transcript='';for(let i=0;i<event.results.length;i++)transcript+=event.results[i][0].transcript;$('transcriptText').removeAttribute('data-i');$('transcriptText').textContent=transcript.trim()||pageText('transcript_hint');$('transcriptText').lang=$('language').value;};liveSpeechRecognition.start();}catch{liveSpeechRecognition=null;}
}
function render(data){
  const copy=labelsByLanguage[$('language').value.split('-')[0]]||labelsByLanguage.en;
  knownSlots=data.slots||knownSlots;updateFormSlots(knownSlots);$("emptyState").hidden=true;$("results").innerHTML="";
  for(const rawItem of data.results||[]){
    const item=localizeResult({...rawItem});
    const card=document.createElement('article');card.className='result-card';
    const head=document.createElement('div');head.className='result-head';
    const title=document.createElement('b');title.textContent=item.name;
    const badge=document.createElement('span');badge.className=`status ${item.status}`;badge.textContent=copy[item.status]||item.status;
    head.append(title,badge);if(item.verified===false){const draft=document.createElement('span');draft.className='status need_more_info';draft.textContent=copy.draft;head.append(draft)}card.append(head);
    const p=document.createElement('p');p.textContent=item.summary;card.append(p);
    const next=document.createElement('p');
    if(item.missing?.length) next.textContent=($('language').value.startsWith('hi')?'अभी जानकारी चाहिए: ':copy.needed)+item.missing.map(x=>x.replaceAll('_',' ')).join(', ');
    else if(item.status==='eligible') next.textContent=item.next_steps;
    else if(item.reasons?.length) next.textContent=item.reasons.join(' ');
    else next.textContent=item.next_steps;
    card.append(next);
    if(item.source_basis){const basis=document.createElement('p');basis.className='source-basis';basis.textContent=item.source_basis;card.append(basis)}
    if(item.not_checked?.length){const details=document.createElement('details');details.className='not-checked';const summary=document.createElement('summary');summary.textContent=`${copy.notChecked} (${item.not_checked.length})`;const list=document.createElement('ul');for(const note of item.not_checked){const li=document.createElement('li');li.textContent=note;list.append(li)}details.append(summary,list);card.append(details)}
    const link=document.createElement('a');link.href=item.source_url||item.source;link.target='_blank';link.rel='noreferrer';link.textContent=copy.official;card.append(link);
    $("results").append(card);
  }
  pendingSlot=data.next_slot||null;confirmedTurn=data.stage==='complete';
  const question=data.next_question||'';$('nextQuestion').hidden=!question;$('nextQuestionText').textContent=question;
  latestReply=question||data.reply||'';$('reply').textContent=data.reply||'';$('reply').hidden=Boolean(question);$('speakBtn').hidden=!latestReply;
  $('resultTitle').textContent=data.stage==='confirming'?pageText('title_confirm'):question?pageText('title_question'):pageText('title_results');
  toast(data.stage==='complete'?pageText('toast_complete'):data.mode==='evon'?pageText('toast_evon'):pageText('toast_step'));
}
function showPrompt(data){
  knownSlots=data.slots||knownSlots;updateFormSlots(knownSlots);pendingSlot=data.pending_slot||null;confirmedTurn=false;
  $('emptyState').hidden=true;$('results').innerHTML='';$('resultTitle').textContent=pageText('title_question');
  $('nextQuestion').hidden=false;$('nextQuestionText').textContent=data.next_question||'';
  latestReply=data.next_question||'';$('reply').hidden=true;$('speakBtn').hidden=!latestReply;
}
function normalizedCheck(data){
  const results=(data.results||[]).map(item=>({...item,name:item.scheme_name,summary:item.benefit,source:item.source_url,missing:item.missing_slots,reasons:(item.failed_rules||[]).map(rule=>`${rule.slot} ${rule.op} ${JSON.stringify(rule.value)}`)}));
  return {...data,results,slots:data.slots||knownSlots};
}
async function submitText(text){
  readFormSlots();
  const extractedResponse=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,language:$('language').value,known_slots:knownSlots,session_id:sessionId,pending_slot:pendingSlot})});
  const extracted=await extractedResponse.json();if(!extractedResponse.ok)throw new Error(extracted.detail||'Could not understand those details. Please try again.');
  knownSlots=extracted.slots||knownSlots;
  if(['fix_detail','correction','confirm_retry'].includes(extracted.stage)){showPrompt(extracted);return}
  confirmedTurn=extracted.stage==='confirmed';
  const response=await fetch('/api/check',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({slots:knownSlots,language:$('language').value,session_id:sessionId,confirmed:confirmedTurn})});
  const checked=await response.json();if(!response.ok)throw new Error(checked.detail||'Could not check the schemes. Please try again.');
  knownSlots=checked.slots||knownSlots;
  if(extracted.disclosure){checked.reply=[extracted.disclosure,checked.reply].filter(Boolean).join(' ');if(checked.next_question)checked.next_question=`${extracted.disclosure} ${checked.next_question}`;}
  render({...normalizedCheck(checked),slots:knownSlots,mode:extracted.mode});
}
async function submitAudio(file){
  $('voiceStatus').textContent=pageText('voice_processing');
  $('transcriptPanel').hidden=false;$('transcriptText').textContent=pageText('transcript_processing');
  const form=new FormData();form.append('audio',file,file.name||'farmer-audio.webm');form.append('language',$('language').value);form.append('session_id',sessionId);form.append('pending_slot',pendingSlot||'');form.append('known_slots',JSON.stringify(knownSlots));
  const response=await fetch('/api/voice',{method:'POST',body:form});const data=await response.json();if(!response.ok)throw new Error(data.detail||'Voice turn failed');
  $('transcriptText').removeAttribute('data-i');$('transcriptText').textContent=data.transcript||pageText('transcript_error');$('transcriptText').lang=data.detected_language_code||$('language').value;$('voiceStatus').textContent=data.transcript?pageText('transcript_done'):pageText('transcript_error');
  const spokenReply=data.next_question||data.reply||'';$('voiceReply').textContent=spokenReply;$('responsePanel').hidden=!spokenReply;$('voicePlayer').hidden=!data.audio_base64;
  if(data.audio_base64){const bytes=Uint8Array.from(atob(data.audio_base64),c=>c.charCodeAt(0));const audioUrl=URL.createObjectURL(new Blob([bytes],{type:'audio/wav'}));$('player').src=audioUrl;$('player').hidden=false;$('voicePlayer').src=audioUrl}
  if(data.stage==='fix_detail'||data.stage==='correction'||data.stage==='confirm_retry')showPrompt(data);else render(normalizedCheck(data));
  if(data.audio_base64){try{await $('player').play()}catch{}}
  else if(data.fallback_audio_text&&'speechSynthesis'in window){const utterance=new SpeechSynthesisUtterance(data.fallback_audio_text);utterance.lang=data.detected_language_code||$('language').value;speechSynthesis.speak(utterance)}
  $('voiceStatus').textContent=pageText('voice_ready');
}
async function recordingToWav(blob){
  const AudioContextClass=window.AudioContext||window.webkitAudioContext;if(!AudioContextClass)throw new Error(pageText('audio_conversion_unavailable'));
  const context=new AudioContextClass();try{
    const decoded=await context.decodeAudioData(await blob.arrayBuffer());const targetRate=16000;const length=Math.ceil(decoded.duration*targetRate);const pcm=new Int16Array(length);
    for(let i=0;i<length;i++){const sourceIndex=Math.min(decoded.length-1,Math.floor(i*decoded.sampleRate/targetRate));let sample=0;for(let channel=0;channel<decoded.numberOfChannels;channel++)sample+=decoded.getChannelData(channel)[sourceIndex]/decoded.numberOfChannels;sample=Math.max(-1,Math.min(1,sample));pcm[i]=sample<0?sample*32768:sample*32767;}
    const buffer=new ArrayBuffer(44+pcm.length*2);const view=new DataView(buffer);const write=(offset,value)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i))};write(0,'RIFF');view.setUint32(4,36+pcm.length*2,true);write(8,'WAVE');write(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,targetRate,true);view.setUint32(28,targetRate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);write(36,'data');view.setUint32(40,pcm.length*2,true);new Int16Array(buffer,44).set(pcm);return new File([buffer],'farmer-audio.wav',{type:'audio/wav'});
  }finally{await context.close()}
}
const friendlyErrors={'hi-IN':'अभी जवाब नहीं मिल पाया। कृपया फिर कोशिश करें या 1551 पर कॉल करें।','ta-IN':'இப்போது பதில் கிடைக்கவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது 1551-ஐ அழைக்கவும்.','te-IN':'ఇప్పుడు సమాధానం రాలేదు. మళ్లీ ప్రయత్నించండి లేదా 1551కు కాల్ చేయండి.','en-IN':'I could not get a response. Please try again or call 1551.'};
document.addEventListener('yojana:check',async event=>{
  window.ysHandled=true;
  const detail=event.detail||{};const lang=detail.lang||$('language').value;$('language').value=lang;
  const button=$('chatForm').querySelector('button[type="submit"]');if(button){button.disabled=true;button.querySelector('[data-i]')&&(button.querySelector('[data-i]').textContent=pageText('toast_checking'))}
  try{if(detail.audio instanceof Blob)await submitAudio(detail.audio);else await submitText(String(detail.text||''))}
  catch(err){const message=friendlyErrors[lang]||friendlyErrors['en-IN'];$('voiceStatus').textContent=message;window.showResponse(message);toast(message)}
  finally{if(button){button.disabled=false;const label=button.querySelector('[data-i]');if(label)label.textContent=pageText('submit_check')}}
});
$('chatForm').addEventListener('submit',e=>{e.preventDefault();const text=$('utterance').value.trim();if(!text)return;window.ysHandled=false;document.dispatchEvent(new CustomEvent('yojana:check',{detail:{text,lang:$('language').value}}));if(window.ysHandled)$('utterance').value=''});
$('audioFile').addEventListener('change',async e=>{
  const file=e.target.files[0];if(!file)return;
  toast(pageText('toast_processing'));
  try{await submitAudio(file);if(latestReply)toast(pageText('toast_voice_complete'))}catch(err){$('voiceStatus').textContent=pageText('voice_ready');toast(err.message)}finally{e.target.value=''}
});
$('recordBtn').addEventListener('click',()=>{
  if(recorder){recorder.stop();return}
  if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){toast(pageText('toast_mic_unavailable'));return}
  navigator.mediaDevices.getUserMedia({audio:true}).then(stream=>{
    mediaStream=stream;chunks=[];recorder=new MediaRecorder(stream);recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
    recorder.onstart=()=>{$('recordBtn').classList.add('listening');$('recordBtnCard')?.classList.add('listening');$('recordBtnCard')?.setAttribute('aria-label',pageText('record_listening'));$('wave')?.style.setProperty('display','flex');$('recordText').textContent=pageText('record_listening');$('recordBtn').setAttribute('aria-label',pageText('record_listening'));$('voiceStatus').textContent=pageText('voice_recording');$('transcriptPanel').hidden=false;$('transcriptText').setAttribute('data-i','transcript_hint');$('transcriptText').textContent=pageText('transcript_hint');startLiveTranscript()};
    recorder.onerror=()=>{const message=pageText('toast_record_error');$('voiceStatus').textContent=message;toast(message)};
    recorder.onstop=async()=>{const clip=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});stream.getTracks().forEach(track=>track.stop());mediaStream=null;try{liveSpeechRecognition?.stop()}catch{}liveSpeechRecognition=null;$('recordBtn').classList.remove('listening');$('recordBtnCard')?.classList.remove('listening');$('recordBtnCard')?.setAttribute('aria-label',pageText('record_button'));$('wave')?.style.setProperty('display','none');$('recordText').textContent=pageText('record_start');$('recordBtn').setAttribute('aria-label',pageText('record_button'));$('voiceStatus').textContent=pageText('transcript_processing');recorder=null;try{const wav=await recordingToWav(clip);await submitAudio(wav)}catch(err){$('voiceStatus').textContent=pageText('transcript_error');$('transcriptText').textContent=err.message;toast(err.message)}};
    recorder.start();
  }).catch(()=>{const message=pageText('toast_allow_mic');$('voiceStatus').textContent=message;toast(message)});
});
$('speakBtn').addEventListener('click',async()=>{
  try{const res=await fetch('/api/speak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:latestReply,language:$('language').value})});if(!res.ok){const body=await res.json();throw new Error(body.detail||pageText('toast_timbre_missing'))};const audio=URL.createObjectURL(await res.blob());$('player').src=audio;$('player').hidden=false;await $('player').play()}catch(err){if('speechSynthesis'in window){const u=new SpeechSynthesisUtterance(latestReply);u.lang=$('language').value;speechSynthesis.speak(u);toast(pageText('toast_playing_browser'))}else toast(err.message)}
});
for(const chip of document.querySelectorAll('[data-prompt]'))chip.addEventListener('click',()=>{$('utterance').value=chip.dataset.prompt;$('utterance').focus()});
$('fieldModeToggle')?.addEventListener('click',e=>{const on=e.currentTarget.getAttribute('aria-pressed')!=='true';e.currentTarget.setAttribute('aria-pressed',String(on));document.body.classList.toggle('field-mode',on);document.body.classList.toggle('mode-field',on)});
document.getElementById('recordBtnCard')?.addEventListener('click',()=>{if($('recordBtn').classList.contains('listening'))$('recordBtn').click();else $('recordBtn').click()});
document.getElementById('heroSpeak')?.addEventListener('click',()=>{document.getElementById('recordBtn')?.scrollIntoView({behavior:'smooth',block:'center'});if(!$('recordBtn').classList.contains('listening'))$('recordBtn').click()});
function updateNetwork(){const online=navigator.onLine;$('networkDot')?.classList.toggle('offline',!online);if($('networkStatus'))$('networkStatus').textContent=pageText(online?'network_online':'network_offline')}
window.addEventListener('online',updateNetwork);window.addEventListener('offline',updateNetwork);updateNetwork();
fetch('/api/health').then(r=>r.json()).then(h=>{if($('voiceModePill'))$('voiceModePill').textContent=pageText(h.modes?.voice_mock?'mode_mock':'mode_live')}).catch(()=>{if($('voiceModePill'))$('voiceModePill').textContent=pageText('mode_unknown')});
