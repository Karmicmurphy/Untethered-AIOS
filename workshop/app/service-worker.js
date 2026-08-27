const C="twis-holo-full-v27-music-loop-deck-v1";
const F=[
  "./",
  "./index.html",
  "./assets/style.css",
  "./assets/music-studio.css",
  "./assets/video-workstation.css",
  "./assets/media-workspace.css",
  "./assets/local-worker-kit.css",
  "./assets/builder-workspace.css",
  "./assets/model-bay.css",
  "./assets/capability-bay.css",
  "./assets/shell-0.14.css",
  "./assets/shell-0.14-layout.css",
  "./assets/room-system.css",
  "./assets/ui-coherence.css",
  "./assets/remote-access.css",
  "./assets/navigation-state.js",
  "./assets/app.js",
  "./assets/media-workspace.js",
  "./assets/music-engine.js",
  "./assets/music-room.js",
  "./assets/video-workstation.js",
  "./assets/talk-room.js",
  "./assets/write-room.js",
  "./assets/local-worker-kit.js",
  "./assets/builder-workspace.js",
  "./assets/model-bay.js",
  "./assets/capability-bay.js",
  "./assets/shell-0.14.js",
  "./assets/room-system.js",
  "./assets/ui-coherence.js",
  "./assets/remote-access.js",
  "./assets/worker-harness-view.js",
  "./assets/worker-harness.js",
  "./assets/flashriver-import-ui.js",
  "./assets/flashriver-review.js",
  "./modules/modules.json"
];

self.addEventListener("install",event=>{
  event.waitUntil(caches.open(C).then(cache=>cache.addAll(F)).then(()=>self.skipWaiting()));
});

self.addEventListener("activate",event=>{
  event.waitUntil((async()=>{
    const keys=await caches.keys();
    const stale=keys.filter(key=>key.startsWith("twis-holo-full-")&&key!==C);
    await Promise.all(stale.map(key=>caches.delete(key)));
    await self.clients.claim();
    if(stale.length){
      const windows=await self.clients.matchAll({type:"window"});
      await Promise.all(windows.map(client=>client.navigate(client.url)));
    }
  })());
});

self.addEventListener("fetch",event=>{
  const request=event.request;
  const url=new URL(request.url);
  if(request.method!=="GET"||url.origin!==self.location.origin||url.pathname.startsWith("/api/"))return;
  event.respondWith(fetch(request).then(async response=>{
    if(response.ok){
      const cache=await caches.open(C);
      await cache.put(request,response.clone());
    }
    return response;
  }).catch(()=>caches.match(request)));
});
