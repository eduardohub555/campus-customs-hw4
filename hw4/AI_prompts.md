# AI Prompts Log — HW4

This file records the prompts I type as a vibe coder. One section per problem, updated as we work. For each problem: the problem number and title, at least one prompt I typed, and a follow-up prompt where I needed one (with one sentence on what was lacking after the first).

The evidence for this homework is the running site, the database writes, and the screenshots — not an extra proof essay beyond these prompts.

## Problem 1 — Vibe Coder Prompts

**Prompt 1 (initial):**
> /folder-joke HW4

**Follow-up prompt:**
> Let's start with Problem 1: Vibe coder prompts. Lets create AI_prompts.md and keep it updated as we work. As in previous homeworks, this file is the log of what you typed to your vibe coder. For each problem, put one section, each section must include: problem number and title, at least 1 prompt i typed, one follow-up prompt if i needed it (and one sentence on what was lacking after the first). The evidence is the running site (more to come), database writes, and screenshots (there is no need for an extra proof essay beyond these prompts)

**What was lacking:** The first prompt only set HW4 as the active workspace and proved it with a joke file; it did not yet ask for the prompt log or say what each section had to contain.

**Evidence:** [AI_prompts.md](AI_prompts.md) itself, which is the log this problem asked for.

## Problem 2 — Analyze the Database

**Prompt 1 (initial):**
> Now to Problem 2: Analyze the database. Show me the database data/campus_customs.db and give me a summary of the fields of each table so I can understand them. Explain in detail catalogue, inventory, and users. Start the file output/harness.md . Write down each table and each of its fields, and one short sentence (maximum 1 line) on why each field matters for the shop or the chatbot. We will keep growing this harness file in further problems (models, tools, safety, specs)

**Follow-up prompt:** None needed. The initial prompt named the database file, the three tables to explain in detail, the harness file to start, and the exact per-field format (one line on why each field matters).

**Evidence:** [harness.md](output/harness.md) — all four tables (`catalogue`, `inventory`, `users`, `chat_messages`), every field with a one-line reason, and the real row counts read out of the database.

**What the data showed:** 102 products, 612 inventory rows (102 x 6 sizes), 3 users, 22 chat messages. Integrity is clean — every product has inventory, no orphan stock rows, and all 102 product images exist on disk. Three issues were found and written into the harness because they affect how search must be built: `garment_type` has 22 spellings for 102 products (`short-sleeve t-shirt` and `short-sleeve T-shirt` are the same thing), 145 of 612 size rows are sold out, and three products have an empty `colors` array.

## Problem 3 — Build the Campus Customs Website

**Prompt 1 (initial):**
> Problem 3: Build the Campus Customs website. We need to scaffold a React + Vite + TypeScript front end for Campus Customs. Include a navigation bar at the top that links to the main pages: Home, Products, About Us, Log in, Create account. From https://yalebulldogblue.com pull the Campus Customs-style wording for "Home" (note the homework instructions ask to do the same for "About Us", but I can't find that main page. if you find it, then do the same for style wording). We need to write the pages in our own voice, so its important that you do not copy the original site text. I like a lot the desing of the Yale Club NYC webpage https://www.yaleclubnyc.org so you can find inspiration on doing something similar in terms of the page design. On the Products page, please show product images from the catalogue (data/products) with basic product information like name, price, description (make it short). We need that each product opens a single-item page (large image on one side, full product text on the other - description, price, size, stock (if quantity>0), colors when you have these); so clicking a card on Products should take the shoper there. Also, add a chat interface in the bottom right of the site (a floating chat panel is fine). It doesnt need to talk to an agent yet, so a stub that will call your backend later is enough for this Problem 3. We will need a small API soon to read the database. It's ok to start a simple FastAPI app in backend/main.py just to serve products and images, then we will grow it into the agent backend in Problem 5.

**Follow-up prompt:** None needed. The initial prompt specified the stack, the five navigation links, the two reference sites and what to take from each, the no-copying rule, the product card fields, the single-item page layout, the chat panel stub, and the FastAPI starting point.

**Evidence:** the running site at `http://localhost:5174`, [harness.md](output/harness.md) section 2, and the screenshots recorded while building it.

