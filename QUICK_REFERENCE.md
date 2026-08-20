# 📚 راهنمای سریع استانداردهای طراحی
**Quick Reference Guide - Design Standards**

---

## 🎨 رنگ‌ها (Colors)

### رنگ‌های اصلی
```css
--primary: #2c3e50        /* آبی تیره */
--accent: #3498db         /* آبی روشن */
--success: #28a745        /* سبز */
--error: #cf222e          /* قرمز */
--warning: #f39c12        /* نارنجی */
--info: #17a2b8           /* فیروزه‌ای */
```

### استفاده در HTML
```html
<button class="btn btn-primary">دکمه اصلی</button>
<span class="badge badge-success">موفق</span>
<div class="status-msg error">خطا</div>
```

---

## 📝 فونت‌ها (Typography)

### اندازه‌ها
| نام | پیکسل | استفاده |
|-----|--------|---------|
| xs | 11px | راهنمایی |
| sm | 13px | label |
| base | 14px | متن اصلی |
| lg | 16px | مهم |
| xl | 18px | زیرعنوان |
| 2xl | 20px | عنوان |
| 3xl | 24px | عنوان صفحه |

```html
<h1>عنوان صفحه (24px)</h1>
<p>متن اصلی (14px)</p>
<small class="text-muted">راهنمایی (11px)</small>
```

---

## 📋 فرم‌ها (Forms)

### ساختار پایه
```html
<div class="form-panel">
  <form class="form-grid">
    <div>
      <label>عنوان</label>
      <input type="text">
    </div>
    <div class="form-col-span-full">
      <button class="btn btn-primary">ثبت</button>
    </div>
  </form>
</div>
```

### Grid Types
```html
<form class="form-grid">          <!-- خودکار -->
<form class="form-grid-2">        <!-- 2 ستون -->
<form class="form-grid-3">        <!-- 3 ستون -->
<form class="form-grid-4">        <!-- 4 ستون -->
```

### حالت‌های Input
```html
<input type="text">                 <!-- عادی -->
<input type="text" class="error">   <!-- خطا -->
<input type="text" class="success"> <!-- موفق -->
<input type="text" disabled>        <!-- غیرفعال -->
```

---

## 🔘 دکمه‌ها (Buttons)

### انواع
```html
<button class="btn btn-primary">اصلی</button>
<button class="btn btn-secondary">ثانویه</button>
<button class="btn btn-success">موفق</button>
<button class="btn btn-danger">خطر</button>
<button class="btn btn-warning">هشدار</button>
<button class="btn btn-info">اطلاعات</button>
<button class="btn btn-outline">خطی</button>
```

### سایزها
```html
<button class="btn btn-sm">کوچک</button>
<button class="btn">عادی</button>
<button class="btn btn-lg">بزرگ</button>
<button class="btn btn-xl">خیلی بزرگ</button>
<button class="btn btn-block">تمام عرض</button>
```

### گروه دکمه
```html
<div class="btn-group">
  <button class="btn">1</button>
  <button class="btn">2</button>
  <button class="btn">3</button>
</div>
```

---

## 📊 جداول (Tables)

### ساختار پایه
```html
<div class="table-container">
  <table>
    <thead>
      <tr><th>ستون 1</th><th>ستون 2</th></tr>
    </thead>
    <tbody>
      <tr><td>داده 1</td><td>داده 2</td></tr>
    </tbody>
  </table>
</div>
```

### انواع
```html
<table class="table-compact">     <!-- فشرده -->
<th class="sortable">عنوان</th>   <!-- قابل مرتب‌سازی -->
<tr class="row-selected">         <!-- انتخاب شده -->
<tr class="row-success">          <!-- موفق -->
<tr class="row-warning">          <!-- هشدار -->
<tr class="row-error">            <!-- خطا -->
```

### ریسپانسیو
```html
<div class="table-responsive">
  <div class="table-container">
    <table>...</table>
  </div>
</div>
```

---

## 🎴 کارت‌ها (Cards)

### کارت ساده
```html
<div class="card">
  <h3 class="card-title">عنوان</h3>
  <p>محتوا</p>
</div>
```

