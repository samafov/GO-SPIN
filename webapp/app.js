// ЗАМЕНИ на адрес своего backend (тот же, что слушает backend/app.py)
const API_BASE = "https://YOUR-BACKEND-DOMAIN.example.com";

const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const initData = tg?.initData || "";

// ---------- утилиты ----------
function apiFetch(path, options = {}) {
  return fetch(API_BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Init-Data": initData,
      ...(options.headers || {}),
    },
  }).then(async (res) => {
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
  });
}

function showToast(text) {
  const toast = document.getElementById("toast");
  toast.textContent = text;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2600);
}

function formatCooldown(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

// ---------- вкладки ----------
document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`panel-${btn.dataset.tab}`).classList.add("active");
    if (btn.dataset.tab === "inventory") loadInventory();
  });
});

// ---------- витрина (фиксированные цены) ----------
async function loadShop() {
  const grid = document.getElementById("shopGrid");
  try {
    const { items } = await apiFetch("/api/shop");
    grid.innerHTML = "";
    items.forEach((item) => {
      const card = document.createElement("div");
      card.className = "item-card";
      card.innerHTML = `
        <div class="item-emoji">${item.emoji}</div>
        <div class="item-title">${item.title}</div>
        <div class="item-price">✦ ${item.price_stars}</div>
        <button class="buy-btn">Купить</button>
      `;
      card.querySelector(".buy-btn").addEventListener("click", () => buyItem(item));
      grid.appendChild(card);
    });
  } catch (e) {
    grid.innerHTML = `<p class="empty-state">Не удалось загрузить витрину: ${e.message}</p>`;
  }
}

function buyItem(item) {
  if (!tg) {
    showToast("Открой это внутри Telegram, чтобы оплатить.");
    return;
  }
  // Mini App не проводит платёж сама — она просит бота выставить счёт
  // на фиксированную сумму в Stars. Никакой случайности здесь нет.
  tg.sendData(JSON.stringify({ action: "buy", item_id: item.item_id }));
}

// ---------- тираж / колесо (бесплатно, раз в 24ч) ----------
let cooldownInterval = null;

async function loadWheel() {
  const spinBtn = document.getElementById("spinBtn");
  const cooldownText = document.getElementById("cooldownText");
  const track = document.getElementById("reelTrack");

  try {
    const status = await apiFetch("/api/wheel/status");
    renderReel(status.possible_items);

    if (cooldownInterval) clearInterval(cooldownInterval);

    if (status.can_spin) {
      spinBtn.disabled = false;
      spinBtn.textContent = "Крутить бесплатно";
      cooldownText.textContent = "";
    } else {
      spinBtn.disabled = true;
      let secondsLeft = status.seconds_left;
      const tick = () => {
        spinBtn.textContent = "Уже потрачен на сегодня";
        cooldownText.textContent = `Следующий тираж через ${formatCooldown(secondsLeft)}`;
        secondsLeft -= 1;
        if (secondsLeft < 0) { clearInterval(cooldownInterval); loadWheel(); }
      };
      tick();
      cooldownInterval = setInterval(tick, 1000);
    }
  } catch (e) {
    spinBtn.disabled = true;
    spinBtn.textContent = "Ошибка загрузки";
  }
}

function renderReel(items, highlightId = null) {
  const track = document.getElementById("reelTrack");
  track.style.transition = "none";
  track.style.transform = "translateX(0)";
  track.innerHTML = "";
  // повторяем список несколько раз, чтобы было куда "прокручивать"
  const repeated = Array(6).fill(items).flat();
  repeated.forEach((item) => {
    const el = document.createElement("div");
    el.className = "reel-item" + (item.item_id === highlightId ? " winner" : "");
    el.innerHTML = `<div class="emoji">${item.emoji}</div><div class="name">${item.title}</div>`;
    track.appendChild(el);
  });
}

async function spin() {
  const spinBtn = document.getElementById("spinBtn");
  spinBtn.disabled = true;
  try {
    const { won_item } = await apiFetch("/api/wheel/spin", { method: "POST" });

    // анимация прокрутки к случайной позиции, затем показываем выигрыш
    const track = document.getElementById("reelTrack");
    const itemWidth = 94; // width + gap
    const stopIndex = 3 * 9 + Math.floor(Math.random() * 9); // едем в глубину повторов
    track.style.transition = "transform 3.5s cubic-bezier(0.12,0.85,0.15,1)";
    track.style.transform = `translateX(-${stopIndex * itemWidth}px)`;

    setTimeout(() => {
      showToast(`🎉 Выпало: ${won_item.emoji} ${won_item.title}`);
      tg?.HapticFeedback?.notificationOccurred("success");
      loadWheel();
    }, 3600);
  } catch (e) {
    showToast(e.message);
    loadWheel();
  }
}

document.getElementById("spinBtn").addEventListener("click", spin);

// ---------- коллекция ----------
async function loadInventory() {
  const list = document.getElementById("inventoryList");
  try {
    const { inventory } = await apiFetch("/api/inventory");
    if (inventory.length === 0) {
      list.innerHTML = `<p class="empty-state">Пока пусто — загляни в витрину или крути тираж.</p>`;
      return;
    }
    list.innerHTML = inventory
      .map(
        (row) => `
        <div class="inventory-row">
          <div class="emoji">${row.emoji}</div>
          <div class="meta">
            <div class="title">${row.title}</div>
            <div class="source">${row.source === "purchase" ? "Куплено" : "Выиграно в тираже"}</div>
          </div>
        </div>`
      )
      .join("");
  } catch (e) {
    list.innerHTML = `<p class="empty-state">Не удалось загрузить коллекцию: ${e.message}</p>`;
  }
}

// ---------- старт ----------
loadShop();
loadWheel();