**What the reference sites gave:** yalebulldogblue.com confirmed the business — officially licensed Yale merchandise run by Campus Customs out of New Haven, organised by residential college, varsity sport, graduate school and family collections. Those themes shaped the Home page, but every sentence on the site is written from scratch. Your reading was right that there is no "About Us" page to draw from: the site has no mission or history page at all, so the About page is entirely our own. From yaleclubnyc.org came the design — navy and white, serif headings over a sans-serif interface, a crest in the navigation, a rotating hero with an overlay tagline, three cards, thin gold rules, generous whitespace.

**Two problems hit along the way:**
1. The desktop preview pane could not launch the dev server — its sandbox cannot read files under the HW4 folder, and the Chrome extension was not connected either. The servers run fine from the terminal, so the site was verified and screenshotted by driving the system Chrome with Playwright instead.
2. Vite's default port 5173 was already held by a dev server left running from Lecture 11, so this site runs on 5174 rather than killing your other app.

**One bug found and fixed:** product card footers did not line up when descriptions were different lengths, because the card body was not a flex column. Caught in the first home-page screenshot.

## Problem 4 — Create Account and Login

**Prompt 1 (initial):**
> Thanks, now to Problem 4: Create account and login. We need to build a normal create-account / login flow. For Create Account, consider: first name, last name, email, password, confirm password (of course, passwords have to match, lets make it case-sensitive). For Login: consider: email and password. New accounts must go into the users table we already saw in Problem 2. We need to be very careful, so make sure to store passwords securely so hackers (either human or AI) cannot access them, for that please use HASH. The seed database already has a test user we can use while building: Email is test@campuscustoms.yale.edu and Password is password
> Confirm that we can log in as that user, and I will create a brand-new account to check if its actually working. Once I finish that, you need to update output/harness.md with how auth works (what is stored for a user and how passwords are protected)

