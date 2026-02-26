/* ====================================================
   Travel Presenter — 編輯器邏輯
   ==================================================== */

const Editor = {
  currentDay: 0,

  /* ═══════════════════════════════════════════════
     表單 → 填入資料 (populate)
     ═══════════════════════════════════════════════ */
  populate(data) {
    // 基本資訊
    this._val("f-title", data.title || "");
    this._val("f-subtitle", data.subtitle || "");
    this._val("f-company", data.company || "");
    this._val("f-destination", data.destination || "");
    this._val("f-date_range", data.date_range || "");
    this._val("f-quote", data.quote || "");
    this._val("f-quote_en", data.quote_en || "");
    this._val("f-cover_image", data.cover_image || "");

    // 封面縮圖
    if (data.cover_image && App.sessionId) {
      const thumb = document.getElementById("cover-thumb");
      thumb.src = `/uploads/${App.sessionId}/${data.cover_image}`;
      thumb.style.display = "";
    }

    // 航班
    this.renderFlights(data.flights || []);

    // 集合資訊
    const mp = data.meeting_point || {};
    this._val("f-meeting_time", mp.time || "");
    this._val("f-meeting_location", mp.location || "");
    this._val("f-group_number", mp.group_number || "");

    // 每日行程
    this.renderDayTabs(data.days || []);
    if (data.days && data.days.length) {
      this.currentDay = 0;
      this.renderDayEditor(data.days[0], 0);
    }

    // 住宿總覽
    this.renderHotels(data.hotels || []);

    // 注意事項
    this.renderNotes(data.notes || []);
  },

  /* ═══════════════════════════════════════════════
     表單 → 收集資料 (collect)
     ═══════════════════════════════════════════════ */
  collectFormData() {
    const data = {};

    // 基本資訊
    data.title = this._val("f-title");
    data.subtitle = this._val("f-subtitle") || undefined;
    data.company = this._val("f-company") || undefined;
    data.destination = this._val("f-destination");
    data.date_range = this._val("f-date_range");
    data.quote = this._val("f-quote") || undefined;
    data.quote_en = this._val("f-quote_en") || undefined;
    data.cover_image = this._val("f-cover_image") || undefined;

    // 主題
    const activeTheme = document.querySelector(".theme-card.active");
    data.theme = activeTheme ? activeTheme.dataset.theme : "soft-cream";

    // 航班
    data.flights = this.collectFlights();

    // 集合資訊
    const mTime = this._val("f-meeting_time");
    const mLoc = this._val("f-meeting_location");
    if (mTime || mLoc) {
      data.meeting_point = {
        time: mTime,
        location: mLoc,
        group_number: this._val("f-group_number") || undefined,
      };
    }

    // 先儲存當前 day editor
    this._saveDayFromEditor();

    // 每日行程
    data.days = (App.data && App.data.days) ? App.data.days.map(d => ({ ...d })) : [];

    // 住宿
    data.hotels = this.collectHotels();

    // 注意事項
    data.notes = this.collectNotes();
    if (data.notes && !data.notes.length) data.notes = undefined;

    return data;
  },

  /* ═══════════════════════════════════════════════
     主題選擇器
     ═══════════════════════════════════════════════ */
  renderThemeSelector(themes, current) {
    const container = document.getElementById("theme-selector");
    if (!container) return;
    container.innerHTML = "";

    themes.forEach((t) => {
      const card = document.createElement("div");
      card.className = "theme-card" + (t.id === current ? " active" : "");
      card.dataset.theme = t.id;

      const colors = t.colors || {};
      const dots = ["bg-primary", "charcoal", "accent", "accent-light"]
        .filter((k) => colors[k])
        .map((k) => `<span class="theme-color-dot" style="background:${colors[k]}"></span>`)
        .join("");

      card.innerHTML = `
        <div class="theme-card-name">${t.name}</div>
        <div class="theme-card-desc">${t.description || ""}</div>
        <div class="theme-card-colors">${dots}</div>
      `;

      card.addEventListener("click", () => {
        container.querySelectorAll(".theme-card").forEach((c) => c.classList.remove("active"));
        card.classList.add("active");
      });

      container.appendChild(card);
    });
  },

  /* ═══════════════════════════════════════════════
     航班
     ═══════════════════════════════════════════════ */
  renderFlights(flights) {
    const list = document.getElementById("flights-list");
    list.innerHTML = "";
    flights.forEach((f, i) => this._appendFlightItem(list, f, i));
  },

  addFlight() {
    const list = document.getElementById("flights-list");
    const i = list.children.length;
    this._appendFlightItem(list, {
      direction: "departure", airline: "", flight_number: "",
      date: "", departure_airport: "", departure_time: "",
      arrival_airport: "", arrival_time: "",
    }, i);
  },

  _appendFlightItem(list, f, idx) {
    const div = document.createElement("div");
    div.className = "list-item flight-item";
    div.innerHTML = `
      <div class="form-group" style="min-width:80px;max-width:100px">
        <label>方向</label>
        <select class="fl-direction">
          <option value="departure" ${f.direction === "departure" ? "selected" : ""}>去程</option>
          <option value="return" ${f.direction === "return" ? "selected" : ""}>回程</option>
        </select>
      </div>
      <div class="form-group"><label>航空公司</label><input type="text" class="fl-airline" value="${this._esc(f.airline || "")}"></div>
      <div class="form-group"><label>航班號</label><input type="text" class="fl-number" value="${this._esc(f.flight_number || "")}"></div>
      <div class="form-group"><label>日期</label><input type="text" class="fl-date" value="${this._esc(f.date || "")}"></div>
      <div class="form-group"><label>出發機場</label><input type="text" class="fl-dep-airport" value="${this._esc(f.departure_airport || "")}"></div>
      <div class="form-group"><label>出發時間</label><input type="text" class="fl-dep-time" value="${this._esc(f.departure_time || "")}"></div>
      <div class="form-group"><label>抵達機場</label><input type="text" class="fl-arr-airport" value="${this._esc(f.arrival_airport || "")}"></div>
      <div class="form-group"><label>抵達時間</label><input type="text" class="fl-arr-time" value="${this._esc(f.arrival_time || "")}"></div>
      <button class="list-item-remove" onclick="this.parentElement.remove()" title="移除">×</button>
    `;
    list.appendChild(div);
  },

  collectFlights() {
    const items = document.querySelectorAll("#flights-list .flight-item");
    return Array.from(items).map((el) => ({
      direction: el.querySelector(".fl-direction").value,
      airline: el.querySelector(".fl-airline").value,
      flight_number: el.querySelector(".fl-number").value,
      date: el.querySelector(".fl-date").value,
      departure_airport: el.querySelector(".fl-dep-airport").value,
      departure_time: el.querySelector(".fl-dep-time").value,
      arrival_airport: el.querySelector(".fl-arr-airport").value,
      arrival_time: el.querySelector(".fl-arr-time").value,
    })).filter((f) => f.airline || f.flight_number);
  },

  /* ═══════════════════════════════════════════════
     每日行程 Tabs
     ═══════════════════════════════════════════════ */
  renderDayTabs(days) {
    const tabs = document.getElementById("day-tabs");
    tabs.innerHTML = "";
    days.forEach((d, i) => {
      const btn = document.createElement("button");
      btn.className = "day-tab" + (i === this.currentDay ? " active" : "");
      btn.textContent = `Day ${d.day}`;
      btn.addEventListener("click", () => this.switchDay(i));
      tabs.appendChild(btn);
    });
  },

  switchDay(idx) {
    // 先儲存當前 day
    this._saveDayFromEditor();

    this.currentDay = idx;

    // 更新 tab 高亮
    document.querySelectorAll(".day-tab").forEach((t, i) => {
      t.classList.toggle("active", i === idx);
    });

    const day = App.data.days[idx];
    if (day) this.renderDayEditor(day, idx);
  },

  addDay() {
    if (!App.data) return;
    if (!App.data.days) App.data.days = [];

    this._saveDayFromEditor();

    const newDay = {
      day: App.data.days.length + 1,
      date: "",
      title: "",
      meals: { breakfast: "敬請自理", lunch: "敬請自理", dinner: "敬請自理" },
    };
    App.data.days.push(newDay);
    this.currentDay = App.data.days.length - 1;

    this.renderDayTabs(App.data.days);
    this.renderDayEditor(newDay, this.currentDay);
  },

  /* ═══════════════════════════════════════════════
     Day Editor 渲染
     ═══════════════════════════════════════════════ */
  renderDayEditor(day, idx) {
    const container = document.getElementById("day-editor");
    const meals = day.meals || {};
    const hotel = day.hotel || {};
    const highlights = (day.highlights || []).join(", ");

    container.innerHTML = `
      <div class="day-editor-card">
        <div class="form-row">
          <div class="form-group"><label>日期</label><input type="text" id="d-date" value="${this._esc(day.date || "")}"></div>
          <div class="form-group"><label>Day</label><input type="text" id="d-day" value="${day.day || ""}"></div>
        </div>
        <div class="form-group"><label>標題</label><input type="text" id="d-title" value="${this._esc(day.title || "")}"></div>
        <div class="form-group"><label>英文標題</label><input type="text" id="d-title_en" value="${this._esc(day.title_en || "")}"></div>
        <div class="form-group"><label>路線</label><input type="text" id="d-route" value="${this._esc(day.route || "")}"></div>
        <div class="form-group"><label>描述</label><textarea id="d-desc" rows="3">${this._esc(day.description || "")}</textarea></div>
        <div class="form-group"><label>亮點（逗號分隔）</label><input type="text" id="d-highlights" value="${this._esc(highlights)}"></div>

        <!-- 活動 -->
        <div class="day-sub-section">
          <div class="day-sub-title">活動列表</div>
          <div id="d-activities"></div>
          <button class="btn btn-sm btn-outline" onclick="Editor.addActivity()">+ 新增活動</button>
        </div>

        <!-- 餐食 -->
        <div class="day-sub-section">
          <div class="day-sub-title">餐食</div>
          <div class="form-row">
            <div class="form-group"><label>早餐</label><input type="text" id="d-meal-b" value="${this._esc(meals.breakfast || "")}"></div>
            <div class="form-group"><label>午餐</label><input type="text" id="d-meal-l" value="${this._esc(meals.lunch || "")}"></div>
            <div class="form-group"><label>晚餐</label><input type="text" id="d-meal-d" value="${this._esc(meals.dinner || "")}"></div>
          </div>
        </div>

        <!-- 住宿 -->
        <div class="day-sub-section">
          <div class="day-sub-title">當日住宿</div>
          <div class="form-row">
            <div class="form-group"><label>飯店名稱</label><input type="text" id="d-hotel-name" value="${this._esc(hotel.name || "")}"></div>
            <div class="form-group"><label>區域</label><input type="text" id="d-hotel-area" value="${this._esc(hotel.area || "")}"></div>
          </div>
        </div>

        <!-- 圖片 -->
        <div class="day-sub-section">
          <div class="day-sub-title">圖片</div>
          <div class="form-row">
            <div class="form-group">
              <label>主圖</label>
              <div class="image-upload-row">
                <label class="btn btn-sm btn-outline">
                  上傳
                  <input type="file" accept="image/*" hidden onchange="App.uploadImage(this, 'day${idx+1}', 'd-image', 'd-image-thumb')">
                </label>
                <input type="text" id="d-image" value="${this._esc(day.image || "")}" class="flex-1">
              </div>
            </div>
            <div class="form-group">
              <label>副圖</label>
              <div class="image-upload-row">
                <label class="btn btn-sm btn-outline">
                  上傳
                  <input type="file" accept="image/*" hidden onchange="App.uploadImage(this, 'day${idx+1}_alt', 'd-image-alt', null)">
                </label>
                <input type="text" id="d-image-alt" value="${this._esc(day.image_alt || "")}" class="flex-1">
              </div>
            </div>
          </div>
        </div>

        <!-- 備註 -->
        <div class="day-sub-section">
          <div class="day-sub-title">備註</div>
          <div id="d-notes"></div>
          <button class="btn btn-sm btn-outline" onclick="Editor.addDayNote()">+ 新增備註</button>
        </div>

        <!-- 刪除整天 -->
        <div style="margin-top:16px;text-align:right">
          <button class="btn btn-sm btn-danger" onclick="Editor.removeDay(${idx})">刪除此天</button>
        </div>
      </div>
    `;

    // 填入活動
    const actContainer = document.getElementById("d-activities");
    (day.activities || []).forEach((a) => this._appendActivityItem(actContainer, a));

    // 填入備註
    const noteContainer = document.getElementById("d-notes");
    (day.notes || []).forEach((n) => this._appendDayNoteItem(noteContainer, n));
  },

  removeDay(idx) {
    if (!App.data || !App.data.days) return;
    if (!confirm(`確定要刪除 Day ${App.data.days[idx].day} 嗎？`)) return;

    App.data.days.splice(idx, 1);
    // 重新編號
    App.data.days.forEach((d, i) => { d.day = i + 1; });

    if (this.currentDay >= App.data.days.length) {
      this.currentDay = Math.max(0, App.data.days.length - 1);
    }

    this.renderDayTabs(App.data.days);
    if (App.data.days.length) {
      this.renderDayEditor(App.data.days[this.currentDay], this.currentDay);
    } else {
      document.getElementById("day-editor").innerHTML = "";
    }
  },

  /* ── Day Editor → 儲存回 App.data ────────────── */
  _saveDayFromEditor() {
    if (!App.data || !App.data.days || !App.data.days[this.currentDay]) return;
    const dayEl = document.getElementById("d-title");
    if (!dayEl) return; // editor not rendered yet

    const day = App.data.days[this.currentDay];
    day.day = parseInt(this._val("d-day")) || this.currentDay + 1;
    day.date = this._val("d-date");
    day.title = this._val("d-title");
    day.title_en = this._val("d-title_en") || undefined;
    day.route = this._val("d-route") || undefined;
    day.description = this._val("d-desc") || undefined;

    // 亮點
    const hl = this._val("d-highlights");
    day.highlights = hl ? hl.split(/[,，]/).map((s) => s.trim()).filter(Boolean) : undefined;

    // 活動
    day.activities = this.collectActivities();
    if (day.activities && !day.activities.length) day.activities = undefined;

    // 餐食
    day.meals = {
      breakfast: this._val("d-meal-b") || "敬請自理",
      lunch: this._val("d-meal-l") || "敬請自理",
      dinner: this._val("d-meal-d") || "敬請自理",
    };

    // 住宿
    const hName = this._val("d-hotel-name");
    if (hName) {
      day.hotel = { name: hName, area: this._val("d-hotel-area") || undefined };
    } else {
      day.hotel = undefined;
    }

    // 圖片
    day.image = this._val("d-image") || undefined;
    day.image_alt = this._val("d-image-alt") || undefined;

    // 備註
    day.notes = this.collectDayNotes();
    if (day.notes && !day.notes.length) day.notes = undefined;
  },

  /* ── 活動 ────────────────────────────────────── */
  addActivity() {
    const container = document.getElementById("d-activities");
    this._appendActivityItem(container, { name: "", description: "" });
  },

  _appendActivityItem(container, a) {
    const div = document.createElement("div");
    div.className = "list-item activity-item";
    div.innerHTML = `
      <div class="activity-row">
        <div class="form-group" style="flex:2"><label>活動名稱</label><input type="text" class="act-name" value="${this._esc(a.name || "")}"></div>
        <div class="form-group" style="flex:1"><label>圖標</label><input type="text" class="act-icon" value="${this._esc(a.icon || "")}" placeholder="🎿"></div>
        <button class="list-item-remove" onclick="this.parentElement.parentElement.remove()" title="移除">×</button>
      </div>
      <div class="form-group" style="width:100%"><label>說明</label><input type="text" class="act-desc" value="${this._esc(a.description || "")}"></div>
    `;
    container.appendChild(div);
  },

  collectActivities() {
    const items = document.querySelectorAll("#d-activities .activity-item");
    return Array.from(items).map((el) => ({
      name: el.querySelector(".act-name").value,
      description: el.querySelector(".act-desc").value || undefined,
      icon: el.querySelector(".act-icon").value || undefined,
    })).filter((a) => a.name);
  },

  /* ── Day 備註 ────────────────────────────────── */
  addDayNote() {
    const container = document.getElementById("d-notes");
    this._appendDayNoteItem(container, "");
  },

  _appendDayNoteItem(container, text) {
    const div = document.createElement("div");
    div.className = "note-item";
    div.innerHTML = `
      <input type="text" class="dn-text" value="${this._esc(text)}">
      <button class="btn-danger-sm" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(div);
  },

  collectDayNotes() {
    const items = document.querySelectorAll("#d-notes .note-item");
    return Array.from(items).map((el) => el.querySelector(".dn-text").value).filter(Boolean);
  },

  /* ═══════════════════════════════════════════════
     住宿總覽
     ═══════════════════════════════════════════════ */
  renderHotels(hotels) {
    const list = document.getElementById("hotels-list");
    list.innerHTML = "";
    hotels.forEach((h) => this._appendHotelItem(list, h));
  },

  addHotel() {
    const list = document.getElementById("hotels-list");
    this._appendHotelItem(list, { name: "", area: "", phone: "" });
  },

  _appendHotelItem(list, h) {
    const div = document.createElement("div");
    div.className = "hotel-item";
    const nightsStr = (h.nights || []).join(", ");
    div.innerHTML = `
      <div class="form-row">
        <div class="form-group" style="flex:2"><label>飯店名稱</label><input type="text" class="ht-name" value="${this._esc(h.name || "")}"></div>
        <div class="form-group"><label>區域</label><input type="text" class="ht-area" value="${this._esc(h.area || "")}"></div>
        <button class="btn-danger-sm" onclick="this.parentElement.parentElement.remove()" style="margin-top:18px">×</button>
      </div>
      <div class="form-row">
        <div class="form-group"><label>電話</label><input type="text" class="ht-phone" value="${this._esc(h.phone || "")}"></div>
        <div class="form-group"><label>入住天數（如 1,4）</label><input type="text" class="ht-nights" value="${nightsStr}"></div>
      </div>
    `;
    list.appendChild(div);
  },

  collectHotels() {
    const items = document.querySelectorAll("#hotels-list .hotel-item");
    return Array.from(items).map((el) => {
      const nights = el.querySelector(".ht-nights").value
        .split(/[,，]/).map((s) => parseInt(s.trim())).filter((n) => !isNaN(n));
      return {
        name: el.querySelector(".ht-name").value,
        area: el.querySelector(".ht-area").value || undefined,
        phone: el.querySelector(".ht-phone").value || undefined,
        nights: nights.length ? nights : undefined,
      };
    }).filter((h) => h.name);
  },

  /* ═══════════════════════════════════════════════
     注意事項
     ═══════════════════════════════════════════════ */
  renderNotes(notes) {
    const list = document.getElementById("notes-list");
    list.innerHTML = "";
    notes.forEach((n) => this._appendNoteItem(list, n));
  },

  addNote() {
    const list = document.getElementById("notes-list");
    this._appendNoteItem(list, "");
  },

  _appendNoteItem(list, text) {
    const div = document.createElement("div");
    div.className = "note-item";
    div.innerHTML = `
      <input type="text" class="note-text" value="${this._esc(text)}">
      <button class="btn-danger-sm" onclick="this.parentElement.remove()">×</button>
    `;
    list.appendChild(div);
  },

  collectNotes() {
    const items = document.querySelectorAll("#notes-list .note-item");
    return Array.from(items).map((el) => el.querySelector(".note-text").value).filter(Boolean);
  },

  /* ═══════════════════════════════════════════════
     工具
     ═══════════════════════════════════════════════ */
  _val(id, val) {
    const el = document.getElementById(id);
    if (!el) return "";
    if (val !== undefined) { el.value = val; return; }
    return el.value.trim();
  },

  _esc(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;")
              .replace(/</g, "&lt;").replace(/>/g, "&gt;");
  },
};
