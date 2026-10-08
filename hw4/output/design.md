# Campus Customs — Design

What changed in the styling pass, what was deliberately left alone, and why each choice should help a shopper stay and buy.

## What was kept

The original design was already doing its job, so this pass added rather than replaced.

- **Navy and white.** `#00356b` and white, with a single gold accent for rules and eyebrows. Untouched.
- **The Yale Club of New York structure.** Serif headings over a sans-serif interface, a crest in the navigation, the rotating hero with an overlay line, three cards, thin gold rules, and a great deal of white space. All of it stayed.
- **The navigation, footer and page skeleton.** Unchanged.
- **Every product card still opens the same single-item page.** Nothing about the click path moved.

## 1. The products now float

### What changed

The catalogue photographs were shot on flat black or flat white studio backdrops. Those backdrops have been removed: `backend/cutouts.py` writes a transparent PNG for each of the 102 garments, and the API serves those in place of the originals.

The card then stopped being a box. The bordered grey tile is gone, replaced by a soft radial field of light — white at the centre, easing to pale blue at the edges — with the garment sitting on top in `object-fit: contain` and carrying its own `drop-shadow`. On hover it lifts six pixels and the shadow deepens.

**How the background is removed.** The flood runs **inward from the border**, not as a colour threshold. That distinction matters: "remove everything white" would erase the white YALE lettering across a navy hoodie. Flooding from the edge only removes background actually connected to the edge, so lettering enclosed by the garment survives.

Three refinements were needed, each from looking at the result:

1. **A one-pixel erosion**, because a garment shot against black has a faint light rim that reads as a white halo once the black behind it is gone.
2. **An opening — erode then dilate —** to drop small islands of leftover backdrop without shrinking the garment. Checked against hoodie drawstrings, which survive.
3. **A tolerance ladder (42 → 30 → 20 → 12) with a quality gate.** Some photos have a glow bleeding off the garment that a loose flood follows inward, eating part of the garment. The gate looks at the middle of the frame — where the garment is, not the backdrop — and rejects the attempt if much of it went transparent, trying again more tightly. Four photos needed this; all 102 now cut cleanly.

### Why it should help

A shopper is not buying a photograph, they are buying a jumper. A black rectangle around a navy hoodie makes it read as a picture of a product in a catalogue. Lift it off and the garment itself is what is on the page — the shape, the weight, the way the fleece hangs. The soft shadow does the rest: it puts the garment in the room with the shopper rather than behind glass.

It also makes the grid cohere. Before, a white-backed tee sat beside a black-backed hoodie and the eye saw the rectangles, not the clothes. Now the eye travels across garments, which is what the page is for.

## 2. Handsome Dan around the shop

### What changed

Dan was already in the chat panel. He now appears in four places, each a nod rather than a performance:

| Where | What he does |
| --- | --- |
| The statement band on the home page | Sits above the shop's line, which is signed *"— Handsome Dan, keeping an eye on the door"* |
| The closing navy band | Invites the shopper to come by the store |
| The footer | Beside the crest, in the brand mark |
| The About page hero | Watching from the right of the heading |
| The chat results band | Beside the heading when he has found something |

He is **drawn in HTML and CSS** — shaped `div`s with border-radius, no image file and nothing generated — so he is sharp at any size, costs nothing to download, and scales from a 46px footer mark to a 132px greeting from one component. He nods gently where he greets someone, and holds still where he is just present. The nod is disabled under `prefers-reduced-motion`.

### Why it should help

A merchandise site is a grid of rectangles, and a grid of rectangles is a catalogue, not a shop. Dan is the one thing on the page that is pleased you came. He is also the single most affectionate piece of iconography Yale has — putting him beside the clothes makes wearing them feel like belonging rather than buying.

The restraint matters as much as the presence. He is small, he is drawn in the shop's own two colours, and he never speaks over the garments. The Yale Club does the same thing with its crest: present throughout, never loud.

## 3. Language that asks for the sale

### What changed

The copy was accurate but reserved. It now says what a garment is *for* rather than only what it is.

| Was | Now |
| --- | --- |
| "Browse the shop" | **"Find yours"** |
| "Products" | **"Find Yours"** |
| "The Shop on the Corner" | **"Why People Keep Coming Back"** |
| "Find Your Layer" | **"What Are You Reaching For?"** |
| "Picked Off the Rack" | **"Handsome Dan's Picks"** |
| "See all products" | **"See everything we have"** |
| "Licensed, Not Lookalike" | **"The Real Blue"** — *"nobody has to wonder whether it is the real thing — and neither do you"* |
| "Fourteen Colleges, One Shop" | **"Your Corner of Campus"** — *"whatever you belong to here, there is something with your name on it"* |
| "Built for the Walk to Class" | **"Made to Be Lived In"** — *"the one you reach for first, for years"* |
| "Not souvenirs — a wardrobe" | "Not souvenirs — **the jumper you live in**" |
| "4 sizes in stock" | **"4 sizes ready"** |
| "Unavailable" | **"Gone for now"** |

The hero gained one sentence: *"You worked for this one."*

### Why it should help

Every rewrite moves the subject from the shop to the shopper. "Products" is a noun the business uses; "Find Yours" is what the shopper came to do. "Built for the Walk to Class" describes construction; "Made to Be Lived In" describes a life with the garment in it.

The emotional claim is always about **belonging**, never urgency. Nothing says limited, hurry, or exclusive. That is deliberate: this shop's appeal is that you have earned the right to wear the thing, and manufactured scarcity would cheapen it. It also keeps the marketing copy consistent with the assistant, which is forbidden from inventing scarcity — a site that pressures in print and refuses to pressure in chat reads as dishonest in one of the two places.

---

## Why this should keep potential clients around, in the shopkeeper's words

The new design feels more interactive with Handsome Dan in there, while keeping the elegance of the Yale Club of New York — the serif headings, the navy and white, the gold rules and the open space are all still doing the work. The products no longer have a background, which helps customers see how nice they actually are, instead of looking at what reads as a bad picture. And the language is written so that customers want to buy: it speaks to belonging at Yale rather than to a transaction.