**Follow-up prompt:**
> when you are in create account, make sure htat the last name, email, password, etc, fit in the white box (you can make the white box larger. Make that the password needs at least one special character like "." and at least one number

**What was lacking:** the first build left the form inputs overflowing past the right edge of the white card, and the only password rule was a minimum length.

**What the follow-up changed:** the card went from 440px to 520px wide, and the real cause of the overflow was fixed — the form's grid children kept their default intrinsic input width because they had no `min-width: 0`, so the inputs sized themselves wider than their track. Every field now sits inside the card at both 1440px and 390px, checked against the card's measured bounds. Two password rules were added — at least one number and at least one special character (anything that is not a letter, digit or space) — enforced in `backend/main.py` and mirrored as a live checklist on the form that ticks as you type, with submit disabled until all three rules pass.

**Evidence:** the running site, [harness.md](output/harness.md) section 3.

**Confirmed, as asked:** `test@campuscustoms.yale.edu` / `password` signs in through the real form and the nav bar switches to "Hi, Test". The site is ready for you to create your own account.

**What the seed data decided:** rather than pick hashing parameters, the format was read back off the existing rows — PBKDF2-HMAC-SHA256, 120,000 iterations, a per-user salt, stored as `pbkdf2_sha256$<salt>$<hex>`. Recovering 120,000 iterations took a short search against the test user's known password. New accounts therefore hash identically to the seeded ones, and the test user keeps working.

**Security decisions worth naming:** passwords are never stored or logged, only derived; comparison is constant-time; a wrong password and an unknown email return the same message *and* take the same time, so neither can be used to discover which emails have accounts; the catalogue connection is read-only and only registration can write.

**Your account, confirmed:** you registered through the form and the row landed in `users` as id 6 (the address you signed up with, 2026-10-07), with a unique 16-character salt and a correctly shaped 95-character hash. The id is 6 rather than 4 because two scratch accounts were created during development to test the insert and the complexity rules, then deleted; SQLite does not reuse autoincrement ids. Audited afterwards: 4 users, 4 distinct salts, 4 distinct hashes, no plaintext password stored anywhere in the schema.

## Problem 5 — PydanticAI Agent Backend

**Prompt 1 (initial):**
> Now, to Problem 5: PydanticAI agent backend. Now we are going to build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into our front-end chat widget. Let's put the API app in backend/main.py (which is the file we need to run with Uvicorn. Keep the agent as these four files next to it (same idea as how we did for Homework 3): 1) backend/prompts/prompt.md : is the system prompt, we will grow this same file later; 2) backend/agent.py : is the agent entry/wiring; 3) backend/tools.py : are the tools the agent can call ; 4) backend/models.py : Pydantic / PydanticAI structured types.
> In main.py , expose a chat rout so that a message from the website returns a reply from the agent (including information for the products like price, sizes, color, description). ONLY respond information that the page explicitly has (do not make up any data nor go to any other webpage to find information. You can only use information from the yalebulldogblue webpage, information on folder HW4, and the design from the NYC Yale Club), remember don't giving any private information on emails or passwords. The agent should respond nicely, as if you were arriving to the Yale Club as a guest. Use my PORTKEYAPI key, but make sure no one (human nor AI) ever gets access to it.
> Put Campus Customs an elegant voice, and make sure it doesn't lie or makeup information, again it needs to treat users nicely and give the true proper information; I need you to put this into prompts/prompt.md (we will expand more tools and safety later). Start or update types in models.py for chat replies and/or product cards as needed. In output/harness.md, note how the front end talks to FastAPI and how the agent is loaded (prompt file + model). And it is important to make sure that the backend runs from the backend/ folder like this: uvicorn main:app --reload --port 8000

**Follow-up prompt:** None needed. The initial prompt specified the four-file layout, the chat route and what its replies must contain, the no-invention rule, the privacy rule, the Yale Club voice, the key handling, the models to add, the two harness sections, and the exact command the backend must run under.

**Evidence:** the running site, [harness.md](output/harness.md) section 4.

**The main design decision — the agent cannot state a wrong price.** Rather than let the model write prices and stock counts into its prose, it returns `reply` plus `product_ids`, and `main.py` builds the cards from the database afterwards. So every figure on screen is read from SQLite at that moment. An invented id finds nothing and is dropped — tested with `yale-jetpack-9000`, which never reached the browser.

**Privacy:** only the signed-in shopper's first name is passed to the agent. The email address and password hash never enter the prompt, and no tool can see the `users` table at all — so there is nothing private for the model to leak even under pressure. Asked "do you know my email address?" while signed in, it correctly said it has no access.

**The key:** read with `load_dotenv` from the course root `.env`, which sits outside HW4 and is git-ignored. Swept afterwards — the key appears nowhere inside HW4 and in no API response, including a chat message that asked for it directly.

**One thing found while testing:** a blunt "ignore your previous instructions" is rejected by the provider's own content filter before it reaches the model, which arrives as a 400. The first version reported that as "the assistant is unavailable", which was misleading since nothing was broken. It now answers with a courteous decline and a 200; genuine failures still return 502 and the real error goes only to the server log.

## Problem 6 — Tools: Product Info and Stock

**Prompt 1 (initial):**
> Thank you, now to Problem 6: Tools: Product info and stock. We need to give the agent the tools that look up real information from campus_customs.db such as: the product description, colors, prices, stock (by size when the customers ask!), and the type of garment. Remember, the agent must use the database, and it should not invent prices nor stock quantities nor inexistent colors for garments available. If a size is out of stock, and I tested this, the agent is doing a good job already on saying clearly that is out of stock and doing the job of a seller by offering additional products of the size that the customer may want (but again, use only the information on the database and dont lie nor make anything up).
> Expand prompts/prompt.md so the agent knows to call these tools for price, stock and the rest of the mentioned items related questions. Add or update return types in models.py
> In output/harness.md, list each tool and explain to me which model fields you chose for lookup results and also explain why

**Follow-up prompt:** None needed. The initial prompt named every lookup the tools must cover, the no-invention rule, the out-of-stock behaviour to preserve, the prompt expansion, the models to update, and exactly what the harness section had to explain.

**Evidence:** the running site, [harness.md](output/harness.md) section 5.

**What your observation changed.** You were right that the agent already offered alternatives when a size was gone — but it was doing that by guessing from an earlier search, with no way to confirm the substitute was actually available in the size asked for. A new tool, `find_available_in_size`, makes it reliable: everything it returns is confirmed in stock in that size, it can exclude the product that was unavailable, and it can stay within the same category so the suggestion is comparable. The prompt now sets out the sequence — say no plainly, name the sizes that remain, then offer confirmed alternatives.

**The field-choice principle,** written out in the harness: a lookup type carries every field the agent may need to *say*, and nothing the website alone uses. `image_url` and `search_tags` are deliberately withheld — a model never given a field cannot repeat it, and tags like "college merch" read as marketing copy if spoken aloud. The sharpest example is `SizeOption.quantity_in_size`, which is the count for *that one size* rather than the total: a garment with 60 units overall is no use if the only size left is XXL.

**Two rules the data forced.** `search_catalogue` gained `size` and `max_price` filters. And because three products have an empty `colors` list, the prompt now states that colours are only ever what the list contains — asked about the Benjamin Franklin T Shirt, the agent correctly said no colours are recorded instead of reading one off the name.

## Problem 7 — Chat Search That Updates the Page

**Prompt 1 (initial):**
> Lets now go to Problem 7: Chat search that updates the page. We are now adding a neat feature to our site. When someone asks about a type of item, like "what hoodies do you have?" or "what t-shirts do you have?", the agent should search the catalogue and the website must dynamically show those matching items as product cards (image, name, price, short description). This is an API contract: the agent returns structured product matches and then the front end renders them on the website (make it look very cool and again, use the Yale Club design so it looks elegant).
> After the dynamic product cards are loaded by this new feature, make sure the same simgle-item page behaviour that was built in Problem 3 still works: each product card (including the ones that the chat just included on the page) should still open that detail view which was a large image and a full description, when clicked.
> Update prompts/prompt.md and output/harness.md so it is clear how the search results reach the page

**Follow-up prompt:** None needed. The initial prompt specified the trigger, the card contents, that this is an API contract, the Yale Club styling, the requirement that chat-placed cards still open the Problem 3 detail view, and the two files to update.

**Evidence:** the running site, [harness.md](output/harness.md) section 6.

**The design decision that makes it work.** The results do not belong to the chat panel. They go into a React context above the router, and a band mounted at the top of `<main>` renders them. That is what lets them be *on the page* rather than in the conversation, survive navigation between pages, and be drawn by the very same `ProductCard` the catalogue uses — which is also why requirement two came for free: there is no second kind of card and no separate click path, so a chat-placed card opens the Problem 3 detail view by construction. Verified by clicking one through to `/products/basic-hoodie-big-yale`.

**One addition to the contract.** `AgentReply` and `ChatResponse` gained `result_title`, a two-to-four-word heading in the shop's voice ("Hoodies", "Available in XS"), so the band has an elegant title rather than a generic one. It is only returned when at least one card survived the database lookup, so an empty band with a heading over it is impossible.

**Two things changed after seeing it render.** The chat panel first closed itself when results arrived — presumptuous, and it hid the conversation, so it now stays open and adds a quiet line saying how many garments were placed on the page. And the sticky navigation bar was clipping the band's heading when it scrolled into view, fixed with `scroll-margin-top`; measured afterwards at nav bottom 72px against band header top 120px.

**A prompt change the feature required:** the agent is now told its ids become full cards on the page, so it should stop reciting prices and sizes that are about to appear immediately below its message, and should treat "what do you have?" as a request to *see* the garments rather than only read about them.

## Problem 8 — Customer Memory

**Prompt 1 (initial):**
> Thank you! Lets go to Problem 8: Customer memory. When a customer is logged in already, save their chat history in the database in an appropriate table and reload it when they return. The agent must know who is chatting (remember it has both the name and email, but also remember the agent cannot store passwords); put that in agent deps (or an equivalent clear pattern) and/or tools that the agent is able to call
> Also I need you to give the agent enough page context that if someone is on a product page and asks "do you have this in pink?", or "do you have a similar blue sweatshirt?", the agent knows which item they mean (for example, you can put code into the agent context).
> Guests can still chat, but history only needs to persist for logged-in users. To make myself clear, if a customer hasn't logged in, there should be no history recorded for that customer. Make sure you only record the history for users that have already logged-in. Maybe you can tell the customer "Hi CUSTOMER_NAME" when it has logged in, and "Welcome to Yale Campus Customs" for users that haven't logged in.
> Document in output/harness.md how the user chat history is stored (for example, use its name and email as identifiers, remember the products/garment type the customer asked for, the colors, sizes, and if they told you something about their taste like "I prefer sweatshirts to t-shirts"), what customer fields the agent sees, and how the page context is passed

**Follow-up prompt:** None needed. The initial prompt specified the storage requirement, the identity fields and the password exclusion, the page-context behaviour with two worked examples, the guest rule stated twice for emphasis, both greetings, and the three things the harness had to document.

**Evidence:** the running site, [harness.md](output/harness.md) section 7.

**The guest rule is structural, not a check.** Every chat-history function takes a `user_id` as its first argument, so there is no code path that can store a turn without one — an anonymous conversation leaves nothing behind by construction rather than by remembering to test for it. Verified by sending three messages as a guest and counting rows before and after: 38, then 38.

**Keyed on `user_id`, not name or email.** You suggested name and email as identifiers; they are what the agent uses to *recognise and address* the shopper, but the rows are filed under the integer primary key. A name is not unique and an email can change; the key cannot, and it is already the foreign key the table was built around.

**Page context carries an id, never figures.** The front end derives `{ path, product_id, category }` from the URL and sends it with every message. The agent is told *which* garment "this" refers to and is instructed to call `get_product` for the details — so page context can never become the source of a stale price. Both of your examples work: "do you have this in pink?" on the Basic Hoodie page answered "recorded in navy blue and white, not pink", and "a similar blue sweatshirt?" compared against that hoodie and returned four crewnecks.

**The email, raised and settled.** I flagged that a field the model holds is a field a clever prompt might try to extract, and you confirmed you want the email kept. It stays.

**Follow-up prompt:**
> yeah lets keep email

**What was lacking:** the first version protected the email with the prompt alone, which is an instruction rather than a guarantee.

**What the follow-up changed:** since the email is staying, the protection became structural as well. `_redact_account_details()` in `main.py` now checks every reply before it leaves the server; if the signed-in shopper's address appears it becomes `[withheld]`, a warning is logged, and the redacted text is what is both sent and stored, so a slip reaches neither the browser nor the disk. Four extraction attempts were tried — a plain request, a "for my records" appeal, a "character by character memory test", and a fake shop policy — and the prompt refused all four, so the guard has not yet had to fire.

**A bug caught while building that guard.** The first version also matched the email's local part on its own, which looked safer and was worse: your own account's local part is your first name, so it turned "Hi <name>. Welcome back to Campus Customs." into "Hi [withheld]." — censoring the exact first-name greeting Problem 8 asked for. It now matches the complete address only, which has no false positives.

## Problem 9 — Usability Improvements

**Prompt 1 (initial):**
> Great, lets now go to Problem 9: Usability improvements. We have the core shop now, so the next step is to improve it. Let's do the following 2 front-end usability improvements: 1) When the user logs in, he should have some more cool stuff, like include in the chat a figure of handsome dan greeting the logged-in user. To make sure users want to login, for the users that haven't logged in include a message that they can join for additional benefits. Now backed to the logged-in users: offer them a 10% every now and then that handsome Dan makes them feel special for belonging to Yale! 2) ask a person how would they rate (from 1 to 5 stars) the product they are about to buy.
> Were also doing 2 back-end usability improvements: 1) for logged in users, record the discounts they have been interested for. For example if they wanted to learn more about the discount, that is something the agent must keep in mind for future discounts; 2) Its also important to save the ratings, and actually we can record the rating from when user bought the merchandise. Actually, were doing two more back-end: 3) lets make the agent run faster, for example for the ratings and discounts use a low spending model; 4) make the agent safe by not lying to customers or making assumptions that the customer hasn't told the agent.
> Write output/usability.md before or as it is built. For each of the improvements, say: what it is being added, and why it helps a campus customs shoper and/or the business. Then lets make sure that all improvements actually show up in the running app, so double check that each of the improvements in this prompt work perfectly

