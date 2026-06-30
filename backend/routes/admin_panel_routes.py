"""Staff-facing Admin Panel page for uploading URLs / PDFs on a live deployment."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/admin", tags=["Admin Panel"])

PAGE = """<!DOCTYPE html>
<html lang='en'>
<head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width, initial-scale=1.0'>
<title>DST AI - Admin Panel</title>
<style>
:root{--blue:#00518a;--blue-dark:#003f6b;--accent:#1c84c6;--bg:#f5f9fc;}
*{box-sizing:border-box;font-family:Segoe UI,Arial,sans-serif;}
body{margin:0;background:var(--bg);color:#1a2733;}
header{background:var(--blue);color:#fff;padding:18px 24px;}
header h1{margin:0;font-size:20px;}
header p{margin:4px 0 0;font-size:13px;opacity:.85;}
.wrap{max-width:720px;margin:24px auto;padding:0 16px;}
.card{background:#fff;border:1px solid #e3edf5;border-radius:12px;padding:20px;margin-bottom:20px;box-shadow:0 1px 4px rgba(0,0,0,.04);}
.card h2{margin:0 0 14px;font-size:16px;color:var(--blue-dark);}
label{display:block;font-size:13px;font-weight:600;margin:10px 0 4px;}
input,select{width:100%;padding:10px;border:1px solid #cdddea;border-radius:8px;font-size:14px;}
button{background:var(--blue);color:#fff;border:none;padding:11px 18px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;margin-top:12px;}
button:hover{background:var(--blue-dark);}
.stat{font-size:28px;font-weight:700;color:var(--blue);}
.msg{margin-top:12px;padding:10px 12px;border-radius:8px;font-size:13px;display:none;}
.msg.ok{background:#e6f6ec;color:#1b7a3d;display:block;}
.msg.err{background:#fdebec;color:#b5292f;display:block;}
.hint{font-size:12px;color:#6b7c8a;margin-top:6px;}
</style>
</head>
<body>
<header>
<h1>DST AI - Admin Panel</h1>
<p>DST-CIMS knowledge base management (staff only)</p>
</header>
<div class='wrap'>

<div class='card'>
<label>Admin Key</label>
<input id='key' type='password' placeholder='Enter admin key'>
<div class='hint'>Set by the ADMIN_KEY environment variable. Required for uploads.</div>
</div>

<div class='card'>
<h2>Knowledge base status</h2>
<div class='stat' id='count'>-</div>
<div class='hint'>Total indexed chunks</div>
<button onclick='refreshStats()'>Refresh</button>
</div>

<div class='card'>
<h2>Add a website URL</h2>
<label>URL</label>
<input id='url' type='text' placeholder='https://...'>
<label>Department</label>
<select id='urlDept'>
<option value='general'>general</option>
<option value='computer-science'>computer-science</option>
<option value='mathematics'>mathematics</option>
<option value='mba'>mba</option>
</select>
<button onclick='addUrl()'>Read and Add URL</button>
<div class='msg' id='urlMsg'></div>
</div>

<div class='card'>
<h2>Upload a PDF</h2>
<label>PDF file</label>
<input id='pdf' type='file' accept='.pdf'>
<label>Department</label>
<select id='pdfDept'>
<option value='general'>general</option>
<option value='computer-science'>computer-science</option>
<option value='mathematics'>mathematics</option>
<option value='mba'>mba</option>
</select>
<button onclick='addPdf()'>Upload and Train</button>
<div class='msg' id='pdfMsg'></div>
</div>

</div>
<script>
function show(id,ok,text){var m=document.getElementById(id);m.className='msg '+(ok?'ok':'err');m.textContent=text;}
function key(){return document.getElementById('key').value.trim();}
function refreshStats(){
 fetch('/admin/stats').then(function(r){return r.json();}).then(function(d){
  document.getElementById('count').textContent=d.documents;
 }).catch(function(){document.getElementById('count').textContent='?';});
}
function addUrl(){
 var url=document.getElementById('url').value.trim();
 var dept=document.getElementById('urlDept').value;
 if(!url){show('urlMsg',false,'Please enter a URL.');return;}
 show('urlMsg',true,'Reading URL, please wait...');
 fetch('/admin/upload/url',{method:'POST',headers:{'Content-Type':'application/json','X-Admin-Key':key()},body:JSON.stringify({url:url,department:dept})})
 .then(function(r){return r.json().then(function(d){return {ok:r.ok,d:d};});})
 .then(function(res){
  if(res.ok){show('urlMsg',true,'Done! '+res.d.chunks_indexed+' chunks added from the URL.');refreshStats();}
  else{show('urlMsg',false,'Error: '+(res.d.detail||'failed'));}
 }).catch(function(){show('urlMsg',false,'Network error.');});
}
function addPdf(){
 var f=document.getElementById('pdf').files[0];
 var dept=document.getElementById('pdfDept').value;
 if(!f){show('pdfMsg',false,'Please choose a PDF file.');return;}
 show('pdfMsg',true,'Uploading and training, please wait...');
 var fd=new FormData();fd.append('file',f);fd.append('department',dept);
 fetch('/admin/upload/pdf',{method:'POST',headers:{'X-Admin-Key':key()},body:fd})
 .then(function(r){return r.json().then(function(d){return {ok:r.ok,d:d};});})
 .then(function(res){
  if(res.ok){show('pdfMsg',true,'Done! '+res.d.chunks_indexed+' chunks added from '+res.d.filename+'.');refreshStats();}
  else{show('pdfMsg',false,'Error: '+(res.d.detail||'failed'));}
 }).catch(function(){show('pdfMsg',false,'Network error.');});
}
refreshStats();
</script>
</body>
</html>"""


@router.get("/panel", response_class=HTMLResponse, include_in_schema=False)
def admin_panel():
    return PAGE
