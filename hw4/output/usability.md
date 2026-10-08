# Campus Customs — Usability Improvements

Six improvements to the working shop: two on the front end, four behind it. For each: what was added, and why it is worth having for the shopper, the business, or both.

| # | Improvement | Where |
| --- | --- | --- |
| [FE1](#fe1--handsome-dan-in-the-chat) | Handsome Dan in the chat, with a discount for members | Front end |
| [FE2](#fe2--a-star-rating-at-the-moment-of-buying) | A star rating at the moment of buying | Front end |
| [BE1](#be1--remembering-which-discounts-a-shopper-cared-about) | Remembering which discounts a shopper cared about | Back end |
| [BE2](#be2--saving-ratings-against-the-purchase) | Saving ratings against the purchase | Back end |
| [BE3](#be3--a-lighter-model-for-the-light-work) | A lighter model for the light work | Back end |
| [BE4](#be4--an-assistant-that-does-not-assume) | An assistant that does not assume | Back end |

---

## FE1 — Handsome Dan in the chat

### What was added

Handsome Dan now sits at the top of the chat panel, **drawn entirely in HTML and CSS** — no image file, nothing generated. He is a component of shaped `div`s, so he is sharp at any size, costs nothing to download, and nods gently when he greets someone.

He behaves differently depending on who opened the panel:

| | A guest sees | A signed-in shopper sees |
| --- | --- | --- |
| Dan says | "Welcome in. Members get a discount from me every now and then — ten percent off, just for being one of ours." | A line written for them, naming them: *"Welcome to Campus Customs, Test; as Handsome Dan, I am pleased to offer you 10 percent off."* |
| Below him | **Join for member discounts**, and a quieter link to log in | A navy card: **10% OFF**, the code, and **Tell me more** |

**The discount is the only reason to join that the shop ever gives.** Kept conversations and saved ratings are how the shop works, not benefits to a shopper — being told the shop will remember you is at best uninteresting and at worst slightly off-putting. So every guest-facing surface leads with the ten percent and nothing else: Dan's line, the join button, the Log in and Create Account pages, the prompt a guest sees when they press Buy, and what the assistant itself is permitted to say. The agent's rule is explicit: *that is the only reason to sign in that you should ever give.* Asked "why should I make an account?" it answers that members sometimes receive a discount from Handsome Dan, and offers to help without one.

**The discount is occasional, not constant.** The backend decides whether Dan is due to offer one: a shopper must have no usable code, and at least 20 hours must have passed since the last offer. Reopening the panel does not produce a new code. That is what "every now and then" has to mean if the gesture is to feel like a gesture.

The percentage is never the model's to choose. Dan's sentence is *written* by the light model, but the figure comes from the database, and if the sentence comes back without the right number in it, the shop's own written line is used instead.

### Why it helps

**For the shopper.** The panel stops being a text box and becomes someone receiving you. A guest learns, in one sentence and without a popup, exactly what an account is worth to them — ten percent — rather than a list of things the shop finds convenient. A member is recognised, and occasionally given something, by the mascot they already have affection for.

**For the business.** This is the registration prompt, and it is placed where intent already is: the moment someone starts asking questions. It answers "why would I make an account" with the one answer a shopper actually values, instead of asking for an email on principle. And because the discount is rationed by the server, the shop controls its margin; a shopper cannot farm codes by reopening a panel.

---

## FE2 — A star rating at the moment of buying

### What was added

A product page now has a **Buy** button that becomes active once a size is chosen. Pressing it does not complete the order. It opens a short step that asks:

> **Before we wrap it** — How would you rate the Basic Hoodie Big Yale?
> ★ ★ ★ ★ ★  *optional*

Along with the size, the price, a tick-box to apply Handsome Dan's code, and **Complete order**. The rating is optional; being asked is not. The stars light on hover, and clicking a chosen star again clears it.

Above the price, every product page now shows what buyers made of it — **★★★★★ 4.0 out of 5 · 1 buyer** — or "No ratings yet" when nobody has bought one.

Guests who press Buy are shown the member discount rather than a login wall.

### Why it helps

**For the shopper.** Ratings are the thing a photograph cannot tell you, and they come from people who actually paid. Being asked at the moment of purchase is a single click at a moment of goodwill — not an email three days later. And "No ratings yet" is shown honestly rather than dressed up as five stars.

**For the business.** Rating response rates collapse when the ask is separated from the purchase; asking in the flow is the cheapest review collection there is. Reviews raise conversion on everything that has them, and the shop gets an early signal when a garment disappoints — a run of two-star ratings is a quality problem visible before the returns arrive.

---

## BE1 — Remembering which discounts a shopper cared about

### What was added

A `discount_offers` table recording every offer Dan makes: who it went to, the code, the percentage, when it was offered, **when they showed interest**, what they said, and whether it was used.

Interest is captured from both directions:

- Pressing **Tell me more** in the panel records it directly.
- Asking the assistant about it — what it is, whether it still stands, how to use it — makes the agent call its `record_discount_interest` tool, with a note in its own words. Verified: asking "Tell me more about my discount" wrote `interested_at` and the note *"Shopper asked for more information about their discount."*

The agent is given a summary with every message — *"offered 1; asked about 1; currently holds 10% code DAN10-4C81AF"* — so it knows this shopper's relationship with discounts without being able to see anybody else's.

### Why it helps

**For the shopper.** The shop stops repeating itself. Someone who already asked about their code does not get it explained again; someone who ignores discounts is not nagged with them.

**For the business.** This is the difference between issuing discounts and understanding them. Offered-versus-asked-versus-used is a redemption funnel, and it answers questions a flat discount cannot: who responds to a discount at all, whether interest converts, and whether 10% is doing any work. Over time it is the basis for offering discounts to the shoppers they actually move, which is where discount margin is won or lost.

---

## BE2 — Saving ratings against the purchase

### What was added

Two tables. `purchases` records what was bought, in what size, at what price, and under which discount code. `product_ratings` records the stars — and holds a `purchase_id`.

That foreign key is the point. **A rating in this database is always traceable to someone who bought the garment.** `UNIQUE (purchase_id)` allows one rating per purchase, and `CHECK (stars BETWEEN 1 AND 5)` makes the range a property of the database rather than a rule the form happens to follow. A purchase is also refused for a size that is not in stock, and for a product that does not exist.

The average feeds three places: the product page, the agent's `product_rating` tool, and the shop's own view of its stock.

### Why it helps

**For the shopper.** Ratings that cannot be left by someone who never bought the thing are worth reading. It is a quieter promise than a "verified buyer" badge and a stronger one, because it is enforced by the schema rather than asserted in the interface.

**For the business.** Ratings joined to purchases answer better questions than ratings alone: how a garment rates by size, whether discounted buyers rate differently from full-price ones, which products earn repeat custom. And it closes the loop on the discount — the same row knows what was paid and what was thought of it.

---

## BE3 — A lighter model for the light work

### What was added

Two measures, in order of how much they matter.

**First, most of this work needs no model at all.** Issuing a discount, recording interest, saving a rating and reading an average are plain SQLite operations. They were built that way deliberately:

| Operation | Time | Model |
| --- | --- | --- |
| Issue a discount | 1.3 ms | none |
| Record discount interest | 0.5 ms | none |
| Read a product's rating | 0.2 ms | none |
| Handsome Dan's sentence | 421 ms | `gpt-5.4-nano` |

**Second, where a model is genuinely wanted, it is the light one.** Dan's greeting is the only model call in these features, and it runs on `gpt-5.4-nano` rather than the shop assistant's `gpt-5.6-luna`. Measured on the same prompt over three runs, median 1.61s against 1.89s, at a fraction of the cost per token. Writing one warm sentence from a bulldog does not need the larger model.

Dan's line also **fails soft**: if the light model is slow or unavailable, the shopper still gets their discount, with a written line in place of a generated one. The offer is a database fact; the sentence is only its wrapping.

### Why it helps

**For the shopper.** The parts of the shop that should feel instant are instant, because they are a database query and not a conversation. Nobody waits on a language model to be told their own discount code.

**For the business.** The honest saving here is not the cheaper model, it is the calls that were never made. A discount that costs a model call every time it is displayed is a discount with a running cost; this one costs a millisecond. The cheaper model then takes the one call that remains. And because that call degrades to a written line, a provider outage costs the shop a sentence rather than a sale.

---

## BE4 — An assistant that does not assume

### What was added

A standing rule in the system prompt: **say only what you know** — what the tools returned, what the shop said about this shopper, and what this shopper actually said. Everything else is a guess, and a guess stated as a fact is a lie.

Spelled out, the assistant must not assume:

- **Their size.** Not from what they looked at, not from what they bought before. Ask.
- **That they are buying.** They may be browsing, buying for someone else, or curious.
- **Who they are** — year, college, team, gender, or whether they are a student, parent or alumnus. *Someone asking about a Yale Dad crewneck is not necessarily a father.*
- **What they can spend.** No price is described as cheap, expensive or a bargain.
- **Why they want it.** No occasion they have not given.
- **That they liked something.** A garment shown before is not a preference; only what they said is.

With matching rules for the new features: state only the discount actually issued, never promise a future one, never invent an average, and say plainly when a garment has no ratings.

Verified:

| Asked | Answered |
| --- | --- |
| "What size should I get?" | "We can't choose a size reliably without knowing your usual sweatshirt size or preferred fit... which of those do you normally wear?" |
| "Can you give me 30% off instead?" | "We cannot offer 30% off. Your current discount is 10% with code DAN10-4C81AF." |
| "Will I get another discount next week?" | "We cannot say whether another discount will be offered next week." |
| "Everyone says it's the best hoodie on campus, right?" | "We cannot say that... a 4.0 from one rating is not evidence that everyone on campus considers it the best." |
| "How is the Basic Hoodie Big Yale rated?" | "Rated 4.0 out of 5 from 1 rating." — the real figure |

### Why it helps

**For the shopper.** An assistant that guesses is exhausting, and occasionally insulting — being told what you must want because of the garment you clicked is worse service than being asked. One short question costs a moment; a wrong assumption costs trust, and sometimes a return.

**For the business.** Every invented fact is a liability the shop has to honour or disown. A promised discount that does not exist, a size confirmed that is out of stock, an average nobody earned — each becomes a refund, a complaint, or a customer who stops believing the shop. This rule is also what makes the ratings worth collecting: an assistant that would flatter a garment makes its own rating figures meaningless.

---

## A limitation worth stating

**A purchase does not reduce stock.** The `purchases` table records what was bought, but `inventory` is left untouched, so a garment bought here still shows its original counts. That is deliberate: the seeded stock figures are the evidence base for the rest of this homework, and quietly draining them would invalidate the earlier verification. A real shop would decrement inside the same transaction as the purchase insert, and would need to handle two shoppers buying the last one at once.
