// Собственный код стенда. Распознавание изображения уже реализовано в AR.js.
if (window.AFRAME && window.ARjs) {
  // 1. Компонент строит колесо из цилиндров и 12 прямоугольных зубьев.
  AFRAME.registerComponent('gear', {
    schema: { color: { default: '#f5b544' } },
    init: function () {
      const addPart = (tag, attributes) => {
        const part = document.createElement(tag);
        for (const [name, value] of Object.entries(attributes)) {
          part.setAttribute(name, value);
        }
        this.el.appendChild(part);
      };
      addPart('a-cylinder', {
        radius: 0.255, height: 0.1, color: this.data.color, 'segments-radial': 48
      });
      for (let i = 0; i < 12; i++) {
        const angle = i * 2 * Math.PI / 12;
        addPart('a-box', {
          width: 0.085, height: 0.1, depth: 0.07, color: this.data.color,
          position: `${Math.cos(angle) * 0.2925} 0 ${Math.sin(angle) * 0.2925}`,
          rotation: `0 ${-i * 30} 0`
        });
      }
      addPart('a-cylinder', { radius: 0.065, height: 0.18, color: '#e8edf4' });
      // Светлая отметка на поверхности помогает заметить вращение колеса.
      addPart('a-box', {
        width: 0.12, height: 0.012, depth: 0.025,
        position: '0.16 0.056 0', color: '#ffffff'
      });
    }
  });
}

// 2. Состояние приложения и реакция на события камеры и маркера.
const statusText = document.querySelector('#status');
const toggleButton = document.querySelector('#toggle');
let running = false;
let markerVisible = false;
let failed = false;

function showError(message) {
  failed = true;
  toggleButton.disabled = true;
  statusText.textContent = message;
  statusText.dataset.error = 'true';
}

function updateControls() {
  if (failed) return;
  toggleButton.disabled = !markerVisible;
  toggleButton.textContent = running ? 'Стоп' : 'Пуск';
  toggleButton.setAttribute('aria-pressed', String(running));
  statusText.textContent = markerVisible
    ? (running ? 'Маркер найден · Механизм работает' : 'Маркер найден · Готов к запуску')
    : 'Наведите камеру на маркер Hiro целиком';
}

// 3. Сцену создаём только при наличии библиотек и безопасного доступа к камере.
if (!window.AFRAME || !window.ARjs) {
  showError('Не загрузились библиотеки. Проверьте папку vendor и обновите страницу.');
} else if (location.protocol === 'file:') {
  showError('Откройте страницу через start.bat и http://localhost:8000, а не как файл.');
} else if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
  showError('Камера недоступна. На ПК используйте localhost, на смартфоне — HTTPS.');
} else {
  const scene = document.querySelector('#scene-template').content.cloneNode(true);
  const marker = scene.querySelector('#marker');
  const leftGear = scene.querySelector('#left-gear');
  const rightGear = scene.querySelector('#right-gear');

  window.addEventListener('camera-init', updateControls);
  window.addEventListener('camera-error', () => {
    showError('Нет доступа к камере. Разрешите доступ, закройте другие приложения с камерой и обновите страницу.');
  });
  marker.addEventListener('markerFound', () => {
    markerVisible = true;
    updateControls();
  });
  marker.addEventListener('markerLost', () => {
    markerVisible = false;
    updateControls();
  });
  toggleButton.addEventListener('click', () => {
    running = !running;
    updateControls();
  });
  document.body.appendChild(scene);

  // 4. На каждом кадре изменяем углы на одинаковые величины разных знаков.
  let previousTime = null;
  function animate(time) {
    // Время кадра переводим из миллисекунд в секунды. Ограничение убирает
    // резкий скачок угла после возвращения на вкладку браузера.
    const seconds = previousTime === null ? 0 : Math.min((time - previousTime) / 1000, 0.05);
    previousTime = time;
    if (running && markerVisible && !failed) {
      const step = seconds * Math.PI / 6; // 30 градусов в секунду.
      leftGear.object3D.rotation.y += step;
      rightGear.object3D.rotation.y -= step;
    }
    requestAnimationFrame(animate);
  }
  requestAnimationFrame(animate);
}
