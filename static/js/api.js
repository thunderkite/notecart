const api = (()=>{
    async function request(path, method='GET', data=null){
        const opts = {method, headers:{'Accept':'application/json'}};
        if(data){
            if(!(data instanceof FormData)){
                opts.headers['Content-Type']='application/json';
                opts.body=JSON.stringify(data);
            } else { opts.body = data; }
        }
        const res = await fetch('/api'+path, opts);
        const json = await res.json().catch(()=>({}));
        return res.ok? Object.assign(json,{ok:true}): Object.assign(json,{ok:false});
    }
    return {
        get: (p)=> request(p,'GET'),
        post: (p,d)=> request(p,'POST',d),
        put: (p,d)=> request(p,'PUT',d),
        del: (p)=> request(p,'DELETE'),
        request
    };
})();

function showToast(msg, timeout=2000){
    const t = document.getElementById('toast');
    t.innerText = msg; t.style.display='block';
    setTimeout(()=> t.style.display='none', timeout);
}

window.api = api; window.showToast = showToast;

// attach logout if button present
window.addEventListener('load', ()=>{
    const btn = document.getElementById('logoutBtn');
    if(!btn) return;
    btn.hidden = false;
    btn.addEventListener('click', async ()=>{
        const r = await api.post('/auth/logout');
        if(r.ok){ showToast('Вы вышли'); setTimeout(()=>location.href='/',400); }
    });
});
