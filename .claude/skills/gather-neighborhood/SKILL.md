---
name: gather-neighborhood
description: Gather Nosh pilot data (restaurant list, menus, opening hours) for one neighborhood listed in data/pilot/neighborhoods.yaml. Use as /gather-neighborhood <slug>.
---

# Gather one neighborhood

Neighborhood slug: **$ARGUMENTS**

Gather pilot data for that one neighborhood. Data files only: no application
code, no migrations, no commits, no staging.

## Setup

1. Read `data/pilot/neighborhoods.yaml` and find the entry whose `slug` is
   `$ARGUMENTS`. If there is no such entry, or no slug was given, stop and
   list the available slugs.
2. Read `data/pilot/san-mateo-downtown/restaurants.csv`, `hours.csv`, one
   captured file and one failed file in its `menus/` folder, and both reports.
   **Match those file formats and field names exactly**, so every
   neighborhood can be processed together.
3. Work in `data/pilot/<slug>/`. If files already exist there, this is a
   resume or a top-up: keep everything already captured, do not re-fetch
   restaurants that already have a menu file, and only add what is missing.
4. Set this entry's `status` to `in_progress` in `neighborhoods.yaml`.

## Step 1: select restaurants

Aim for `target` restaurants plus `reserves` reserves.

- **Look in `core` first.** Use `may_extend_to` only as far as needed to
  reach the target. Say in a restaurant's `notes` when it is in the extended
  area. Never go outside both.
- Sit-down or counter service, open for lunch or dinner.
- As many countries of cuisine as the area supports, at most 4 per country.
  If the target cannot be met at 4, raise the cap to 6 and say so in the
  report.
- Mostly independents; at most 5 chain branches. A **chain** is any brand
  with 3 or more locations anywhere (count them on its own site). Set
  `is_chain` the same way for the same brand in every area.
- **Country labels:** Hong Kong and Taiwan are their own labels, separate
  from China. Hawaiian is its own label, separate from United States. Label
  a restaurant by what its menu actually serves, never to fit under a cap.
- **Price level: mostly $ and $$.** Judge a place by the typical price of a
  main dish on its own menu: $ is under $18, $$ is $18–32, $$$ is $32–55,
  $$$$ is over $55. Aim for at least 85% of selected restaurants at $ or $$;
  allow at most 5 at $$$ and none at $$$$. If you can't tell before capture,
  check again after capture and swap a reserve in for anything over the
  limit. Write the tier in `notes` (for example "price tier $$ (typical main
  about $24)", a generated estimate), and give the tier mix in the report.
- Strongly prefer places whose own website has a readable menu.
- Skip bars, dessert-only shops, coffee shops, and ghost kitchens.
- Confirm each restaurant on its own site or an official listing (business
  association, city listing, local press). Do not copy ratings, review
  counts, review text, or details from Google Maps, Yelp, or delivery apps.
  If you cannot confirm a place is open at that address, leave it out and
  note it.
- For a restaurant with several branches, record only the branch inside the
  area, with its own address.

Write `restaurants.csv` and `restaurants_report.md`. The report states the
area's time zone (from the yaml). `primary_country` is your own generated
label, for the owner to review.

## Step 2: capture menus and hours

One subagent per selected restaurant, 5 at a time, using **the restaurant's
own website only**. The restaurant's own first-party ordering page (for
example Toast, Square, Clover, Chowbus, ChowNow or NCR Aloha) also counts,
but only when the restaurant's own site links to it; record that link in the
menu file. The crawler rules below still apply to the ordering host.
Marketplaces (DoorDash, Uber Eats, Grubhub) never count.

When a restaurant has no site of its own, two things also count as its own
site: a site its ordering platform built and hosts for it (for example a
Chowbus-made Wix page), and its official page on a food hall operator's site
(for example San Pedro Square Market). Say which in `notes`.

