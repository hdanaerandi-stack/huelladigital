(function(){
  'use strict';
  const DB_NAME = 'HuellaMediaDB';
  const DB_VERSION = 1;
  const STORE = 'productMedia';
  let dbPromise;

  function openDB(){
    if(dbPromise) return dbPromise;
    dbPromise = new Promise((resolve,reject)=>{
      if(!('indexedDB' in window)){
        reject(new Error('IndexedDB no disponible'));
        return;
      }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        let store;
        if(!db.objectStoreNames.contains(STORE)){
          store = db.createObjectStore(STORE, {keyPath:'id'});
          store.createIndex('productId','productId',{unique:false});
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error || new Error('No se pudo abrir la base multimedia'));
    });
    return dbPromise;
  }

  async function list(productId){
    const db = await openDB();
    return new Promise((resolve,reject)=>{
      const tx = db.transaction(STORE,'readonly');
      const idx = tx.objectStore(STORE).index('productId');
      const req = idx.getAll(String(productId));
      req.onsuccess = () => resolve((req.result || []).sort((a,b)=>(a.order||0)-(b.order||0)));
      req.onerror = () => reject(req.error);
    });
  }

  async function clear(productId){
    const items = await list(productId);
    if(!items.length) return;
    const db = await openDB();
    await new Promise((resolve,reject)=>{
      const tx = db.transaction(STORE,'readwrite');
      const store = tx.objectStore(STORE);
      items.forEach(item => store.delete(item.id));
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }

  async function replace(productId, files){
    const cleanFiles = Array.from(files || []).slice(0,5).filter(f => /^image\//.test(f.type) || /^video\//.test(f.type));
    await clear(productId);
    if(!cleanFiles.length) return [];
    const db = await openDB();
    const saved = [];
    await new Promise((resolve,reject)=>{
      const tx = db.transaction(STORE,'readwrite');
      const store = tx.objectStore(STORE);
      cleanFiles.forEach((file,index)=>{
        const item = {
          id: `${String(productId)}:${Date.now()}:${index}`,
          productId: String(productId),
          order:index,
          name:file.name || `archivo-${index+1}`,
          type:file.type || 'application/octet-stream',
          size:file.size || 0,
          blob:file,
          createdAt:new Date().toISOString()
        };
        store.put(item);
        saved.push({id:item.id, type:item.type, name:item.name, size:item.size, order:index});
      });
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    return saved;
  }

  function objectURL(item){
    return item && item.blob ? URL.createObjectURL(item.blob) : '';
  }

  window.HuellaMedia = {openDB,list,clear,replace,objectURL};
})();
