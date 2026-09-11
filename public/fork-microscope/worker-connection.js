/* Static dashboard transport. Models and evidence remain on the user's worker. */
(() => {
  const key = 'fork-worker-session-v1';
  const nativeFetch = window.fetch.bind(window);
  let config = null, generation = 0;
  try { config = JSON.parse(sessionStorage.getItem(key) || 'null'); } catch {}
  const local = ['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname);
  function endpoint(value) {
    const url = new URL(value);
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || !['','/'].includes(url.pathname)) throw Error('Use a worker origin, such as https://gpu.example.org, without a path or credentials.');
    if (url.protocol === 'http:' && !['127.0.0.1','localhost','[::1]'].includes(url.hostname)) throw Error('A remote worker must use HTTPS. For a VM over SSH, forward its port to localhost.');
    return url.origin;
  }
  try { if (config) config = {url:endpoint(config.url), token:String(config.token || '')}; } catch { config=null; }
  window.workerConnection = () => ({url:config?.url || (local ? location.origin : null), connected:!!config || local});
  window.workerFetch = async (input, options={}) => {
    if (typeof input !== 'string' || !input.startsWith('/api/')) return nativeFetch(input, options);
    const current=generation, origin=config?.url || (local ? location.origin : null);
    if (!origin) throw Error('Connect your local or GPU worker using Connect worker above. This website does not run models.');
    const headers=new Headers(options.headers);
    if (config?.token) headers.set('Authorization','Bearer '+config.token);
    const response=await nativeFetch(origin+input,{...options,headers,credentials:'omit',referrerPolicy:'no-referrer'});
    if (current!==generation) throw Error('Worker changed. Discarded a response from the previous worker.');
    return response;
  };
  function persist(value) {
    config=value;generation++;
    try { if (value) sessionStorage.setItem(key,JSON.stringify(value)); else sessionStorage.removeItem(key); } catch {}
    draw();window.dispatchEvent(new Event('worker-connection-change'));
  }
  let status, button;
  function draw() {
    if (!status) return;
    status.textContent=config ? `Worker · ${new URL(config.url).host}` : local ? 'Worker · this installation' : 'Your compute · not connected';
    button.textContent=config ? 'Change worker' : 'Connect worker';
  }
  function init() {
    const style=document.createElement('style');
    style.textContent=`.worker-strip{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:9px max(16px,3vw);font-size:13px;line-height:1.5;font-family:inherit;background:#101820;color:#c8d7df;border-bottom:1px solid #30424e}.worker-strip button,.worker-dialog button{border:1px solid #688496;background:#1c303d;color:#fff;border-radius:8px;padding:8px 13px;cursor:pointer;font:inherit}.worker-dialog{box-sizing:border-box;width:min(560px,calc(100% - 24px));max-height:90vh;overflow:auto;padding:26px;border:1px solid #66808f;border-radius:16px;background:#101d26;color:#e8eff4;font-size:14px;line-height:1.6;font-family:inherit}.worker-dialog::backdrop{background:#020911d9}.worker-dialog h2{font-size:23px;margin-top:0}.worker-dialog label{display:block;margin:16px 0}.worker-dialog input{box-sizing:border-box;display:block;width:100%;padding:11px;margin-top:5px;background:#071219;color:white;border:1px solid #586c77;border-radius:7px;font:inherit}.worker-dialog .worker-actions{display:flex;gap:8px;flex-wrap:wrap}.worker-dialog [role=status]{white-space:pre-wrap;color:#e8d4a8}.worker-dialog code{overflow-wrap:anywhere}.worker-dialog summary{cursor:pointer}.worker-dialog small{color:#b7c7d0}`;
    document.head.append(style);
    const bar=document.createElement('div');bar.className='worker-strip';
    status=document.createElement('span');button=document.createElement('button');button.type='button';
    bar.append(status,button);document.body.prepend(bar);
    const dialog=document.createElement('dialog');dialog.className='worker-dialog';dialog.setAttribute('aria-labelledby','worker-title');
    dialog.innerHTML=`<h2 id="worker-title">Connect your compute</h2><p>The dashboard opens your worker’s models, prompt sets and evidence. Your GPU can be in your computer or with your VM provider.</p>
      <p><a href="https://github.com/iPolluxx/fork-microscope/blob/main/docs/GETTING-STARTED.md" target="_blank" rel="noopener noreferrer" style="color:#c8e5fa">Install and start your worker ↗</a> — the startup command generates your token and prints the URL.</p><form><label>Worker URL<input name="url" type="url" placeholder="http://127.0.0.1:8767" required autocomplete="off"></label><label>Worker access token<input name="token" type="password" autocomplete="off" placeholder="Token configured on your worker"></label><small>The connection and token stay in this tab’s session storage. Disconnect clears them. Never enter a cloud-provider API key here.</small>
      <p role="status" aria-live="polite"></p><div class="worker-actions"><button type="submit">Test and connect</button><button type="button" data-disconnect>Disconnect</button><button type="button" data-close>Close</button></div></form>
      <details><summary>How the worker connects</summary><p>Start Fork Microscope on your hardware. Allow this website’s origin on that worker and set its worker access token. For a VM, use an HTTPS endpoint or an SSH tunnel to localhost. Your browser may ask for local-network permission.</p><p>Allowed dashboard origin: <code data-origin></code></p><p>If your browser blocks localhost access from a hosted site, open the dashboard served by your worker itself. No GPU runs start when connecting.</p></details>`;
    dialog.querySelector('[data-origin]').textContent=location.origin;
    document.body.append(dialog);
    const form=dialog.querySelector('form'), note=dialog.querySelector('[role=status]');
    button.onclick=()=>{form.elements.url.value=config?.url || (local?location.origin:'http://127.0.0.1:8767');form.elements.token.value=config?.token || '';note.textContent='';dialog.showModal();};
    dialog.querySelector('[data-close]').onclick=()=>dialog.close();
    dialog.querySelector('[data-disconnect]').onclick=()=>{persist(null);dialog.close();};
    form.onsubmit=async event=>{
      event.preventDefault();const submit=form.querySelector('[type=submit]');submit.disabled=true;
      try {
        const url=endpoint(form.elements.url.value.trim()),token=form.elements.token.value.trim();
        note.textContent='Checking worker access…';
        const headers=token?{Authorization:'Bearer '+token}:{};
        const response=await nativeFetch(url+'/api/live/status',{headers,credentials:'omit',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(15000)});
        const value=await response.json();
        if (!response.ok) throw Error(value.error || 'Worker refused this connection.');
        if (!value.job || !value.runtime) throw Error('This is not a compatible Fork Microscope worker.');
        persist({url,token});dialog.close();
      } catch (error) {note.textContent=error.message==='Failed to fetch'?'Cannot reach the worker. Check its URL, HTTPS or SSH tunnel, allowed dashboard origin, and browser local-network permission.':error.message;}
      finally {submit.disabled=false;}
    };
    draw();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
