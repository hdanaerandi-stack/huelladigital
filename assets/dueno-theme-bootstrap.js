(function(){
  'use strict';
  var allowed=['normal','futurista','futurista-neon','futurista-dorado','minimal-pastel','oceano-turquesa','costa-natural','bosque-verde','brote-oliva','negro-profundo','personalizado'];
  function read(){
    var keys=['huellaAppearance:dueno','huellaAppearance'];
    for(var i=0;i<keys.length;i++){
      try{
        var raw=localStorage.getItem(keys[i]);
        if(!raw) continue;
        var obj=JSON.parse(raw);
        var t=obj&&typeof obj.theme==='string'?obj.theme:'normal';
        if(t==='future') t='futurista';
        if(allowed.indexOf(t)<0) t='normal';
        return {theme:t,motion:!(obj&&obj.motion===false)};
      }catch(e){}
    }
    return {theme:'normal',motion:true};
  }
  function apply(){
    var s=read(), root=document.documentElement;
    root.setAttribute('data-huella-role','dueno');
    root.setAttribute('data-huella-theme',s.theme);
    root.setAttribute('data-huella-motion',s.motion?'on':'off');
    Array.prototype.slice.call(root.classList).forEach(function(c){if(c.indexOf('huella-theme-')===0)root.classList.remove(c)});
    root.classList.add('huella-theme-'+s.theme);
    if(document.body){
      document.body.setAttribute('data-huella-role','dueno');
      document.body.setAttribute('data-huella-theme',s.theme);
      document.body.setAttribute('data-huella-motion',s.motion?'on':'off');
      Array.prototype.slice.call(document.body.classList).forEach(function(c){if(c.indexOf('huella-theme-')===0)document.body.classList.remove(c)});
      document.body.classList.add('huella-theme-'+s.theme,'huella-dueno-theme-active');
    }
  }
  window.HuellaOwnerThemeBootstrap={apply:apply,read:read};
  apply();
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',apply);
  window.addEventListener('pageshow',apply);
  window.addEventListener('storage',function(e){if(!e.key||e.key==='huellaAppearance:dueno'||e.key==='huellaAppearance')apply()});
  window.addEventListener('huella:appearancechange',apply);
})();