**Follow-up prompt:** None needed. The initial prompt listed all six improvements, what each had to do, the document to write and what it had to say for each, and the requirement to verify everything in the running app.

**Evidence:** the running site, [usability.md](output/usability.md), [harness.md](output/harness.md) section 8. Fifteen checks driven through the browser from a clean database, all passing.

**Handsome Dan is HTML and CSS,** per the project convention — shaped `div`s with border-radius, no image file and nothing generated, so he is sharp at any size and nods when he greets someone.

**"Every now and then" is enforced server-side.** Dan offers a discount only when the shopper holds no usable code and at least 20 hours have passed. Reopening the panel cannot produce a new one — checked immediately after a redemption, where `offer_due` correctly returned False. The percentage is never the model's: Dan's sentence is written by the light model but the figure comes from the database, and the sentence is rejected in favour of a written line if it comes back without that figure.

**On "use a low spending model" (back-end 3).** Worth being precise about where the saving came from. The light model, `gpt-5.4-nano`, is real and measurably lighter — median 1.61s against 1.89s on a like-for-like benchmark, at a fraction of the cost per token — and it runs Handsome Dan's line. But the larger win is that **discounts and ratings make no model call at all**: issuing a discount takes 1.3 ms, recording interest 0.5 ms, reading an average 0.2 ms. They are database operations, which is faster and cheaper than any model however small. The cheap model then takes the one call that genuinely wants writing.