### کارت کامل
```html
<div class="card">
  <div class="card-header">
    <h3 class="card-title">عنوان</h3>
    <p class="card-subtitle">زیرعنوان</p>
  </div>
  <div class="card-body">محتوا</div>
  <div class="card-footer">
    <button class="btn">عملیات</button>
  </div>
</div>
```

### Grid کارت‌ها
```html
<div class="cards">           <!-- خودکار -->
<div class="cards-2">         <!-- 2 ستون -->
<div class="cards-3">         <!-- 3 ستون -->
<div class="cards-4">         <!-- 4 ستون -->
```

---

## 💬 پیام‌های وضعیت (Status Messages)

```html
<div class="status-msg success">موفقیت</div>
<div class="status-msg error">خطا</div>
<div class="status-msg warning">هشدار</div>
<div class="status-msg info">اطلاعات</div>
```

---

## 🏷️ برچسب‌ها (Badges & Chips)

### Badge
```html
<span class="badge badge-primary">اصلی</span>
<span class="badge badge-success">موفق</span>
<span class="badge badge-danger">خطر</span>
<span class="badge badge-warning">هشدار</span>
<span class="badge badge-info">اطلاعات</span>
```

### Chip
```html
<span class="chip">پیش‌فرض</span>
<span class="chip primary">اصلی</span>
<span class="chip ok">موفق</span>
<span class="chip warn">هشدار</span>
```

---

## 📏 فاصله‌گذاری (Spacing)

### Margin
```html
<div class="mt-1">  <!-- margin-top: 4px -->
<div class="mt-2">  <!-- margin-top: 8px -->
<div class="mt-3">  <!-- margin-top: 16px -->
<div class="mt-4">  <!-- margin-top: 24px -->

<div class="mb-1">  <!-- margin-bottom: 4px -->
<div class="mb-2">  <!-- margin-bottom: 8px -->
<div class="mb-3">  <!-- margin-bottom: 16px -->
<div class="mb-4">  <!-- margin-bottom: 24px -->

<div class="ml-1">  <!-- margin-right: 4px (RTL) -->
<div class="mr-1">  <!-- margin-left: 4px (RTL) -->

<div class="m-0">   <!-- margin: 0 -->
```

### Padding
```html
<div class="p-0">   <!-- padding: 0 -->
<div class="p-1">   <!-- padding: 4px -->
<div class="p-2">   <!-- padding: 8px -->
<div class="p-3">   <!-- padding: 16px -->
<div class="p-4">   <!-- padding: 24px -->
```

---

## 🔧 Utility Classes

### Display
```html
<div class="d-none">         <!-- display: none -->
<div class="d-block">        <!-- display: block -->
<div class="d-flex">         <!-- display: flex -->
<div class="d-grid">         <!-- display: grid -->
<div class="d-inline-block"> <!-- display: inline-block -->
```

### Flexbox
```html
<div class="d-flex justify-between align-center gap-3">
  <div>آیتم 1</div>
  <div>آیتم 2</div>
</div>
```

**Justify Content:**
- `justify-start` - flex-start
- `justify-center` - center
- `justify-end` - flex-end
- `justify-between` - space-between

**Align Items:**
- `align-start` - flex-start
- `align-center` - center
- `align-end` - flex-end

**Gap:**
- `gap-1` - 4px
- `gap-2` - 8px
- `gap-3` - 16px
- `gap-4` - 24px

### Text
```html
<p class="text-left">        <!-- text-align: left -->
<p class="text-center">      <!-- text-align: center -->
<p class="text-right">       <!-- text-align: right -->
<p class="text-bold">        <!-- font-weight: 700 -->
<p class="text-muted">       <!-- color: muted -->
<p class="text-primary">     <!-- color: primary -->
```

### Background Colors
```html
<div class="bg-primary">     <!-- background: primary -->
<div class="bg-success">     <!-- background: success -->
<div class="bg-danger">      <!-- background: danger -->
<div class="bg-warning">     <!-- background: warning -->
<div class="bg-info">        <!-- background: info -->
```

### Shadows
```html
<div class="shadow-none">    <!-- box-shadow: none -->
<div class="shadow-sm">      <!-- box-shadow: small -->
<div class="shadow-md">      <!-- box-shadow: medium -->
<div class="shadow-lg">      <!-- box-shadow: large -->
```

