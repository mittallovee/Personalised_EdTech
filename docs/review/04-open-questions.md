# 04 — Open Questions for the Product Owner

> Answer by number (short answers are fine; "don't know yet" is a valid answer — we'll record an assumption).
> Each answer feeds a specific document or decision (ADR).

## A. Business & scope (most important — answer these first)

**Q1. Who is this for?**
(a) Internal platform for one organization (e.g. one coaching company with many centres),
(b) SaaS sold to many independent institutes, or (c) both (internal first, SaaS later)?
→ *Decides tenancy model, billing, onboarding, isolation strength.*

**Q2. Content ownership across tenants.** Will there be a **platform-owned master question bank** that
tenants can use/license, or does every institute only see its own questions?
→ *Decides whether questions can be shared/referenced across tenants.*

**Q3. Existing systems and data.** Is there an existing question bank (how many questions, in what
format — Word, Excel, another tool like a "QBG")? An existing student app/LMS/ERP that must integrate?
→ *Decides migration plan and integration APIs.*

**Q4. Which apps in the first 12 months, and on which platforms?**
Content Studio (web) / Admin / Student practice app / Live exam app / Parent app / Partner API —
and Android, iOS, web?
→ *Decides MVP boundary and mobile technology.*

## B. Students & exams

**Q5. Live-exam scale and style.** Largest number of students in **one exam at the same time** (now and
in 3 years)? At home online, at test centres, or both? Any proctoring/lockdown requirement?
Pattern: JEE Main / JEE Advanced / NEET / school tests?
→ *Decides exam-engine architecture and load-testing targets.*

**Q6. Student identity.** How do students log in (phone OTP, email, Google, institute-issued ID)?
Are most students **under 18**? Do they belong to centres/batches/courses?
→ *Decides identity provider, DPDP parental-consent flow, org hierarchy.*

## C. Content & workflow

**Q7. Subjects, exams, languages at launch.** Physics only first? Which languages are required at day one
(English + Hindi?), and which ones later?

**Q8. Review workflow reality.** In your organization today, how many people check a question before it's
used? Is "reviewer" and "approver" the same person or different people? Should a small institute be able
to use a single-step workflow?
→ *Fixes inconsistency I-1.*

## D. Team, tech & money

**Q9. Your team.** Are you building solo, with a team (how many developers, what experience), or with an
agency? Will you use AI coding tools heavily? What is your own background (technical/non-technical)?
→ *Decides how opinionated/simple the stack must be.*

**Q10. Hosting and budget.** Any cloud preference or existing account (AWS/GCP/Azure)? Must data stay in
India? Rough monthly budget for infrastructure, and separately for AI usage?

**Q11. Technology preferences.** Any language/framework you or your team already know (TypeScript, Python,
Java, Flutter…)? Anything you specifically want to avoid?

**Q12. Timeline.** Target date for the first usable version (internal faculty using it), and for students
using it?

## E. Quality bar & external access

**Q13. Uptime and data-loss tolerance.** If the system is down for 1 hour during a normal day, how bad is it?
During a live exam? How much recent data could you afford to lose in a disaster (5 minutes? 1 hour? zero)?
→ *Becomes SLO, RPO and RTO numbers.*

**Q14. External API consumers.** Will **other companies/partners** call your API (e.g. another LMS pulling
tests or pushing students)? Or only your own apps?
→ *Decides partner auth, rate limits, public documentation, versioning promises.*

**Q15. Monetization.** Will institutes/students pay inside the platform (subscriptions, test series purchase)?
When?
→ *Not MVP, but affects tenancy and student-account design.*
