(function(){
  'use strict';

  var ALLOWED=[
    'normal','futurista','futurista-neon','futurista-dorado',
    'minimal-pastel','oceano-turquesa','costa-natural','bosque-verde',
    'brote-oliva','negro-profundo','personalizado'
  ];

  function normalize(theme){
    if(theme==='future') theme='futurista';
    return ALLOWED.indexOf(theme)>=0 ? theme : 'normal';
  }

  function cookieValue(name){
    try{
      var prefix=name+'=';
      var part=document.cookie.split(';').map(function(x){return x.trim();}).find(function(x){return x.indexOf(prefix)===0;});
      return part ? decodeURIComponent(part.slice(prefix.length)) : '';
    }catch(e){ return ''; }
  }

  function read(){
    // Si huella-ui.js ya está cargado, usar su valor actual como fuente principal.
    try{
      if(window.HuellaAppearance && typeof window.HuellaAppearance.get==='function'){
        var current=window.HuellaAppearance.get();
        if(current && ALLOWED.indexOf(current.theme)>=0){
          return {theme:normalize(current.theme),motion:current.motion!==false};
        }
      }
    }catch(e){}

    // Respaldo en cookie por perfil.
    try{
      var rawCookie=cookieValue('huellaAppearance_dueno');
      if(rawCookie){
        var c=JSON.parse(rawCookie);
        return {theme:normalize(c.theme),motion:c.motion!==false};
      }
    }catch(e){}

    // Respaldo en localStorage.
    var keys=['huellaAppearance:dueno','huellaAppearance'];
    for(var i=0;i<keys.length;i++){
      try{
        var raw=localStorage.getItem(keys[i]);
        if(!raw) continue;
        var obj=JSON.parse(raw);
        return {theme:normalize(obj && obj.theme),motion:!(obj && obj.motion===false)};
      }catch(e){}
    }

    return {theme:'normal',motion:true};
  }

  function removeThemeClasses(el){
    if(!el || !el.classList) return;
    Array.prototype.slice.call(el.classList).forEach(function(c){
      if(c.indexOf('huella-theme-')===0) el.classList.remove(c);
    });
  }

  function apply(){
    var s=read();
    var root=document.documentElement;
    root.setAttribute('data-huella-role','dueno');
    root.setAttribute('data-huella-theme',s.theme);
    root.setAttribute('data-huella-motion',s.motion?'on':'off');
    removeThemeClasses(root);
    root.classList.add('huella-theme-'+s.theme);

    if(document.body){
      document.body.setAttribute('data-huella-role','dueno');
      document.body.setAttribute('data-huella-theme',s.theme);
      document.body.setAttribute('data-huella-motion',s.motion?'on':'off');
      removeThemeClasses(document.body);
      document.body.classList.add('huella-theme-'+s.theme,'huella-dueno-modulo');
    }
  }

  window.HuellaDuenoModuloTema={read:read,apply:apply};
  apply();

  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded',function(){
      apply();
      requestAnimationFrame(apply);
      setTimeout(apply,60);
    });
  }else{
    requestAnimationFrame(apply);
    setTimeout(apply,60);
  }

  window.addEventListener('pageshow',apply);
  window.addEventListener('storage',function(e){
    if(!e.key || e.key==='huellaAppearance:dueno' || e.key==='huellaAppearance') apply();
  });
  window.addEventListener('huella:appearancechange',function(){
    apply();
    requestAnimationFrame(apply);
  });
})();