A third-party menu widget (for example SinglePlatform) counts as the
restaurant's own menu only when the restaurant's own site embeds it. The
crawler rules apply to every host the widget uses.

- **Menu:** every food item exactly as written: section, name, description,
  price, which menu (lunch, dinner, all-day, takeout), source URL, retrieval
  date. Skip drinks. Read web pages, PDFs, and images. If the site has
  separate menus per branch, use this branch's menu; never use another
  branch's menu for this one.
  - **One price for a whole section** (for example "SIDES | 18"): leave each
    line's `price` empty and record the section price in that line's
    `options`. Never copy it onto each line.
  - **Ordering-platform data** (Sauce, Toast, Clover, and similar, including
    data read from the page's embedded JSON) is kept, recorded as menu
    `takeout`, with a note that ordering prices may differ from dine-in.
- **Opening hours** for this branch exactly as posted, in local time,
  including split lunch and dinner service. If two versions conflict, record
  both and flag it; do not pick one. If none are posted, write one row
  saying so.
  - A closed day is written with `open` set to `closed`, never left empty.
  - Hours in the restaurant's own site's schema.org data count. Say so in
    `note`. If they disagree with the visible hours, record both as a
    conflict.
- **Crawler rules:** check `robots.txt` for every host first and obey it,
  including rules aimed at AI crawlers such as ClaudeBot. Never bypass a bot
  check. Never use archived copies or third-party sites (DoorDash, Uber
  Eats, Grubhub, Yelp, Google). Read the `robots.txt` response like this:
  - a real robots file: obey its rules;
  - HTTP 404 (with a plain or HTML "not found" body): no rules, so allowed;
  - HTTP 200 whose body is an HTML page or app shell instead of a robots
    file, or a redirect to an HTML page: **blocked**;
  - 401, 403, other errors, timeouts, or a bot challenge: **blocked**.
  Also request `robots.txt` with a ClaudeBot user agent. If the site refuses
  ClaudeBot (for example "Access Denied") while serving other agents, the
  host is **blocked**.
  Record the status code and what the body was in `robots_checks`.
  Do not render a page in a browser if it pulls scripts or data from a
  blocked host. If a render touches a blocked host anyway, record it as a
  process slip in `notes`; items read from allowed hosts stay, and nothing
  from the blocked host is used.
- **Captured or partial:** a menu is `captured` when everything on the
  restaurant's own site was read, even if a linked ordering page was blocked
  (say so in `notes`). It is `partial` when part of the own site's menu
  could not be read, or when no item has a price.
- **On failure,** record the reason and what a person would need to do.
- **Never invent, complete, translate away, or correct anything.** An
  unreadable line is recorded as unreadable.

Write `menus/<restaurant-slug>.json` and `hours.csv`.

## Step 3: replace failures

When a restaurant yields no menu, set its status to
`failed_needs_manual_capture` (do not delete it), promote the next reserve
whose country is not at its cap, and capture it. Continue until `target`
restaurants have menus or the reserves run out. If reserves run out below
the target, look for more candidates in `may_extend_to` once, then stop.

## Stop rules

Stop and report, instead of continuing, if:

- fewer than 60% of the first 10 restaurants yield a menu; or
- you cannot confirm at least 20 qualifying restaurants in the core and
  extended area together.

## Finish

1. Write `menus_report.md`: restaurants covered, items captured, failures by
   reason, hours coverage and conflicts, the country mix, the price-tier
   mix ($ / $$ / $$$ / $$$$, against the 85% $–$$ aim), how many
   restaurants came from the extended area, and 4 restaurants picked at
   random for the owner to spot-check.
2. Run `python3 data/pilot/check.py <slug>` and fix any format problem it
   reports in your own files.
3. Set this entry's `status` in `neighborhoods.yaml` to `done`, or leave it
   `in_progress` if a stop rule fired, and say which.

Everything is marked generated and unreviewed. Do not group, classify, or
map dishes. Do not commit.
