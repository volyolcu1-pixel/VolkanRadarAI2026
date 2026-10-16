import {initializeApp} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js';
import {getMessaging,getToken,isSupported} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging.js';
const config={"apiKey": "AIzaSyDm3x15uBcG6KED9GvHoK8PCa4E4FGzBjQ", "authDomain": "volkan-d60a7.firebaseapp.com", "projectId": "volkan-d60a7", "storageBucket": "volkan-d60a7.firebasestorage.app", "messagingSenderId": "638334239653", "appId": "1:638334239653:web:19c6dc0b836499f4d2de4c"};
const vapidKey='BGKbiPNWR4Mx8Jtbv5kT0VvohzW_wffJK4iYB0kZRSiHTQx4mXcYkerFgfQMYt05ZZpV1-KsKvyt8j94FS7GyZs';
const button=document.getElementById('enable-push');
const status=document.getElementById('push-status');
button?.addEventListener('click',async()=>{
  button.disabled=true;
  try {
    if(!('Notification' in window)||!('serviceWorker' in navigator)||!(await isSupported())) throw Error('Tarayıcı bildirimleri desteklemiyor.');
    const permission=await Notification.requestPermission();
    if(permission!=='granted'){status.textContent='Bildirim izni verilmedi.';return;}
    const registration=await navigator.serviceWorker.register('./sw.js');
    const token=await getToken(getMessaging(initializeApp(config)),{vapidKey,serviceWorkerRegistration:registration});
    if(!token)throw Error('Cihaz kayıt anahtarı alınamadı.');
    status.textContent='Telefon bildirimi izni hazır. Otomatik alarm gönderimi için güvenli sunucu bağlantısı henüz kurulmadı.';
  } catch(e){status.textContent='Kurulum hatası: '+(e?.message||String(e));}
  finally{button.disabled=false;}
});