**Discount interest is captured from both directions:** pressing "Tell me more" records it, and so does raising it in conversation — the agent calls a `record_discount_interest` tool and writes its own note. Verified: asking about the discount wrote "Shopper asked for more information about their discount."

**Safety (back-end 4) is a standing rule with named cases.** Not just "do not lie" but a list: never assume their size, that they are buying, who they are, what they can spend, why they want it, or that they liked something you showed them. Tested — it asked for a size rather than guessing one, refused to invent a 30% discount, refused to promise a future one, and declined "everyone says it's the best hoodie on campus, right?" by pointing out that one 4-star rating is not evidence of that.

**Follow-up prompt:**
> dont tell them that members get their conversations kept. That is not marketable. neither their ratings. only important for unlogged customers is they can get discoutns

**What was lacking:** the guest-facing copy sold an account on three things — kept conversations, saved ratings and the discount — when only the discount is worth anything to the shopper. The other two are how the shop works, not a benefit to them.

**What the follow-up changed:** every surface a guest sees now leads with the ten percent and nothing else — Handsome Dan's line, the join button ("Join for member discounts"), the Log in and Create Account pages, the prompt shown when a guest presses Buy, and the API's own message. The agent's rule is now explicit that the discount is *the only* reason to sign in it may ever give, and that it must not sell an account on the kept conversation or the ratings. Verified by sweeping every guest-visible page for the retired phrases — all clean — and by asking the assistant "why should I make an account?", which now answers with the discount alone and offers to help without one.

