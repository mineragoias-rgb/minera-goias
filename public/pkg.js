/* Shared loader for the authenticated data packages. Each one is fetched once per page load, so the Overview and the
   Panorama read the same copy of /panorama, /precos, /atlas and /dashboard instead of downloading them twice. */
(()=>{'use strict';
const cache=new Map();
const get=path=>{if(!cache.has(path))cache.set(path,api(path));return cache.get(path)};
// For packages a tab can live without: a failure gives null and can be tried again later.
const tryGet=async path=>{try{return await get(path)}catch(e){cache.delete(path);return null}};
window.PKG={get,tryGet};
})();
