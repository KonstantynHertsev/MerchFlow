# MerchFlow — Roadmap

## Done ✅

### Core Pipeline
- [x] ZIP upload → image extraction (macOS metadata filtered)
- [x] GPT-4o-mini vision → structured JSON listing
- [x] Amazon stop-words filter in system prompt
- [x] Character limits enforced (Title 120, Bullet 256, Description 2000, Brand 50)
- [x] Auto-truncation at word boundary if AI exceeds limits
- [x] Trademark check against local stop-list
- [x] Parallel image processing (asyncio)
- [x] CSV export in 3 formats: LazyMerch, Flying Upload, Merch Titans

### Auth & Profiles
- [x] Register / Login / Logout (JWT, 7-day token)
- [x] User profiles with auto-save (brand, price, colors, department)
- [x] Multiple named profiles with switcher

### Monetization
- [x] 50 images/month free limit (resets on 1st of month)
- [x] Pro waitlist with email collection
- [x] Limit modal with waitlist form

### Admin
- [x] /admin.html — protected by ADMIN_EMAIL
- [x] Waitlist tab: emails + join date + Export CSV
- [x] Users tab: email, plan, usage this month, registered + Export CSV

### UI
- [x] Dark theme, English language
- [x] Drag & drop upload zone
- [x] Software selector: LazyMerch / Flying Upload / Merch Titans
- [x] TM warning badges on listing cards
- [x] Usage badge in header (color changes at 40/50)

---

## To Do 🔧

### Before Launch (critical)
- [ ] Deploy to Railway (or Render)
- [ ] Persistent database volume (SQLite survives redeploys)
- [ ] Verify real CSV column formats with LazyMerch / Flying Upload / Merch Titans
- [ ] Forgot password / password reset flow

### After First Users
- [ ] Stripe — Pro plan payment
- [ ] Welcome email on registration
- [ ] Generation history (user sees past batches)
- [ ] Mobile responsive design check
- [ ] Rate limiting (abuse prevention)
- [ ] Error monitoring (Sentry or similar)

### Growth
- [ ] Landing page (explain what it does, pricing, FAQ)
- [ ] Terms of Service + Privacy Policy
- [ ] Demo video (Loom, 90 sec)
- [ ] Reddit posts: r/AmazonMerch, r/printondemand, r/passive_income
- [ ] Facebook groups: Merch by Amazon, Print on Demand sellers
- [ ] Outreach to 5-10 YouTube merch creators (free Pro access for review)
- [ ] Product Hunt launch
- [ ] Twitter/X: #MerchByAmazon #printondemand #buildinpublic

---

## Promotion Steps (week by week)

**Week 1** — Reddit
Post in r/AmazonMerch, r/printondemand, r/passive_income.
Format: personal story + 2-min Loom demo. Reply to every comment.

**Week 2** — Facebook Groups
Search "Merch by Amazon", "Print on Demand sellers".
Same format: story + demo, not direct advertising.

**Week 3** — YouTube Outreach
Find 5-10 Amazon Merch YouTube channels.
Offer free Pro access in exchange for an honest review.

**Ongoing**
- Ship demo video (screen recording + voiceover, 90 sec max)
- Product Hunt listing
- Twitter/X with relevant hashtags