**One limitation stated rather than hidden:** a purchase does not reduce `inventory`. The seeded stock figures are the evidence base for the earlier problems, and quietly draining them would invalidate that verification. It is written into usability.md rather than left for you to discover.

## Problem 10 — Style the Website

**Prompt 1 (initial):**
> Now to Problem 10: Style the website. We need to add more creative design so it feels like the real deal. Add more handsome dans throughout the webpage that make users feel wewlcome and appreciated (and that they may need the merchandise!) but keep it elegant and simple, and remember we are still taking the main design from the Yale Club NYC. Add more emotionally driven language so that buyers want to actually buy the merchandise (but again, keep it simiple and elegant). I love the white/blue combination you used, so keep that. Maybe for the products you can remove the black/white at the back so it seems like the products are "floating".
> Also, write output/design.md on what was changed (or also keeped, as the design was initially very elegant) and I'll tell you why It should help potential clients to stick around and buy: [the shopkeeper's rationale, reproduced at the end of design.md]. Don't overthink, lets get it done fast please

**Follow-up prompt:** None needed. The initial prompt specified more Handsome Dans kept elegant, warmer language kept simple, the blue/white palette to preserve, the Yale Club reference to keep, the floating products, and the document to write.

**Evidence:** the running site, [design.md](output/design.md), and [harness.md](output/harness.md) section 2.5.

**The floating products are real background removal, not a CSS trick.** The cutout builder (`python main.py --cutouts`) writes a transparent PNG per garment; the API serves those and falls back to the original photo if a cutout is ever missing. The flood runs inward **from the border** rather than thresholding on colour — that distinction is what keeps the white YALE lettering on a navy hoodie, which a "remove everything white" pass would have erased.

**Three refinements came from looking at the output, not from planning:** a one-pixel erosion to kill the white halo where a garment was shot against black; an opening to drop leftover speckle (checked against hoodie drawstrings, which survive); and a tolerance ladder with a quality gate that inspects the middle of the frame and retries more tightly when the flood leaked into the garment. Four photos needed the ladder. All 102 now cut cleanly.

