# “Qarshi Usta Bot” — Texnik topshiriq (TZ)

## 1) Maqsad va umumiy tavsif
Bot mijozlardan xizmat buyurtmalarini qabul qiladi, admin va bo‘limga biriktirilgan ustalarga xabar beradi. Ustalar buyurtmani qabul qiladi yoki rad etadi (sabab bilan). Buyurtma yakunlangach mijoz 1–5 ballik tizimda baholaydi, reytinglar yig‘iladi va yangi buyurtmalarda prioritetlashda ishlatiladi.

## 2) Rol va huquqlar
- **Admin** (ADMIN_CHAT_ID): bo‘limlar/ustalar CRUD, buyurtmalarni ko‘rish, yangi buyurtmani ustaga tayinlash, yakunlash.
- **Usta** (SectionUsta.telegram_id): bo‘lim buyurtmalarini qabul qilish, rad etish (sabab bilan), qabul qilingan buyurtmani tugatish.
- **Mijoz** (users.telegram_id): buyurtma berish, lokatsiya/manzil yuborish, yakunda 1–5 baholash.

## 3) Buyurtma lifecycle (holatlar)
- **new**: mijoz buyurtma yaratdi → admin + ustalarga notificatsiya.
- **accepted**: usta qabul qildi yoki admin tayinladi → mijozga usta kontakti, adminga xabar.
- **done**: usta (yoki admin) tugatdi → mijozga baholash, adminga yakun xabari.

## 4) Funktsional talablar (FR)
### FR-01 — Xizmat bo‘limlari (Sections) boshqaruvi (MUST)
- Admin bo‘lim qo‘sha/nomini o‘zgartira/o‘chira oladi
- Bo‘lim aktiv/pauza holati
- Bo‘lim turi: `standard | suggestion | admin_contact`

### FR-02 — Bo‘limga bir nechta usta biriktirish (MUST)
- Admin usta qo‘shadi: ism, familiya, telefon
- Usta statusi: pending (telegram_id yo‘q) vs claimed (telegram_id bor)

### FR-03 — Usta claim: telefon orqali Telegram ID bog‘lash (MUST)
- Usta botga `/start usta` bilan kiradi
- Usta kontaktini yuboradi (request_contact)
- Telefon DB dagi pending usta(lar) bilan mos kelsa telegram_id yoziladi

### FR-04 — Buyurtma yaratish (mijoz) (MUST)
- Mijoz ro‘yxatdan o‘tadi (ism, familiya, telefon)
- Xizmat/bo‘lim tanlaydi, muammo matni va ixtiyoriy media (foto/video/doc) yuborishi mumkin
- Lokatsiya yoki yozma manzil (`service_address_note`) kiritilishi

### FR-05 — Yangi buyurtma notificatsiyasi (MUST)
- Admin ga buyurtma detail yuboriladi
- Bo‘limdagi claimed ustalarga buyurtma yuboriladi
- Usta xabarida: ✅ Qabul qilish va ❌ Rad etish tugmalari

### FR-06 — Usta qabul qilish (Accept) (MUST)
- Race-conditiondan himoya: faqat 1 usta `status=new` bo‘lsa `accepted` qiladi
- Qabul qilganda: `orders.status=accepted`, `accepted_usta_*` va `accepted_usta_id` to‘ldiriladi
- Mijozga usta ismi+telefon yuboriladi; admin xabardor qilinadi

### FR-07 — Usta rad etish (Reject) + sabab (MUST)
- Usta ❌ Rad etish bosadi → sabab matnini kiritadi (FSM)
- Sabab admin ga yuboriladi
- Admin ga “Boshqa ustaga berish” tugmasi orqali qayta tayinlash yo‘li

### FR-08 — Admin buyurtmani ustaga qo‘lda tayinlash (MUST)
- Faqat `status=new` buyurtmalarda “Ustaga berish” chiqadi
- Admin bo‘lim bo‘yicha claimed ustalar ro‘yxatidan tanlaydi
- Buyurtma `accepted` bo‘ladi va tanlangan ustaga xabar boradi

