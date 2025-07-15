const prizes = [
       { name: "Микс-дринк", rarity: "common", weight: 50 },
       { name: "Содержанка", rarity: "rare", weight: 30 },
       { name: "Клубничный мохито", rarity: "rare", weight: 30 },
       { name: "Ягербул", rarity: "rare", weight: 30 },
       { name: "Зомби", rarity: "epic", weight: 15 },
       { name: "BB Men", rarity: "epic", weight: 15 },
       { name: "Голубая лагуна", rarity: "rare", weight: 30 },
       { name: "Омывшка SHOT", rarity: "epic", weight: 15 },
       { name: "Манго-танго SHOT", rarity: "epic", weight: 15 },
       { name: "10% скидка на стол", rarity: "legendary", weight: 5 }
   ];

   function openTab(tabName) {
       document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
       document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
       document.getElementById(tabName).classList.add('active');
       document.querySelector(`button[onclick="openTab('${tabName}')"]`).classList.add('active');
   }

   // Афиша
   const swiper = new Swiper('.swiper-container', {
       pagination: { el: '.swiper-pagination' },
   });
   fetch('/events')
       .then(res => res.json())
       .then(data => {
           const wrapper = document.querySelector('.swiper-wrapper');
           data.forEach(event => {
               const slide = document.createElement('div');
               slide.className = 'swiper-slide';
               slide.innerHTML = `<img src="${event.image_url}" alt="${event.title}"><p>${event.title}</p>`;
               wrapper.appendChild(slide);
           });
           swiper.update();
       });

   // Рулетка
   const canvas = document.getElementById('wheelCanvas');
   const ctx = canvas.getContext('2d');
   let angle = 0;
   let spinning = false;

   function drawWheel() {
       const totalWeight = prizes.reduce((sum, prize) => sum + prize.weight, 0);
       let currentAngle = 0;
       prizes.forEach(prize => {
           const arc = (prize.weight / totalWeight) * 2 * Math.PI;
           ctx.beginPath();
           ctx.arc(150, 150, 140, currentAngle, currentAngle + arc);
           ctx.lineTo(150, 150);
           ctx.fillStyle = prize.rarity === 'common' ? '#00f0ff' : 
                          prize.rarity === 'rare' ? '#ff00ff' : 
                          prize.rarity === 'epic' ? '#ff9900' : '#ff0000';
           ctx.fill();
           ctx.save();
           ctx.translate(150, 150);
           ctx.rotate(currentAngle + arc / 2);
           ctx.fillStyle = '#fff';
           ctx.fillText(prize.name, 60, 10);
           ctx.restore();
           currentAngle += arc;
       });
   }

   document.getElementById('spinButton').addEventListener('click', () => {
       if (spinning) return;
       const lastSpin = localStorage.getItem('lastSpin');
       if (lastSpin && Date.now() - lastSpin < 24 * 60 * 60 * 1000) return;
       spinning = true;
       const spinAngle = Math.random() * 360 + 720;
       let start = null;
       function animate(timestamp) {
           if (!start) start = timestamp;
           const progress = (timestamp - start) / 2000;
           angle = spinAngle * progress;
           ctx.clearRect(0, 0, canvas.width, canvas.height);
           drawWheel();
           if (progress < 1) {
               requestAnimationFrame(animate);
           } else {
               spinning = false;
               localStorage.setItem('lastSpin', Date.now());
               let totalWeight = 0;
               prizes.forEach(prize => totalWeight += prize.weight);
               let winnerAngle = (angle % 360) * Math.PI / 180;
               let currentAngle = 0;
               let winner = null;
               for (const prize of prizes) {
                   const arc = (prize.weight / totalWeight) * 2 * Math.PI;
                   if (winnerAngle >= currentAngle && winnerAngle < currentAngle + arc) {
                       winner = prize;
                   }
                   currentAngle += arc;
               }
               fetch('/save_prize', {
                   method: 'POST',
                   headers: { 'Content-Type': 'application/json' },
                   body: JSON.stringify({ user_id: Telegram.WebApp.initDataUnsafe.user.id, prize: winner.name })
               });
               document.getElementById('myPrizes').style.display = 'block';
           }
       }
       requestAnimationFrame(animate);
   });

   // Таймер
   function updateTimer() {
       const lastSpin = localStorage.getItem('lastSpin');
       if (!lastSpin) return;
       const timeLeft = 24 * 60 * 60 * 1000 - (Date.now() - lastSpin);
       if (timeLeft <= 0) {
           document.getElementById('timer').innerText = '';
           return;
       }
       const hours = Math.floor(timeLeft / 3600000);
       const minutes = Math.floor((timeLeft % 3600000) / 60000);
       const seconds = Math.floor((timeLeft % 60000) / 1000);
       document.getElementById('timer').innerText = `${hours}:${minutes}:${seconds}`;
   }
   setInterval(updateTimer, 1000);

   // Профиль
   fetch('/profile', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ user_id: Telegram.WebApp.initDataUnsafe.user.id })
   }).then(res => res.json()).then(data => {
       const profileInfo = document.getElementById('profileInfo');
       profileInfo.innerHTML = `
           <p>Имя: ${data.first_name}</p>
           <p>Фамилия: ${data.last_name}</p>
           <p>Номер: ${data.phone || 'Не указан'}</p>
           <p>Username: ${data.username}</p>
       `;
       if (data.role === 'promoter' || data.role === 'employee') {
           document.getElementById('generateQr').style.display = 'block';
           document.getElementById('promoterStats').style.display = 'block';
           document.getElementById('promoterStats').innerHTML = `
               <p>Приглашено за неделю: ${data.invited_week}</p>
               <p>Приглашено за месяц: ${data.invited_month}</p>
           `;
       }
       if (data.role === 'employee') {
           document.getElementById('scanQr').style.display = 'block';
       }
   });

   // Мои призы
   document.getElementById('myPrizes').addEventListener('click', () => {
       fetch('/prizes', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ user_id: Telegram.WebApp.initDataUnsafe.user.id })
       }).then(res => res.json()).then(data => {
           const prizesList = document.getElementById('prizesList');
           prizesList.style.display = 'block';
           prizesList.innerHTML = data.map(prize => `
               <p>${prize.prize} (до ${prize.expiry}) 
               <button onclick="showQr('${prize.id}')">Активировать</button></p>
           `).join('');
       });
   });

   function showQr(prizeId) {
       fetch('/generate_qr', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({ prize_id: prizeId })
       }).then(res => res.json()).then(data => {
           const img = document.createElement('img');
           img.src = data.qr_url;
           document.body.innerHTML = '';
           document.body.appendChild(img);
       });
   }

   drawWheel();
   openTab('events');