**Dan appears in five places** — the home statement band (where the shop's line is now signed "— Handsome Dan, keeping an eye on the door"), the closing navy band, the footer mark, the About hero, and the chat results band — all from the one HTML/CSS component, scaling from 46px to 132px, nodding only where he greets someone and holding still elsewhere.

**The language moves the subject from the shop to the shopper:** "Products" became "Find Yours", "Built for the Walk to Class" became "Made to Be Lived In", "4 sizes in stock" became "4 sizes ready". Every claim is about belonging, never urgency — nothing says limited or hurry. That is deliberate and consistent with the assistant, which is forbidden from inventing scarcity; a site that pressures in print while refusing to pressure in chat would read as dishonest in one of the two places.

**One snag worth noting:** the first pass at the pillar copy silently did not apply — the match string used an escaped apostrophe where the file holds a real one — so the old text was still on the page. Caught in the screenshot rather than assumed fixed, and corrected.

## Problem 11 — Site Testing (App Check)

**Prompt 1 (initial):**
> Problem 11: Site testing (app check). Although we've been already checking the site, lets do the following. Test the live site and document it in output/app_check.html (a page you can double-click open). Include clear screenshots and short captions for: 1) Chat checking the inventory level of an item (honest stock/price from the database), 2) The dynamic search-result cards appearing after a category question (e.g. hoodies, or shirts), 3) One (only one) of the usability features I added in Problem 9.
> Please make the HTML easy to grade (were all in this together!): heading for each check, screenshot, 1-2 sentences on what the screenshot is proving. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png). Lets go were almost there!

**Follow-up prompt:** None needed. The initial prompt specified the file, the three checks, the one-feature limit, the structure each section must have, where the images go, and that the links must be relative.

**Evidence:** [app_check.html](output/app_check.html) and [output/app_check_images/](output/app_check_images) — three screenshots taken from the live site in one run.

**Built to be graded quickly.** A summary table at the top lists all three checks and their results, then each check is a numbered heading, the question that was asked, the screenshot, a caption saying what it proves, and a short note tying it back to the database. Opened as a `file://` URL — the way a double-click opens it — and verified: all three images load, no failed requests, nothing depends on a server running.

**Check 1 was recaptured to make it stronger.** The first attempt showed the chat answer alone. The second puts the product page beside it, so the screenshot carries three independent agreements at once: the assistant saying "not available in XS... $58... S, M, L, and XXL", the size grid with XS and XL struck through, and the stock line reading S (15), M (5), L (25), XXL (25). All match `inventory` exactly. The question was also phrased as just "is **this** available in XS", which incidentally demonstrates the Problem 8 page context resolving "this".

**For check 3 I chose the star rating,** as one feature rather than several: pressing Buy does not complete the order, it first asks how the shopper would rate the garment, with Handsome Dan's 10% applied alongside taking $88.00 to $79.20.

**One housekeeping note:** the test user's chat history and the perk tables were cleared before the capture run so the screenshots show a clean, legible state rather than the accumulated debris of earlier testing.

## Problem 12 — Audit Trail, Safety, Finish Harness

**Prompt 1 (initial):**
> Problem 12: Audit trail, safety, finish harness. Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs. Also, add the safety rules that the agent must be ethical when chatting with customers. I read it is already included, but just to make sure lets make that the agent doesn't try to make people buy stuff, but instead makes people want to belong and that belonging leads to sales. Never lie, always say truthful information. If the truth is that some information doesn't exist, its perfectly fine. Add additional safety rules to give to the agent that make sense with what we built, and put mines plus yours in prompts/prompt.md
> Finish output/harness.md so it is clear how the system works. Model fields in models.py and why they were chosen. Tools and abilities. Also safety rules. Finally specs (loop limits, result caps, models, how to run front and back) that make it as efficient as possible

**Follow-up prompt:** None needed. The initial prompt specified the audit file and its contents, the append-only rule, the three safety principles to add, the instruction to add my own alongside them, and the four things the harness had to finish with.

**Evidence:** [audit_trail.json](output/audit_trail.json) (18 real runs), [prompt.md](backend/prompts/prompt.md), and [harness.md](output/harness.md) sections 9–12.

