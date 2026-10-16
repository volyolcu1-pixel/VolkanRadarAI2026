importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');
firebase.initializeApp({"apiKey": "AIzaSyDm3x15uBcG6KED9GvHoK8PCa4E4FGzBjQ", "authDomain": "volkan-d60a7.firebaseapp.com", "projectId": "volkan-d60a7", "storageBucket": "volkan-d60a7.firebasestorage.app", "messagingSenderId": "638334239653", "appId": "1:638334239653:web:19c6dc0b836499f4d2de4c"});
const messaging=firebase.messaging();
messaging.onBackgroundMessage(payload=>{
  if(payload.notification) return;
  const d=payload.data||{};
  self.registration.showNotification(d.title||'Volkan Kripto Radar',{
    body:d.body||'Yeni radar uyarısı',icon:'./icon.svg',
    data:{url:d.url||'./'}
  });
});
self.addEventListener('notificationclick',event=>{
  event.notification.close();
  const url=new URL(event.notification.data?.url||'./',self.registration.scope).href;
  event.waitUntil(clients.openWindow(url));
});
