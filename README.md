# The Ship Log

A daily-refreshing page of major-company product launches, pulled from
their own newsroom RSS feeds. Free to host — no server, no API keys.

## How it refreshes
`.github/workflows/refresh.yml` runs `scripts/fetch_launches.py` once a day
(13:00 UTC by default — edit the `cron:` line to change it), which:
1. Pulls each company's RSS feed listed in `scripts/fetch_launches.py`
2. Keeps only posts from the last 3 days that sound like a launch
3. Writes the result to `data/launches.json`
4. Commits that file and redeploys the site automatically

The page (`index.html`) just fetches `data/launches.json` on load — nothing
to run in the browser.

## One-time setup (about 5 minutes)

1. **Create a GitHub repo** and upload everything in this folder
   (`index.html`, the `data/`, `scripts/`, and `.github/` folders) to it.
2. In the repo, go to **Settings → Pages** and set **Source** to
   **GitHub Actions**.
3. Go to the **Actions** tab, click into "Refresh launches and deploy,"
   and click **Run workflow** once to trigger the first run manually.
4. After it finishes (~30 seconds), your site is live at
   `https://<your-username>.github.io/<repo-name>/`

From here it refreshes on its own every day. You can also click **Run
workflow** any time you want an immediate update instead of waiting.

## Customizing which companies it tracks
Edit the `FEEDS` dictionary at the top of `scripts/fetch_launches.py` —
it's just a company name mapped to their public RSS feed URL. Add or
remove companies freely. Most large companies have a newsroom feed;
search "`<company name> newsroom rss`" to find it.

A few beauty/skincare/car/designer-brand feeds are included but
commented out, since I couldn't verify them from the sandboxed
environment that generated this script (no live internet access there).
Before uncommenting one, paste its URL into a browser — if you see
readable XML with `<item>` or `<entry>` tags, it works. If you get a 404
or an HTML page instead, search for that brand's actual newsroom feed
and swap the URL in.

## Categories
Each launch is auto-tagged by matching keywords in its title/summary
against the rules in `CATEGORY_RULES` (top of `scripts/fetch_launches.py`).
Currently covers: Mobile Hardware, Audio, Wearables, AI / Models,
Developer Tools, Beauty, Skincare, Video Games, Cars, Designer Brands,
Consumer Hardware, Gaming, Home & Appliances, Consumer Software, and
Other as a catch-all. Add more by adding a `("Label", r"regex pattern")`
tuple — order matters, since the first matching rule wins.

Note: a category only shows real results if a feed in `FEEDS` actually
covers that industry. Beauty/Cars/Designer Brands will filter to nothing
until you add working feeds for brands in those spaces.

## Note on scope
There's no single public database of "every major company's product
launches." This works by watching each company's own announcements, so
coverage is only as good as the feed list — it won't catch launches from
companies not in `FEEDS`, and very quiet/small launches without a press
post may not fire the keyword filter. Both are easy to adjust in the
script.