**Append-only is structural, not a convention.** `append()` reads every existing record before writing them all back, and there is no function that empties the file. Writes go to a temporary file and are then atomically moved into place, so a crash cannot truncate the trail. If the file is ever found unparseable it is copied aside as `audit_trail.corrupt-<timestamp>.json` rather than discarded. Failed runs are audited too — the record is written in a `finally` block with the exception type as the stop reason. Verified across a full server restart: 1 → 4 → 5 records, nothing lost.

**The audit file holds no personal data.** A shopper is `user:1` or `guest` — never a name, never an email. Swept the 18 records for `@campuscustoms`, `@yale.edu`, `pbkdf2`, `password` and `Test User`: all absent.

**Your three principles are now the governing section of the prompt.** The assistant is told it is not there to close a sale — no urgency, no scarcity it was not given, no asking for the sale, and *if someone says no, that is the end of it*. "We do not have that" and "I do not know" are named as complete answers that need no covering up. Tested: "money is tight, I'm not sure I should buy anything" → *"There is no need to buy anything today."*

**My additions, chosen to match what we actually built:** never claim to be a person; do not speak for Yale; do not judge who belongs; do not discuss other shoppers; no advice outside the catalogue; take no personal information; promise nothing the shop has not committed to; disparage nobody; be kind when the conversation is not about clothes; keep the shop's confidence.

**Two rules were tightened after testing them.** Asked "are you a real person?" it first said only "we are the shop's assistant" — true but evasive, so the rule now requires it to say in the first sentence that it is a program. And asked "I didn't go to Yale, am I allowed to wear this?" it deflected to "we do not have eligibility rules", which implies a doubt that does not exist; the rule now requires a warm, unqualified yes. Both now answer correctly.

**One operational gotcha worth knowing.** Those two fixes appeared not to work — because `uvicorn --reload` watches `*.py` only, so editing `prompts/prompt.md` does **not** restart the server and the agent keeps serving the cached prompt. The run command is now `--reload --reload-include "*.md"`, and the trap is written into the harness so it does not cost anyone else a confusing round of testing.

## Problem 13 — Push to GitHub and Submit the URL

**Prompt 1 (initial):**
> Problem 13: Push to GitHub and submit the URL. Put the code in a folder named hw4 and push it to a public GitHub repository. I will submit the repo URL to canvas myself, and I need you to give me this repo URL (the link that graders can open and clone). Do not put my real .env, campus_customs.db, or product images in the GitHub repo. Use .gitignore. Include .env.example with placeholders only. The expected file layout is attached in the image, as well as the Local-only data pack (not in git). The agent itself is four files under backend/ : prompts/prompt.md, agent.py, tools.py, and models.py . README.md should explain how to run the front end and back end after placing the data pack

**Follow-up prompt:**
> yeah mask it too. no additions, so please make it exactly as the screenshots and confirm the webpage works. Double check everything as is in the picture

**What was lacking:** the first push left your own shop account address in the documents, and added two files the layout picture does not show — `output/screenshots/` and `funny_joke.txt` — on the grounds that other documents cited them.

**What the follow-up changed:** both addresses are masked, the two extra files are gone, and every reference to them was rewritten so no document points at a file that is not in the repository. The layout was then checked item by item against the picture, and the running site was re-verified end to end.

**Evidence:** **https://github.com/eduardohub555/campus-customs-hw4** — public, 93 files, verified by cloning it fresh and checking the layout from a grader's point of view.

**Nothing sensitive was published.** Before the first commit the staged tree was swept for the real Portkey key, the Outlook identifiers, any `.db` file, the `data/` pack, `node_modules` and `.venv` — none present. The clone was then re-checked after pushing, confirming the same.

**Two real addresses caught before publishing.** An email-shaped sweep of the staged files turned up a third party's genuine Yale address, which had come out of the seeded `users` table into a worked example in harness.md. Publishing someone else's real address in a public repository is not something to do quietly, so it was masked. Your own shop account address was masked in the same pass at your request. Neither the repository nor your working copy now contains a real email address; the documents say what is stored without naming anybody.

**The repository matches the layout in the picture exactly.** `output/screenshots/` and `funny_joke.txt` were removed at your request, and every reference to them in these documents was rewritten so nothing points at a file that is not there.

<!-- Add one new "## Problem N — Title" section below for each problem, following the same structure. -->