### FR-09 — Tugatish (Complete) + baholash (1–5) (MUST)
- Accepted buyurtmada usta (yoki admin) “Tugatish” qiladi → `status=done`, `rating_requested=true`
- Mijozga 1–5 ⭐ inline baholash yuboriladi (bir marta)
- Usta reytingi: `rating_sum/rating_count`; admin yakun va baho haqida xabar oladi

### FR-10 — Reyting bo‘yicha prioritet xabarnoma (SHOULD)
- Bo‘lim ustalari `avg_rating` bo‘yicha `DESC` tartiblanadi
- Yangi buyurtma xabari avval yuqori reytingdagilarga ketadi

### FR-11 — Admin reply keyboard: buyurtmalarni 3 bo‘limga ajratish (MUST)
- 🆕 Yangi buyurtmalar
- ✅ Qabul qilingan
- 🏁 Tugatilgan
- Shuningdek: 📂 Bo‘limlar, 📊 Statistika, 👷 Ustalar

## 5) Admin interfeysi
- Admin reply keyboard: 2 ustunli joylashuv (buyurtmalar va boshqaruv bo‘limlari).
- Admin inline panel: `/admin` orqali buyurtmalar list/detail/status actions.

## 6) Usta claim oqimi
Admin usta qo‘shganda usta “pending” bo‘ladi (telegram_id yo‘q). Usta botga **/start usta** bilan kiradi va kontakt yuboradi. Telefon mos kelsa telegram_id bog‘lanadi (claimed).

## 7) DB sxema (SQLAlchemy)
### users
- telegram_id (PK), first_name, last_name, phone, locale, registered_at

### sections
- id (PK), title (unique), sort_order, is_active, kind, usta_telegram_id (legacy), created_at

### section_ustas
- id (PK), section_id (FK), telegram_id (nullable), first_name, last_name, phone, phone_normalized, rating_sum, rating_count
- Unique: (section_id, phone_normalized)
- Claimed uchun partial unique index: (section_id, telegram_id) WHERE telegram_id IS NOT NULL

### orders
- id (PK), created_at, client_tg_id, client_name/username/phone, service, section_id, section_kind
- problem, problem_media_json (optional), lat/lon (optional), service_address_note (optional)
- status (new/accepted/done)
- accepted_usta_name/phone/telegram_id, accepted_usta_id
- rating (1–5 optional), rating_requested (bool)

## 8) Callback data va FSM states
### CallbackData
- `ord`: OrderCallback(action, order_id, suid, rating)
- `adm`: AdminCallback(action)
- `sec`: SectionCallback(action, sid)
- `sut`: SectionUstaCallback(action, sid, uid)

### FSM States (aiogram)
- RegStates: waiting_first_name / waiting_last_name / waiting_phone
- LanguageStates: picking
- OrderStates: waiting_problem / waiting_optional_media / waiting_location_choice / waiting_visit_address_note / ...
- SectionAdminStates: waiting_usta_first_name / waiting_usta_last_name / waiting_usta_phone
- UstaClaimStates: waiting_contact
- UstaRejectStates: waiting_reason

## 9) Non-functional talablar
- Polling faqat bitta instans (Railway replicas=1)
- Accept: atomic update (`WHERE status='new'`) bilan
- Telefon faqat request_contact orqali olinadi (self-contact)
- Logging: “chat not found”, tarmoq uzilishi, migration xatolari loglanadi

## 10) Deploy (GitHub + Railway)
- Start: `python main.py` (`railway.toml`)
- Variables:
  - BOT_TOKEN
  - ADMIN_CHAT_ID
  - DATABASE_URL (Railway Postgres beradi; kod `postgresql://` → `postgresql+asyncpg://` ga moslaydi)

## 11) Qabul mezonlari (Acceptance criteria)
- Mijoz ro‘yxatdan o‘tib buyurtma bera oladi (lokatsiya yoki manzil bilan).
- Yangi buyurtma admin va bo‘limdagi claimed ustalarga boradi; usta accept/reject ishlaydi.
- Accept bo‘lsa mijozga usta ismi+telefon boradi; admin buyurtma statusini ko‘radi.
- Reject bo‘lsa usta sabab kiritadi; admin sababni oladi va “Boshqa ustaga berish” orqali tayinlay oladi.
- Tugatish → mijoz 1–5 baho beradi; usta reytingi yangilanadi; admin xabar oladi.