### Border & Radius
```html
<div class="border">         <!-- border: 1px solid -->
<div class="border-0">       <!-- border: none -->
<div class="border-top">     <!-- border-top only -->
<div class="border-bottom">  <!-- border-bottom only -->

<div class="rounded">        <!-- border-radius: 6px -->
<div class="rounded-lg">     <!-- border-radius: 8px -->
<div class="rounded-full">   <!-- border-radius: 9999px -->
```

---

## 📱 Responsive Design

### Breakpoints
- **< 480px:** Mobile
- **480px - 768px:** Tablet
- **768px - 1200px:** Desktop Small
- **> 1200px:** Desktop

### تغییرات خودکار:
- **فرم‌ها:** از چند ستون به ۱ ستون
- **جداول:** فونت کوچک‌تر
- **کارت‌ها:** از چند ستون به ۱ ستون
- **دکمه‌ها:** تمام عرض در موبایل

---

## ⚡ نکات سریع

### ✅ کارهای درست
```html
<!-- استفاده از کلاس‌های استاندارد -->
<button class="btn btn-primary">ثبت</button>

<!-- استفاده از متغیرهای CSS -->
.my-element { color: var(--text); }

<!-- استفاده از Semantic HTML -->
<header>, <nav>, <main>, <footer>

<!-- Label برای input -->
<label for="name">نام</label>
<input id="name" type="text">
```

### ❌ کارهای غلط
```html
<!-- استفاده از inline style -->
<button style="background: blue;">ثبت</button>

<!-- استفاده از مقادیر ثابت -->
.my-element { color: #24292f; }

<!-- استفاده از div برای همه چیز -->
<div class="header">...</div>

<!-- Input بدون Label -->
<input type="text">
```

---

## 🎯 الگوهای رایج (Common Patterns)

### 1. صفحه با هدر و جدول
```html
<div class="header-actions">
  <h1>عنوان صفحه</h1>
  <button class="btn btn-primary">افزودن</button>
</div>

<div class="table-container">
  <table>...</table>
</div>
```

### 2. فرم ساده
```html
<div class="form-panel">
  <h2 class="form-panel-title">عنوان فرم</h2>
  <form class="form-grid">
    <!-- فیلدها -->
    <div class="form-col-span-full">
      <button class="btn btn-primary btn-block">ثبت</button>
    </div>
  </form>
</div>
```

### 3. داشبورد با کارت
```html
<div class="header-actions">
  <h1>داشبورد</h1>
</div>

<div class="cards cards-4">
  <div class="card">
    <h3 class="card-title">عنوان</h3>
    <p>محتوا</p>
  </div>
  <!-- کارت‌های بیشتر -->
</div>
```

### 4. فرم + نتایج
```html
<div class="form-panel">
  <form class="form-grid">
    <!-- فیلترها -->
  </form>
</div>

<div class="table-container">
  <table>
    <!-- نتایج -->
  </table>
</div>
```

---

## 🔍 دیباگ سریع (Quick Debug)

### مشکل: المان نمایش داده نمی‌شود
```css
/* بررسی کنید: */
display: none;  /* آیا این ست شده؟ */
visibility: hidden;  /* یا این؟ */
```

### مشکل: رنگ اشتباه است
```css
/* از متغیر استفاده کنید: */
color: var(--primary);  /* نه #2c3e50 */
```

### مشکل: فاصله‌گذاری نامناسب
```html
<!-- از کلاس‌های utility استفاده کنید: -->
<div class="mt-3 mb-2">محتوا</div>
```

### مشکل: در موبایل خراب است
```html
<!-- ریسپانسیو کنید: -->
<div class="form-grid">  <!-- خودکار ریسپانسیو می‌شود -->
<div class="table-responsive">  <!-- جدول scroll می‌خورد -->
```

---

## 📖 منابع بیشتر

- **سند کامل:** [DESIGN_STANDARDS.md](./DESIGN_STANDARDS.md)
- **فایل CSS:** [design-standards.css](./web/design-standards.css)
- **فایل فعلی:** [styles.css](./web/styles.css)

---

**نکته:** همیشه قبل از شروع کدنویسی، این راهنما را مرور کنید! ✨
