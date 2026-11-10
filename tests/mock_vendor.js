// Test stand-in for Firebase: same calls the app uses, data kept in localStorage, and the same access rules.
(()=>{
const load=()=>{try{return JSON.parse(localStorage.getItem("__mock")||"null")||{docs:{},accounts:{},cur:null}}catch(_){return {docs:{},accounts:{},cur:null}}};
let st=load();const save=()=>localStorage.setItem("__mock",JSON.stringify(st));
const subs=new Set();const notify=()=>{save();for(const f of [...subs])setTimeout(f,0)};
const clone=v=>v===undefined?undefined:JSON.parse(JSON.stringify(v));
const deny=()=>Object.assign(new Error("Missing or insufficient permissions."),{code:"permission-denied"});
const mainAuth={uid:()=>st.cur};
const adminUid=()=>st.docs["meta/admin"]?.uid;
const isAdmin=()=>!!st.cur&&adminUid()===st.cur;
const me=()=>st.docs["users/"+st.cur];
const isActive=()=>!!st.cur&&me()?.active===true;
function canRead(path,d){const [c,a]=path.split("/");
  if(c==="meta"||c==="logins")return true;
  if(c==="users")return isAdmin()||a===st.cur;
  if(c==="jobcards")return isAdmin()||(isActive()&&d?.techId===me().techId);
  if(c==="vanstock")return isAdmin()||(isActive()&&me().techId===a);
  if(c==="blobs"||c==="settings")return isAdmin()||isActive();
  return false}
function canWrite(path,nw,old){const [c,a]=path.split("/");
  if(c==="meta")return !!st.cur&&!old&&nw?.uid===st.cur;
  if(c==="logins"||c==="users"||c==="settings")return isAdmin();
  if(c==="jobcards")return isAdmin()||(isActive()&&(!old||old.techId===me().techId)&&(!nw||nw.techId===me().techId));
  if(c==="vanstock")return isAdmin()||(isActive()&&me().techId===a);
  if(c==="blobs")return isAdmin()||(isActive()&&!old&&!!nw);
  return false}
function canList(col,wh){const c=col.split("/")[0];
  if(c==="users"||c==="logins"||c==="blobs")return isAdmin();
  if(c==="jobcards")return isAdmin()||(isActive()&&wh.some(w=>w.f==="techId"&&w.v===me().techId));
  if(c==="vanstock")return isAdmin()||(isActive()&&me().techId===col.split("/")[1]);
  return false}
const meta={hasPendingWrites:false,fromCache:false};
const dsnap=path=>{const d=st.docs[path];return {id:path.split("/").pop(),exists:d!==undefined,data:()=>clone(d),metadata:meta}};
const newId=()=>Math.random().toString(36).slice(2,12)+Date.now().toString(36);
const docRef=path=>({id:path.split("/").pop(),path,
  async get(){if(!canRead(path,st.docs[path]))throw deny();return dsnap(path)},
  async set(d){if(!canWrite(path,d,st.docs[path]))throw deny();st.docs[path]=clone(d);notify()},
  async update(p){const o=st.docs[path];if(o===undefined)throw Object.assign(new Error("nf"),{code:"not-found"});const n={...o,...clone(p)};if(!canWrite(path,n,o))throw deny();st.docs[path]=n;notify()},
  async delete(){if(!canWrite(path,null,st.docs[path]))throw deny();delete st.docs[path];notify()},
  onSnapshot(...a){const cb=a.find(x=>typeof x==="function");const er=a.filter(x=>typeof x==="function")[1];
    const f=()=>{if(!canRead(path,st.docs[path])){subs.delete(f);er&&er(deny());return}cb(dsnap(path))};subs.add(f);setTimeout(f,0);return()=>subs.delete(f)}});
const colRef=(path,wh=[])=>{const list=()=>Object.keys(st.docs).filter(k=>k.slice(0,k.lastIndexOf("/"))===path&&wh.every(w=>st.docs[k][w.f]===w.v)).map(k=>dsnap(k));
  return {doc:id=>docRef(path+"/"+(id||newId())),where:(f,o,v)=>colRef(path,[...wh,{f,v}]),orderBy:()=>colRef(path,wh),
    async get(){if(!canList(path,wh))throw deny();return {docs:list(),metadata:meta}},
    onSnapshot(...a){const fns=a.filter(x=>typeof x==="function");const cb=fns[0],er=fns[1];let last=null;
      const f=()=>{if(!canList(path,wh)){subs.delete(f);er&&er(deny());return}const docs=list();const sig=JSON.stringify(docs.map(d=>[d.id,d.data()]));const ch=sig!==last;last=sig;cb({docs,metadata:meta,docChanges:()=>ch?[1]:[]})};
      subs.add(f);setTimeout(f,0);return()=>subs.delete(f)}}};
const fsApi={enablePersistence:async()=>{},doc:docRef,collection:p=>colRef(p)};
function mkAuth(main){const ls=new Set();let cur=main?st.cur:null;
  const user=()=>cur?{uid:cur}:null;const fire=()=>{if(main){st.cur=cur;notify()}for(const f of ls)setTimeout(()=>f(user()),0)};
  return {get currentUser(){return user()},
    onAuthStateChanged(cb){ls.add(cb);setTimeout(()=>cb(user()),0);return()=>ls.delete(cb)},
    async setPersistence(){},
    async signInWithEmailAndPassword(e,p){const a=st.accounts[e];if(!a||a.pw!==p)throw Object.assign(new Error("bad"),{code:"auth/wrong-password"});cur=a.uid;fire();return {user:user()}},
    async createUserWithEmailAndPassword(e,p){if(st.accounts[e])throw Object.assign(new Error("in use"),{code:"auth/email-already-in-use"});if(p.length<6)throw Object.assign(new Error("weak"),{code:"auth/weak-password"});const uid="u_"+newId();st.accounts[e]={uid,pw:p};save();cur=uid;fire();return {user:user()}},
    async signOut(){cur=null;fire()}}}
const apps=[];
function mkApp(name,main){const a=mkAuth(main);const app={name,auth:()=>a,firestore:()=>fsApi};apps.push(app);return app}
const firebase={apps,initializeApp(cfg,name){return mkApp(name||"[DEFAULT]",!name)},firestore:()=>fsApi,auth:Object.assign(()=>apps[0].auth(),{Auth:{Persistence:{NONE:"none"}}})};
window.firebase=firebase;window.__mockState=()=>st;
})();
