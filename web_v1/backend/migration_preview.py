"""Read-only migration access while the original server remains authoritative."""
from __future__ import annotations

import re

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

SOURCE_ORIGIN = "https://172.17.39.121:8080"
READ_PATHS = re.compile(r"^/(?:health|api/invoices(?:/\d+(?:/logs)?)?|api/migration-preview/(?:status|invoices/\d+/pdf)|api/setup/certificate)$")


def configure_migration_preview(app: FastAPI, settings) -> None:
    if not settings.migration_preview:
        return

    @app.middleware("http")
    async def read_only_preview(request: Request, call_next):
        path = request.url.path
        permitted = (request.method in {"GET", "HEAD", "OPTIONS"} and (path == "/" or READ_PATHS.fullmatch(path)))
        permitted = permitted or (request.method == "POST" and path == "/api/login")
        if not permitted:
            return JSONResponse({"detail": "105 서버는 이관 검증용으로 조회만 가능합니다. 실제 처리는 기존 서버에서 진행해 주세요.",
                                 "read_only": True, "production_origin": SOURCE_ORIGIN}, status_code=423,
                                headers={"Cache-Control": "no-store", "X-Accounting-Mode": "migration-preview"})
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Accounting-Mode"] = "migration-preview"
        return response


def preview_page() -> HTMLResponse:
    return HTMLResponse(PREVIEW_HTML, headers={"Cache-Control": "no-store"})


PREVIEW_HTML = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>회계업무 · 105 서버 이관 검증</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7fa;color:#173047;font:15px/1.6 'Malgun Gothic',sans-serif}
main{max-width:1280px;margin:36px auto;padding:0 24px}header{display:flex;justify-content:space-between;gap:20px;align-items:center}
h1{font-size:26px;margin:0}h2{font-size:18px;margin-top:0}p{margin:8px 0}a{color:#086e66}button{cursor:pointer}
.banner{background:#e4f4ef;border-left:4px solid #148575;padding:16px 20px;margin:24px 0;border-radius:6px}
.card{background:white;border:1px solid #dbe4eb;border-radius:10px;padding:24px;margin-top:20px}.muted{color:#65788a}
input,button{font:inherit;border:1px solid #c9d6df;border-radius:6px;padding:8px 12px}button{background:#087a6b;color:white;border:0}
form{display:flex;align-items:end;gap:12px;flex-wrap:wrap}label{display:flex;flex-direction:column;gap:5px}
#error{color:#b12626}table{border-collapse:collapse;width:100%;white-space:nowrap}th,td{text-align:left;padding:11px 12px;border-bottom:1px solid #e5ebf0}
th{background:#f1f6f9;font-size:13px}td.amount{text-align:right}#summary{display:flex;gap:28px;flex-wrap:wrap;margin:12px 0}
#records{overflow:auto}#search{width:340px;max-width:100%;margin:8px 0 18px}.badge{color:#087a6b;font-weight:bold}
@media(max-width:700px){main{margin:20px auto;padding:0 14px}header{display:block}.card{padding:16px}h1{font-size:22px}}
</style></head><body><main>
<header><div><h1>회계업무 · 105 서버 이관 검증</h1><p class="muted">172.16.19.105 · 복제 자료 조회</p></div>
<a href="https://172.17.39.121:8080" target="_blank" rel="noopener">기존 운영 서버 열기 ↗</a></header>
<div class="banner"><strong>조회 전용입니다.</strong> ERP 입력·문서 생성·출력·메일 발송은 기존 121 서버에서 계속합니다.
<br><span class="muted">아래 자료는 표시된 시각의 복사본입니다. 운영 전환 전 최신 자료를 다시 동기화합니다.</span></div>
<section class="card" id="login"><h2>기존 계정으로 로그인</h2><form id="loginForm">
<label>아이디<input id="userId" autocomplete="username" required></label>
<label>비밀번호<input id="password" type="password" autocomplete="current-password" required></label>
<button>로그인</button></form><p id="error" role="alert"></p></section>
<section class="card" id="data" hidden><h2>이관 자료 <span class="badge">조회 전용</span></h2>
<p id="user"></p><div id="summary"></div><p id="snapshot" class="muted"></p>
<input id="search" aria-label="자료 검색" placeholder="거래처·번호·담당자 검색"><div id="records">
<table><thead><tr><th>번호</th><th>상태</th><th>거래처</th><th>사업장</th><th>금액</th><th>담당자</th><th>수신일</th><th>세금계산서</th></tr></thead><tbody id="rows"></tbody></table>
</div><p id="notice" class="muted"></p></section></main><script>
let invoices=[];
async function json(url,options={}){const response=await fetch(url,{cache:'no-store',...options});const data=await response.json();if(!response.ok)throw Error(data.detail||'조회 중 오류가 발생했습니다.');return data;}
const labels={waiting:'대기',processing:'처리 중',erp_queued:'ERP 대기',completed:'완료',done:'완료',error:'오류'};
function render(){const query=document.querySelector('#search').value.toLowerCase();const body=document.querySelector('#rows');body.replaceChildren();
 const selected=invoices.filter(row=>[row.id,row.vendor_name,row.processor,row.site_name].join(' ').toLowerCase().includes(query));
 for(const row of selected){const tr=document.createElement('tr');const values=['#'+row.id,labels[row.status]||row.status,row.vendor_name||'-',row.site_name||'-',Number(row.total_sum||0).toLocaleString('ko-KR'),row.processor||'-',row.received_at||'-'];
 values.forEach((value,index)=>{const td=document.createElement('td');td.textContent=value;if(index===4)td.className='amount';tr.append(td);});
 const td=document.createElement('td');if(row.pdf_path){const a=document.createElement('a');a.textContent='PDF 보기';a.href='/api/migration-preview/invoices/'+row.id+'/pdf';a.target='_blank';a.rel='noopener';td.append(a);}else{td.textContent='-';}tr.append(td);body.append(tr);}
 document.querySelector('#notice').textContent='표시 '+selected.length+'건 / 최근 '+invoices.length+'건';}
document.querySelector('#search').addEventListener('input',render);
document.querySelector('#loginForm').addEventListener('submit',async event=>{event.preventDefault();const error=document.querySelector('#error');error.textContent='';
 try{const login=await json('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:document.querySelector('#userId').value,password:document.querySelector('#password').value})});
 const [status,rows]=await Promise.all([json('/api/migration-preview/status'),json('/api/invoices?limit=200')]);invoices=rows;
 document.querySelector('#password').value='';document.querySelector('#user').textContent=login.user.name+' 님';document.querySelector('#login').hidden=true;document.querySelector('#data').hidden=false;
 document.querySelector('#summary').textContent='전체 '+status.invoice_count+'건 · 사용자 '+status.user_count+'명 · 원본 PDF 누락 '+status.missing_invoice_pdfs+'건';
 document.querySelector('#snapshot').textContent='복사 기준: '+(status.snapshot_at||'확인 중')+' · 실제 업무: 기존 121 서버';render();
 }catch(reason){error.textContent=reason.message;}});
</script></body></html>"""
