# אפיון מלא ומקיף — Sam Spiegel Dashboard v2.0

**תאריך:** מרץ 2026
**גרסה:** 2.0 (אפיון מורחב)
**פרויקט:** Sam Spiegel Film School Dashboard
**Stack:** Vanilla JS + Firebase Firestore + GitHub Pages

---

## תוכן עניינים

1. [KPIs — מחוון ביצועים מעודכן](#1-kpis)
2. [Custom Events CRUD](#2-custom-events-crud)
3. [Calendar Date Picker — מלא עם Lesson Overlay](#3-calendar-date-picker)
4. [תאריך פתיחה (Opening Date)](#4-opening-date)
5. [Kanban Board — 4 עמודות](#5-kanban-board)
6. [Lesson Matching — מנוע קטלוג חכם](#6-lesson-matching)
7. [עיצוב כרטיסיות — צבע קורס מלא](#7-עיצוב-כרטיסיות)
8. [הגדרות עיצוב אישי מורחבות](#8-הגדרות-עיצוב-אישי)
9. [פיצ'רים נוספים שהוספתי](#9-פיצרים-נוספים)
10. [מבנה Firebase](#10-מבנה-firebase)
11. [ארכיטקטורה טכנית](#11-ארכיטקטורה-טכנית)
12. [סדר פיתוח — Phases](#12-סדר-פיתוח)

---

## 1. KPIs

### 1.1 ארבעת ה-KPIs החדשים

**מיקום:** 2×2 Grid בראש ה-Sidebar (כמו היום), אבל עם נתונים מעודכנים.

```
┌─────────────────┬─────────────────┐
│  📋  משימות     │  ⚡  72 שעות    │
│     פתוחות      │    קריטי        │
│      7          │      3          │
├─────────────────┼─────────────────┤
│  📅  שבועות     │  🎓  שיעורים    │
│  לסוף סמסטר ב  │  סמסטר ב        │
│      11         │   23 / 68       │
└─────────────────┴─────────────────┘
```

---

### KPI 1: משימות פתוחות

**הגדרה:** כל המשימות שסטטוסן הפרסונלי של המשתמש הנוכחי הוא **לא** `submitted`.

```javascript
function kpiOpenTasks() {
  return tasksData.filter(t =>
    t.status === 'active' &&
    getStatus(t.id) !== 'submitted'
  ).length;
}
```

**צבע:** לבן/סגול רגיל.
**לחיצה:** מסנן את ה-Kanban להציג רק "פתוח+לעשות+בתהליך".

---

### KPI 2: 72 שעות קריטי

**הגדרה:** משימות אקטיביות עם `due_date <= now+72h` שסטטוסן **לא** `submitted`.

```javascript
function kpi72h() {
  const cutoff = new Date(Date.now() + 72 * 3600 * 1000);
  return tasksData.filter(t =>
    t.status === 'active' &&
    t.due_date &&
    new Date(t.due_date) <= cutoff &&
    getStatus(t.id) !== 'submitted'
  ).length;
}
```

**צבע:** אדום פועם (`#FF4757`) אם > 0.
**לחיצה:** מסנן Kanban לאלה בלבד.

---

### KPI 3: שבועות לסוף סמסטר ב

**הגדרה:** `Math.ceil((endOfSemB - today) / 7)` שבועות.

```javascript
const SEMESTER_B_END = '2026-06-30'; // ← ניתן לשינוי בהגדרות

function kpiWeeksLeft() {
  const today = new Date();
  const end = new Date(SEMESTER_B_END);
  const diffMs = end - today;
  if (diffMs <= 0) return 0;
  return Math.ceil(diffMs / (7 * 24 * 3600 * 1000));
}
```

**עיצוב:** progress bar אנכי בתוך הcard (כמו countdown בpinboard).
**צבע:** ירוק → כתום → אדום ככל שמתקרב.
**לחיצה:** פותח dialog לשינוי תאריך סיום הסמסטר.

---

### KPI 4: שיעורים שעברו מסמסטר ב

**הגדרה:** מתוך כל שיעורי `events.json` (סמסטר ב): כמה כבר עברו vs. סך הכל.

```javascript
function kpiLessonsProgress() {
  const now = new Date();
  const semBLessons = events.filter(ev =>
    ev.type === 'lecture' || ev.type === 'workshop'
  );
  const done = semBLessons.filter(ev => new Date(ev.end) < now).length;
  const total = semBLessons.length;
  return { done, total };
}
// → "23 / 68"
```

**עיצוב:** fraction + progress bar אופקי `████░░░░░░ 34%`.
**צבע:** תכלת כמו Lesson badge הקיים.
**לחיצה:** פותח modal עם breakdown לפי קורס.

#### Modal — פירוט שיעורים לפי קורס:
```
📊 שיעורים סמסטר ב

קורס              עבר    נשאר   סה"כ
─────────────────────────────────────
תחקיר            ██░░    4/8    █████
קולנוע ישראלי   ████░   5/7    ██░░░
תולדות הקולנוע  ██████  6/6  ✅ הושלם
...
```

---

## 2. Custom Events CRUD

### 2.1 מה זה Custom Event

אירוע שאינו מ-Yedion. לדוגמה:
- "מפגש קבוצת כתיבה"
- "הגשת פרויקט — Dropbox"
- "ישיבת הפקה עם סיגל"
- "חג שבועות"

**הבדל מ-Task:**
| | Custom Event | Task |
|--|--|--|
| **מיקום** | לוח שנה | Kanban |
| **תאריך** | start + end (עם שעות) | due_date |
| **סטטוס** | אין | none/todo/inprogress/submitted |
| **עריכה** | כולם | כולם |

### 2.2 מבנה נתונים — Firebase `custom_events`

```javascript
{
  id: string,               // Auto-ID
  title: string,            // שם האירוע (required, min 2 chars)
  description: string,      // תיאור חופשי

  start_date: string,       // "YYYY-MM-DD" (required)
  start_time: string,       // "HH:MM" | "" (ריק = all-day)
  end_date: string,         // "YYYY-MM-DD" (= start_date אם חד-יומי)
  end_time: string,         // "HH:MM" | ""

  all_day: boolean,

  color: string,            // hex: "#7C6FF7"
  icon: string,             // emoji: "📝" | "🎬" | "🎓" | "⭐" | "🔴" | ""

  category: "personal" | "academic" | "social" | "deadline" | "other",

  linked_course_key: string | null,  // קישור לקורס

  recurrence: null | {      // חזרות (Phase 2)
    freq: "daily" | "weekly" | "monthly",
    until: string,          // "YYYY-MM-DD"
    days_of_week: number[]  // 0=Sunday...6=Saturday
  },

  created_by: string,
  created_at: Timestamp,
  updated_at: Timestamp
}
```

### 2.3 תצוגה בלוח שנה

```
┌──────────────────────────────────────┐
│ ✏  מפגש קבוצת כתיבה          14:00 │  ← Custom Event
│    [🟣 academic] [ערוך] [מחק]       │
└──────────────────────────────────────┘
```

- גבול שמאלי `3px solid <color>` (מול `2px` לשיעורי ICS)
- Badge קטן `✏ custom` או אייקון האירוע
- כפתורי ערוך/מחק נראים ב-hover
- All-day events — מוצגים בחלק עליון של עמודת היום

### 2.4 Modal — יצירה/עריכה

```
┌──────────────────────────────────────────────────┐
│  ✨  אירוע חדש  /  ✏ ערוך אירוע                 │
├──────────────────────────────────────────────────┤
│                                                   │
│  שם האירוע *   [____________________________]    │
│                                                   │
│  📅 תאריך התחלה  [calendar picker popup]         │
│  ⏰ שעת התחלה    [14:00]    ☐ כל היום            │
│  📅 תאריך סיום   [calendar picker popup]         │
│  ⏰ שעת סיום     [16:00]                         │
│                                                   │
│  🎨 צבע                                          │
│  [●#7C6FF7][●#6FBBF7][●#00E5CC][●#FFD166]       │
│  [●#FF4757][●#FF7F50][●#9C88FF] + [⬛ custom]   │
│                                                   │
│  😊 אייקון  [ 📝 ][ 🎬 ][ 🎓 ][ ⭐ ][ 🔴 ]       │
│                                                   │
│  🏷 קטגוריה  [academic ▼]                        │
│                                                   │
│  📚 קורס קשור  [ללא ▼]                          │
│                                                   │
│  📝 תיאור                                        │
│  [__________________________________________]    │
│  [__________________________________________]    │
│                                                   │
│  [❌ ביטול]              [✅ שמור אירוע]         │
└──────────────────────────────────────────────────┘
```

### 2.5 כפתור "+ אירוע" בכל עמודת יום

```
┌──── ראשון 15.3.26 ────[+ אירוע]──┐
│                                    │
```
לחיצה → Modal עם `start_date` prefilled לאותו יום.

---

## 3. Calendar Date Picker

### 3.1 עיצוב — Mini Calendar Popup

**המשמעות:** כשמשתמש לוחץ על שדה "תאריך יעד" בmodal משימה/אירוע, נפתח popup mini-calendar במקום `<input type="date">` הרגיל.

```
┌────────────────────────────────────────┐
│  ◀   מרץ 2026   ▶                     │
│                                        │
│  א   ב   ג   ד   ה   ו   ש           │
│  1   2   3   4   5   6   7            │
│  8   9  10  11  12  13  14            │
│ 15  16  17 [18] 19  20  21            │
│             ↑                          │
│ 22  23  24  25  26  27  28            │
│ 29  30  31                            │
│                                        │
│ ─── שיעורים ב-18 במרץ ─────────────  │
│ 🟣  תחקיר          שיעור #7  09:00   │
│ 🔵  קולנוע ישראלי  שיעור #4  12:45   │
│ ✏  מפגש כתיבה (custom)       14:00   │
│                                        │
│ ⚠ 2 שיעורים ביום זה                  │
└────────────────────────────────────────┘
```

### 3.2 Color Coding על ימי הלוח

| מצב תאריך | Style |
|-----------|-------|
| ללא שיעורים | רגיל |
| 1 שיעור | `background: rgba(108,186,255,0.12)` + נקודה תכלת |
| 2 שיעורים | `background: rgba(255,163,72,0.18)` + נקודה כתום |
| 3+ שיעורים | `background: rgba(255,71,87,0.22)` + נקודה אדום |
| היום | `::after` dot ירוק #00E5CC |
| נבחר | `background: #7C6FF7; color: white; border-radius: 50%` |
| עבר | `opacity: 0.4` |

### 3.3 Lesson Preview Panel (תחת הלוח)

- מצג: hover/focus על תאריך → מחליף את ה-preview
- מוגבל ל-5 שורות + "ועוד N..."
- Custom Events מוצגים עם `✏`

### 3.4 Navigation

- `◀ ▶` — נווט חודש
- Click on month name → dropdown שנה/חודש
- Keyboard: `Arrow keys` ← ניווט בתאריכים, `Enter` ← בחר, `ESC` ← סגור

---

## 4. Opening Date

### 4.1 שדה ב-Modal

```
│ 📅 תאריך פתיחה  [10/03/2026 ▼] (אופציונלי)  │
│   📚 שיעור ביום זה: תחקיר #3 — 09:00 🎓      │
│                                                 │
│ 📅 תאריך יעד    [20/03/2026 ▼]                │
│   📚 שיעור ביום זה: תחקיר #7 — 09:00 🎓       │
│                                                 │
│  ⚠ Validation: פתיחה חייבת להיות לפני היעד    │
```

### 4.2 לוגיקת תצוגה בKanban

| מצב | Badge |
|-----|-------|
| `opening_date = null` | ─ |
| `opening_date > today` | `🔒 נפתח ב-{N} ימים` (כחול) |
| `opening_date = today` | `🔓 נפתח היום` (ירוק) |
| `opening_date < today` | לא מוצג |

**אפשרות הסתרה:** toggle בHeader הKanban:
```
[👁 הצג ממתינים] [👁 הסתר ממתינים]
```

### 4.3 שדה ב-Firebase

```javascript
// tasks collection — שדות חדשים:
opening_date: "YYYY-MM-DD" | null
```

---

## 5. Kanban Board — 4 עמודות

### 5.1 מבנה Layout

**Desktop:**
```
┌────────────────┬──────────────────────────────────────────────┐
│  KPIs (2×2)   │  📋 פתוח(5) │ 📌 לעשות(3) │ ⚡ בתהליך(2) │ ✅ הוגש(8) │
│               │                                               │
│  Pinboard     │  [cards]    │  [cards]    │  [cards]    │  [cards]    │
│  (scrollable) │                                               │
└────────────────┴──────────────────────────────────────────────┘
│                          CALENDAR                             │
└───────────────────────────────────────────────────────────────┘
```

**Mobile (≤ 768px):**
- Tab bar: `[פתוח] [לעשות] [בתהליך] [הוגש]`
- עמודה בודדת גלילה
- Swipe gesture בין עמודות

### 5.2 עמודות

| עמודה | סטטוס | צבע Header | אייקון |
|-------|-------|-----------|--------|
| פתוח | `none` | `#404060` | 📋 |
| לעשות | `todo` | `#6FBBF7` | 📌 |
| בתהליך | `inprogress` | `#FFD166` | ⚡ |
| הוגש | `submitted` | `#00E5CC` | ✅ |

### 5.3 Task Card — עיצוב מלא

```
┌──────────────────────────────────────────────────┐
│  (background: צבע קורס ב-12% opacity)            │
│  ┌──────────────────────────────────────────┐    │
│  │ border-top: 3px solid <course_color>     │    │
│  │                                          │    │
│  │  🔴 פגר          🟣 תחקיר               │    │
│  │                                          │    │
│  │  ביקורת מחזה — "אוטלו"                  │    │
│  │                                          │    │
│  │  📅 יעד: 15/03   🔒 נפתח: 12/03         │    │
│  │  🎓 תחקיר #5 ב-12/03 (match!)           │    │
│  │                                          │    │
│  │  [→ קדם]    [✏ ערוך]    [🗑 מחק]       │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

### 5.4 Card Elements

| אלמנט | תיאור |
|-------|-------|
| **Background** | `rgba(<course_rgb>, 0.12)` — צבע קורס בשקיפות |
| **Top border** | `3px solid <course_color>` |
| **Urgency chip** | 🔴 פגר / 🟡 ≤3 ימים / 🔵 פתוח / ─ |
| **Course badge** | שם קורס קצר + dot צבעוני |
| **Title** | 2 שורות max, ellipsis |
| **Dates** | תאריך פתיחה + יעד (אם קיימים) |
| **Lesson Match** | `🎓 <קורס> #N ב-<תאריך>` |
| **Advance** | "→ קדם ל<שלב הבא>" |
| **Edit/Delete** | פעולות |

### 5.5 מיון בתוך עמודה

1. Overdue (due_date < today)
2. Due today
3. Due ≤ 3 days
4. Due ≤ 7 days
5. Due later
6. No due date

Secondary: created_at DESC

### 5.6 Filter Bar מעל הKanban

```
[🔍 חפש משימה]  [📚 כל הקורסים ▼]  [👁 הצג ממתינים]
```

---

## 6. Lesson Matching — מנוע קטלוג חכם

### 6.1 הבעיה

ב-`events.json`, כמה אירועים מ-Yedion מגיעים עם שמות שונים קצת מהשמות בcourses.json. לדוגמה:
- `"סדנת תסריט — לוקיישן (קב. א)"` → צריך להיות מקושר ל-`location`
- `"קולנוע ישראלי ב: תקופת ה-New Wave"` → `israeli_cinema`
- `"Workshop: Short Story"` → `short_story`

### 6.2 מנוע ה-Matching

```javascript
// config/course_aliases.js (inline)
const COURSE_ALIASES = {
  tachkir: [
    'תחקיר', 'סדנת תחקיר', 'investigative', 'investigation'
  ],
  location: [
    'לוקיישן', 'location', 'סדנת תסריט לוקיישן', 'תסריט לוקיישן'
  ],
  short_story: [
    'סיפור קצר', 'short story', 'הסיפור הקצר', 'סדנת הסיפור'
  ],
  israeli_cinema: [
    'קולנוע ישראלי', 'israeli cinema', 'קולנוע ישראלי ב'
  ],
  film_history: [
    'תולדות', 'film history', 'היסטוריה קולנועית'
  ],
  kids_series: [
    'ילדים ונוער', 'kids', 'youth', 'סדרת ילדים'
  ],
  scenes: [
    'סצנות', 'scenes', 'עושים סצנות'
  ],
  web_series: [
    'סדרות רשת', 'web series', 'כתיבת סדרות'
  ],
  directing: [
    'בימוי', 'directing', 'בימוי לתסריטאים'
  ]
};

function matchCourseKey(eventTitle) {
  const titleLower = eventTitle.toLowerCase().trim();
  for (const [key, aliases] of Object.entries(COURSE_ALIASES)) {
    for (const alias of aliases) {
      if (titleLower.includes(alias.toLowerCase())) {
        return key;
      }
    }
  }
  return null;
}
```

### 6.3 שימוש בMatching

**ב-`sync_ics.py`:** בזמן parsing כבר קיים, אבל המנוע יהיה גם בClient:
```javascript
// בload של events.json — enrich בזמן ריצה אם course_key = null
events = rawEvents.map(ev => ({
  ...ev,
  course_key: ev.course_key || matchCourseKey(ev.title)
}));
```

**Lesson Match לTask:**
```javascript
function findLessonMatch(task) {
  const due = task.due_date;
  if (!due) return null;
  const windowStart = addDays(due, -6); // 6 ימים אחורה

  const matches = events.filter(ev => {
    const evDay = localDay(new Date(ev.start));
    if (evDay < windowStart || evDay > due) return false;
    if (task.linked_course_key && ev.course_key !== task.linked_course_key) return false;
    return ev.type === 'lecture' || ev.type === 'workshop';
  }).sort((a, b) => new Date(b.start) - new Date(a.start)); // ← קרוב ליעד ראשון

  return matches[0] || null; // ← הכי קרוב ל-due_date
}
```

---

## 7. עיצוב כרטיסיות — צבע קורס מלא

### 7.1 עיקרון

**לפני:** פס צבעוני בצד שמאל בלבד.
**אחרי:** כרטיסייה כולה צבועה ב-gradient קל מצבע הקורס.

### 7.2 חישוב צבע Background

```javascript
// courses.json: color = "#7C6FF7"
// → hexToRgb → rgba(124, 111, 247, 0.12)

function courseCardStyle(courseKey) {
  const course = courses.find(c => c.key === courseKey);
  if (!course) return '';
  const rgb = hexToRgb(course.color);  // {r,g,b}
  return `
    background: rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.12);
    border-top: 3px solid ${course.color};
    border-left: 3px solid ${course.color};
  `;
}
```

### 7.3 אירועי לוח שנה — Custom Events

עם צבע שנבחר:
```javascript
function customEventStyle(event) {
  const rgb = hexToRgb(event.color);
  return `
    background: rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, 0.18);
    border-left: 3px solid ${event.color};
  `;
}
```

### 7.4 Accessibility

- `color-contrast` ratio ≥ 4.5:1
- אם צבע הקורס כהה → טקסט לבן; אם בהיר → טקסט כהה (לפי luminance)

```javascript
function contrastTextColor(hexColor) {
  const {r,g,b} = hexToRgb(hexColor);
  const luminance = (0.299*r + 0.587*g + 0.114*b) / 255;
  return luminance > 0.5 ? '#111' : '#FFF';
}
```

---

## 8. הגדרות עיצוב אישי

### 8.1 פתיחת Settings Modal

**כפתור:** ⚙ בTopbar (קיים), מורחב עכשיו.

### 8.2 מבנה Settings Modal

```
┌──────────────────────────────────────────────────────┐
│  ⚙ הגדרות                                    [✕]   │
├──────────────────────────────────────────────────────┤
│                                                       │
│  👤 פרופיל                                           │
│  ──────────────────────────────────────────          │
│  שם משתמש   [שם שם ____________]                    │
│  ID משתמש   [abc123...] [📋 העתק]                   │
│                                                       │
│  🎨 עיצוב                                            │
│  ──────────────────────────────────────────          │
│  ערכת צבעים     [● Dark] [○ Darker] [○ AMOLED]      │
│                 [○ Dim]  [○ Custom]                   │
│                                                       │
│  צבע Accent     [● סגול #7C6FF7] [○ כחול] [○ ורוד]  │
│                 [○ ירוק] [○ תפוז] [⬛ custom #____]   │
│                                                       │
│  גופן            [● Heebo] [○ Assistant] [○ Rubik]   │
│                                                       │
│  גודל גופן       [A-] [12px ────●──── 18px] [A+]    │
│                                                       │
│  רדיוס פינות    [□ חד] [◩ בינוני ●] [○ עגול]         │
│                                                       │
│  אנימציות       [● הפעל] [○ כבה] [○ מופחת]          │
│                                                       │
│  🪟 פריסה                                            │
│  ──────────────────────────────────────────          │
│  רוחב Sidebar    [200px ────●──── 420px] (340px)    │
│                                                       │
│  Kanban position [● מעל הלוח שנה] [○ מתחת]          │
│                 [○ גוף נפרד]                          │
│                                                       │
│  הצג KPIs        [● הצג] [○ הסתר]                   │
│                                                       │
│  מספר ימים בלוח  [● 3 ימים] [○ 5 ימים] [○ שבוע]    │
│  (Desktop only)                                       │
│                                                       │
│  📅 לוח שנה                                          │
│  ──────────────────────────────────────────          │
│  שיעורי ICS מוצגים  [● כולם] [○ קב. א בלבד]        │
│                      [○ קב. ב בלבד]                  │
│                                                       │
│  Custom events ב-ICS   [● הצג] [○ הסתר]             │
│                                                       │
│  שעת "היום" מתחיל    [08:00 ────●──── 08:00]        │
│  (scroll default)                                     │
│                                                       │
│  📊 סמסטר ב                                          │
│  ──────────────────────────────────────────          │
│  תאריך סיום סמסטר ב  [30/06/2026]                   │
│  תאריך התחלה סמסטר ב [01/02/2026]                   │
│                                                       │
│  💾 localStorage                                      │
│  ──────────────────────────────────────────          │
│  [🗑 נקה נתונים מקומיים]  [📤 ייצא הגדרות]          │
│  [📥 ייבא הגדרות]                                    │
│                                                       │
│  [שמור שינויים]                                      │
└──────────────────────────────────────────────────────┘
```

### 8.3 ערכות צבעים

| ערכה | Background | Surface | Accent |
|------|-----------|---------|--------|
| **Dark** (ברירת מחדל) | `#09090F` | `#11111C` | `#7C6FF7` |
| **Darker** | `#050508` | `#0A0A14` | `#7C6FF7` |
| **AMOLED** | `#000000` | `#050505` | `#9C88FF` |
| **Dim** | `#1A1A2E` | `#16213E` | `#6FBBF7` |
| **Custom** | color picker | color picker | color picker |

### 8.4 שמירת הגדרות

```javascript
// localStorage key: 'userSettings'
const defaultSettings = {
  // profile
  userName: '',
  userId: '',

  // theme
  colorScheme: 'dark',           // 'dark'|'darker'|'amoled'|'dim'|'custom'
  accentColor: '#7C6FF7',
  fontFamily: 'Heebo',           // 'Heebo'|'Assistant'|'Rubik'
  fontSize: 14,                  // 12-18px
  borderRadius: 'medium',        // 'sharp'|'medium'|'round'
  animations: 'full',            // 'full'|'off'|'reduced'

  // layout
  sidebarWidth: 340,
  kanbanPosition: 'above',       // 'above'|'below'|'separate'
  showKPIs: true,
  calDays: 3,                    // 3|5|7

  // calendar
  lessonGroup: 'all',            // 'all'|'a'|'b'
  showCustomEventsInCal: true,
  calScrollHour: 8,

  // semester
  semesterBStart: '2026-02-01',
  semesterBEnd: '2026-06-30',
};
```

### 8.5 CSS Custom Properties — Apply Settings

```javascript
function applySettings(settings) {
  const root = document.documentElement;

  // Accent color
  root.style.setProperty('--accent', settings.accentColor);
  root.style.setProperty('--accent-rgb', hexToRgbStr(settings.accentColor));

  // Backgrounds
  const scheme = COLOR_SCHEMES[settings.colorScheme];
  root.style.setProperty('--bg', scheme.bg);
  root.style.setProperty('--surface', scheme.surface);

  // Font
  root.style.setProperty('--font-family', settings.fontFamily);
  root.style.setProperty('--font-size-base', settings.fontSize + 'px');

  // Border radius
  const radii = { sharp: '4px', medium: '12px', round: '20px' };
  root.style.setProperty('--radius', radii[settings.borderRadius]);

  // Animations
  if (settings.animations === 'off') {
    root.style.setProperty('--transition', 'none');
    root.style.setProperty('--anim-duration', '0s');
  } else if (settings.animations === 'reduced') {
    root.style.setProperty('--anim-duration', '0.1s');
  }

  // Layout
  document.querySelector('.sidebar').style.width = settings.sidebarWidth + 'px';
}
```

---

## 9. פיצ'רים נוספים שהוספתי

### 9.1 Notification / Reminder System

**מה זה:** כפתור 🔔 בTopbar — מציג popover עם תזכורות.

```
🔔 (3)
┌────────────────────────────────────┐
│  🔴 פגר! ביקורת מחזה — 3 ימים     │
│  🟡 ל-36 שעות: עיבוד תסריט        │
│  📅 מחר: שיעור תחקיר 09:00        │
└────────────────────────────────────┘
```

**Data:** generated client-side, לא Firebase.

### 9.2 Progress Bar לכל קורס

**מיקום:** מתחת לKPIs — סליידר קטן עם progress כל קורס.

```
תחקיר          ████████░░  4/8 שיעורים
קולנוע ישראלי  █████░░░░░  5/10 שיעורים
תולדות         ██████████  ✅ הושלם
```

### 9.3 Fullscreen Calendar Mode

**F11 / כפתור ⛶:** מרחיב את לוח השנה למסך מלא — עם sidebar מינימלי.

### 9.4 Quick Add — Cmd+K / Ctrl+K

**Command Palette:**
```
┌──────────────────────────────────────┐
│  🔍  ⌘K   [חפש או צור...]           │
│  ──────────────────────────────────  │
│  ✚ משימה חדשה                        │
│  ✚ אירוע חדש                         │
│  📅 עבור לתאריך...                   │
│  📋 הצג/הסתר Kanban                  │
│  ⚙ פתח הגדרות                        │
└──────────────────────────────────────┘
```

### 9.5 Statistics Page / Modal

**כפתור 📊 בTopbar:**
```
📊 סטטיסטיקות שלי

הגשות השבוע: 3
הגשות החודש: 12
שיעורים שנוכחתי: 23/68 (34%)
ממוצע זמן לסגירת משימה: 4.2 ימים

Heatmap — ציר הזמן של הסמסטר
[ינ][פב][מר][אפ][מא][יו]
 ░░ ██ ██ ░░  ░  ░
```

### 9.6 Task Templates

**ב-Modal יצירת משימה:** dropdown "מתבנית":
- `ביקורת מחזה` → prefill כותרת + description
- `ניתוח קטע` → כנ"ל
- `טיוטת תסריט` → כנ"ל

Templates שמורים ב-localStorage.

### 9.7 Bulk Actions

**ב-Kanban:** checkbox על כל card + action bar:
```
[☑ 3 נבחרו]  [→ קדם לבתהליך]  [🗑 מחק]  [📚 שנה קורס]
```

### 9.8 Keyboard Shortcuts

| מקש | פעולה |
|-----|-------|
| `Ctrl+K` | Command Palette |
| `N` | משימה חדשה |
| `E` | אירוע חדש |
| `←/→` | ניווט לוח שנה |
| `T` | קפוץ להיום |
| `ESC` | סגור modal |
| `1/2/3/4` | עבור לעמודת Kanban |

**מיפוי מוצג בSettings:**
```
⌨ קיצורי מקלדת
  N — משימה חדשה
  E — אירוע חדש
  ...
```

### 9.9 Pinboard — עריכת פריטים קיימים

**כרגע:** ניתן רק ליצור ולמחוק.
**חדש:** כפתור ✏ על פריט pinboard → modal עריכה.

### 9.10 Undo / Redo

**Toast notification** אחרי מחיקה:
```
✅ המשימה נמחקה  [בטל — 5 שניות]
```
Buffer של 5 שניות לפני commit ל-Firebase.

### 9.11 Export / Import Tasks

**ב-Settings:**
- ייצא כל המשימות → JSON
- ייצא → CSV לExcel
- ייצא כל האירועים → ICS מלא (tasks + custom events)

### 9.12 Dark/Light Contrast Toggle

**כפתור ☀/🌙 בTopbar** — toggle מהיר בין Dark ו-Dim ו-AMOLED.

### 9.13 Lesson Detail Popover

**לחיצה על שיעור בלוח שנה** (ICS) → Popover:
```
┌──────────────────────────────────────┐
│ 🟣  תחקיר — שיעור #7               │
│  📅 ראשון, 18.3.2026                │
│  ⏰ 09:00 — 12:00 (180 דקות)        │
│  👤 סיגל רש                         │
│  📍 (מיקום ריק)                     │
│                                      │
│  📋 משימות קשורות לשיעור זה:        │
│  • ביקורת מחזה — יעד 20/03          │
│                                      │
│  [+ הוסף משימה קשורה]               │
└──────────────────────────────────────┘
```

### 9.14 Course Filter בלוח שנה

**Chips מעל הלוח שנה:**
```
[כולם] [תחקיר] [קולנוע ישראלי] [תולדות] [+custom]
```
לחיצה → מסנן לקורס זה בלבד.

### 9.15 Sticky Notes / Quick Memos

**אזור קטן בSidebar** (מתחת לPinboard) — textarea קטן לכתיבת הערות מהירות.
שמור ב-localStorage.

---

## 9.5-CRITICAL — Lesson-Task Match: הלב של המערכת

### הרעיון המרכזי

כשמשתמש פותח משימה ("ביקורת מחזה") הוא בדרך כלל מתחיל לעבוד עליה **ביום שיעור מסוים** — למשל "אחרי שיעור תחקיר #5". תאריך הגשה (due_date) גם קשור לרוב לשיעור הבא ("צריך להגיש עד לפני שיעור #7").

**המטרה:** לתת למשתמש *ויזואליזציה אוטומטית* של הקשר הזה — בלי שצריך להקליד כלום.

---

### ה-Match הדו-כיווני

#### 1. Match ל-Opening Date ("נפתח ביום שיעור X")

כשמשתמש בוחר `opening_date`:
- המערכת מחפשת שיעורים **באותו יום** עצמו
- אם נמצא שיעור של `linked_course_key` → **הכי חזק**
- אם נמצא שיעור כלשהו → **match משני**

```
📅 תאריך פתיחה: ראשון 12.3.26 ← נבחר

💡 מאץ! ביום זה:
   🟣  תחקיר — שיעור #5  |  09:00–12:00
   ← המשימה נפתחת ביחד עם השיעור הזה
```

**שמירה בFirebase:**
```javascript
{
  opening_lesson_match: {
    event_uid: "abc123",
    course_key: "tachkir",
    lesson_number: 5,
    lesson_date: "2026-03-12"
  }
}
```

---

#### 2. Match ל-Due Date ("להגיש לפני שיעור Y")

כשמשתמש בוחר `due_date`:
- חיפוש בחלון 6 ימים לאחור מה-due_date
- מוצא שיעור של `linked_course_key` הקרוב ביותר ל-due_date
- מציג: "כנראה להגשה **לפני** שיעור #7 של תחקיר"

```
📅 תאריך יעד: רביעי 20.3.26 ← נבחר

💡 מאץ! שיעור קרוב:
   🟣  תחקיר — שיעור #7  |  ראשון 18.3.26  09:00
   ← 2 ימים לפני היעד
   "הגש לפני שיעור 7"
```

---

#### 3. תצוגת Match בכרטיסיית Kanban

כרטיסייה כוללת שורת match **ויזואלית**:

```
┌──────────────────────────────────────────────────┐
│ (background: rgba(purple, 0.12))                 │
│                                                   │
│  🔴 דחוף         🟣 תחקיר                        │
│                                                   │
│  ביקורת מחזה — "אוטלו"                           │
│                                                   │
│  ┌──────────────────────────────────────────┐    │
│  │  🔓 נפתח ב-12/03   ←→   📅 יעד 20/03   │    │
│  └──────────────────────────────────────────┘    │
│                                                   │
│  ┌── match ────────────────────────────────┐     │
│  │ 🎓 נפתח עם: תחקיר #5 | 12/03 09:00    │     │
│  │ 🎓 הגש לפני: תחקיר #7 | 18/03 09:00   │     │
│  └─────────────────────────────────────────┘     │
│                                                   │
│  [→ קדם]   [✏ ערוך]   [🗑 מחק]                  │
└──────────────────────────────────────────────────┘
```

---

#### 4. Timeline View — ציר זמן משימה×שיעורים

בלחיצה על כרטיסייה (expand) — ציר זמן מינימלי:

```
פתיחה           שיעור פתיחה       שיעור יעד         יעד
 12/03  ─────────── 12/03 ─────────── 18/03 ─────── 20/03
  🔓              🎓 #5             🎓 #7            📅
                  תחקיר             תחקיר         הגשה
```

זה נותן **הקשר חזותי מיידי** מבלי להסביר כלום.

---

#### 5. Smart Suggestion — Opening Date Autofill

כשמשתמש בוחר `due_date` אבל **לא** `opening_date`:
```
💡 רוצה להגדיר תאריך פתיחה?
   הצעה: ראשון 12/03 (שיעור תחקיר #5)
   [✅ כן] [❌ לא, תודה]
```

---

#### 6. Warning — אין שיעורים בחלון הזמן

אם נבחר `due_date` ואין שיעורים ב-6 ימים לפני:
```
ℹ️ לא נמצאו שיעורים לפני מועד זה
   (אין match ידוע)
```

---

#### 7. שמירת Match בFirebase

```javascript
// tasks collection — שדות Match:
{
  // ... שדות קיימים ...
  opening_date: "2026-03-12",
  due_date: "2026-03-20",

  opening_lesson_match: {           // ← חדש
    event_uid: "abc-uid-123",
    course_key: "tachkir",
    lesson_number: 5,
    lesson_date: "2026-03-12",
    start_time: "09:00"
  } | null,

  due_lesson_match: {               // ← חדש
    event_uid: "def-uid-456",
    course_key: "tachkir",
    lesson_number: 7,
    lesson_date: "2026-03-18",
    start_time: "09:00",
    days_before_due: 2
  } | null
}
```

---

#### 8. חישוב Match — הפונקציות

```javascript
// מחפש שיעורים ביום מסוים
function findLessonsOnDate(dateStr, courseKey = null) {
  return events.filter(ev => {
    const evDay = localDay(new Date(ev.start));
    if (evDay !== dateStr) return false;
    if (courseKey && ev.course_key !== courseKey) return false;
    return ev.type === 'lecture' || ev.type === 'workshop';
  });
}

// מחפש שיעור הקרוב ביותר לפני due_date
function findDueLessonMatch(dueDate, courseKey = null) {
  const windowStart = addDays(dueDate, -6);
  const candidates = events.filter(ev => {
    const evDay = localDay(new Date(ev.start));
    if (evDay < windowStart || evDay >= dueDate) return false;
    if (courseKey && ev.course_key !== courseKey) return false;
    return ev.type === 'lecture' || ev.type === 'workshop';
  });
  if (!candidates.length) return null;
  // הכי קרוב ל-due_date (הכי גדול)
  candidates.sort((a, b) => new Date(b.start) - new Date(a.start));
  const ev = candidates[0];
  const daysBeforeDue = Math.ceil(
    (new Date(dueDate) - new Date(localDay(new Date(ev.start)))) / 86400000
  );
  return {
    event_uid: ev.uid,
    course_key: ev.course_key,
    lesson_number: ev.lesson_number,
    lesson_date: localDay(new Date(ev.start)),
    start_time: fmtTime(new Date(ev.start)),
    days_before_due: daysBeforeDue
  };
}

// מחפש match לpening_date (שיעור באותו יום)
function findOpeningLessonMatch(openingDate, courseKey = null) {
  const lessons = findLessonsOnDate(openingDate, courseKey);
  if (!lessons.length) {
    // אם לא נמצא לקורס הספציפי, חפש כלשהו
    return findLessonsOnDate(openingDate, null)[0] || null;
  }
  const ev = lessons[0];
  return {
    event_uid: ev.uid,
    course_key: ev.course_key,
    lesson_number: ev.lesson_number,
    lesson_date: openingDate,
    start_time: fmtTime(new Date(ev.start))
  };
}
```

---

## 10. מבנה Firebase

### Collections

```
sam-spiegel (Firestore)
├── tasks/
│   └── {taskId}
│       ├── title: string
│       ├── description: string
│       ├── due_date: "YYYY-MM-DD" | null
│       ├── opening_date: "YYYY-MM-DD" | null   ← חדש
│       ├── course_key: string | null
│       ├── status: "active" | "archived"
│       ├── created_by: string
│       ├── created_at: Timestamp
│       └── linked_event_uid: string | null
│
├── personal_status/
│   └── {userId}/
│       └── tasks/
│           └── {taskId}
│               ├── status: "none"|"todo"|"inprogress"|"submitted"
│               └── updated_at: Timestamp
│
├── links/              (קיים — Pinboard)
│   └── {linkId}
│       └── ... (קיים)
│
└── custom_events/       ← חדש
    └── {eventId}
        ├── title: string
        ├── description: string
        ├── start_date: "YYYY-MM-DD"
        ├── start_time: "HH:MM" | ""
        ├── end_date: "YYYY-MM-DD"
        ├── end_time: "HH:MM" | ""
        ├── all_day: boolean
        ├── color: "#HEX"
        ├── icon: string
        ├── category: string
        ├── linked_course_key: string | null
        ├── created_by: string
        ├── created_at: Timestamp
        └── updated_at: Timestamp
```

### Firestore Rules (להוסיף)

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /tasks/{taskId} {
      allow read, write: if true;
    }
    match /personal_status/{userId}/tasks/{taskId} {
      allow read, write: if true;
    }
    match /links/{linkId} {
      allow read, write: if true;
    }
    match /custom_events/{eventId} {  // ← חדש
      allow read, write: if true;
    }
  }
}
```

---

## 11. ארכיטקטורה טכנית

### 11.1 State גלובלי — כל המשתנים

```javascript
// === DATA ===
let events = [];                  // ICS events (read-only)
let courses = [];                 // Course definitions
let tasksData = [];               // Firebase tasks
let customEventsData = [];        // Firebase custom_events ← חדש
let linksData = [];               // Firebase links (pinboard)
let personalStatus = {};          // taskId → status

// === UI STATE ===
let calStart = 'YYYY-MM-DD';      // 3-day window start
let searchQ = '';                 // global search
let kanbanFilter = null;          // null | 'none'|'todo'|'inprogress'|'submitted'
let kanbanCourseFilter = null;    // null | courseKey
let showPending = true;           // show tasks with future opening_date

// === MODALS ===
let taskModalMode = 'create';     // 'create' | 'edit'
let editingTaskId = null;
let eventModalMode = 'create';    // 'create' | 'edit' ← חדש
let editingEventId = null;        // ← חדש

// === DATE PICKERS ===
let dueDatePickerMonth = null;    // currently shown month in due date picker
let openDatePickerMonth = null;   // currently shown month in opening date picker
let activePickerField = null;     // 'due' | 'opening' | 'event_start' | 'event_end'

// === SETTINGS ===
let userSettings = { ...defaultSettings };   // ← חדש

// === USER ===
let userId = '';
let userName = '';
```

### 11.2 פונקציות חדשות

| קבוצה | פונקציה | תיאור |
|-------|---------|-------|
| **KPIs** | `kpiOpenTasks()` | מונה פתוחות |
| | `kpi72h()` | מונה דחופות |
| | `kpiWeeksLeft()` | שבועות לסוף סמסטר |
| | `kpiLessonsProgress()` | `{done, total}` |
| **Kanban** | `renderKanban()` | מרנדר 4 עמודות |
| | `renderKanbanColumn(status)` | עמודה בודדת |
| | `renderTaskCard(task)` | כרטיסייה |
| | `advanceTask(id)` | קדם סטטוס |
| **Custom Events** | `setupCustomEventsListener()` | Firebase listener |
| | `openEventModal(date?, event?)` | פותח modal |
| | `saveCustomEvent()` | שומר ל-Firebase |
| | `deleteCustomEvent(id)` | מוחק |
| | `renderCustomEvent(event, day)` | מרנדר ב-calendar |
| **Date Picker** | `renderMiniCalendar(field, month)` | מרנדר popup |
| | `getMiniCalDateInfo(dateStr)` | lessons+events לתאריך |
| | `selectDate(field, dateStr)` | בחר תאריך |
| | `closeDatePicker()` | סגור popup |
| **Matching** | `matchCourseKey(title)` | מציא course_key לevent |
| | `findLessonMatch(task)` | שיעור קרוב ל-due_date |
| **Settings** | `loadSettings()` | קרא מlocalStorage |
| | `saveSettings()` | שמור לlocalStorage |
| | `applySettings(settings)` | עדכן CSS variables |
| | `renderSettingsModal()` | בנה modal |
| **Styling** | `courseCardStyle(key)` | CSS לcard |
| | `hexToRgb(hex)` | המרת צבע |
| | `contrastTextColor(hex)` | לבן/שחור |

---

## 12. סדר פיתוח — Phases

### Phase 1 — Infrastructure (ראשון)
- [ ] הוסף `custom_events` Firebase collection + listener
- [ ] הוסף `opening_date` לtask schema + modal
- [ ] הוסף Settings localStorage + `applySettings()`
- [ ] Course Aliases engine + `matchCourseKey()`

### Phase 2 — Kanban
- [ ] מחק task list מה-sidebar
- [ ] בנה Kanban 4 עמודות (layout + CSS)
- [ ] `renderTaskCard()` עם course background color
- [ ] `findLessonMatch()` + badge
- [ ] Filter bar מעל הKanban

### Phase 3 — Date Picker
- [ ] Mini-calendar component (popup)
- [ ] Color coding תאריכים
- [ ] Lesson Preview panel
- [ ] חיבור לfields: due_date + opening_date

### Phase 4 — Custom Events
- [ ] Modal יצירת/עריכת event
- [ ] תצוגה בלוח שנה
- [ ] כפתור "+ אירוע" לכל עמודת יום
- [ ] Edit/Delete על events בלוח

### Phase 5 — KPIs
- [ ] עדכון 4 KPIs לנתונים החדשים
- [ ] Progress bar לשיעורים בסמסטר
- [ ] Modal פירוט לפי קורס

### Phase 6 — Settings UI
- [ ] Modal הגדרות מורחב
- [ ] כל הסעיפים (theme, layout, semester)
- [ ] Export/Import settings

### Phase 7 — Extra Features
- [ ] Notification/Reminder popover
- [ ] Quick Add Cmd+K
- [ ] Keyboard shortcuts
- [ ] Undo toast
- [ ] Lesson Detail popover
- [ ] Course filter chips בלוח שנה

---

*אפיון זה הוא source of truth. גרסה 2.0 — מרץ 2026.*
