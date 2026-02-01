# Watchlist Checker - Retro

## What it does

You know how Letterboxd lets you build a watchlist but doesn't tell you where to actually watch anything? This fixes that. Pop in your Letterboxd username, pick your streaming services (Netflix, Max, Hulu, Prime, whatever), and it shows you which films from your watchlist are available right now — with posters and direct links to start watching.

## How it works

- Scrapes your public Letterboxd watchlist
- Hits the JustWatch GraphQL API to check streaming availability
- Runs as a Netlify serverless function so your friends can use it too (no code required)
- Frontend styled to feel like Letterboxd (dark theme, green accents)

## Tech used

- JavaScript (Node.js serverless function)
- HTML/CSS for the frontend
- JustWatch API for streaming data
- Netlify for hosting
- Anthropic's frontend-design skill for UI styling principles
- macOS app bundle + AppleScript for the desktop icon

## Things that broke along the way

- **Letterboxd scraping:** HTML structure was different than expected — had to hunt down the right selectors (`div[data-component-class='LazyPoster']` instead of `li.poster-container`)
- **Title matching:** JustWatch returns "Parasite" but Letterboxd stores "Parasite (2019)" — had to strip the year with regex for matching
- **Fish shell:** Doesn't support heredocs (`<< 'EOF'`), which tripped up like 4 different commands throughout the build
- **Two machines:** Built everything on bat-king, then had to figure out how to get it onto goblin — SSH auth between them was a mess
- **macOS icon caching:** Even after setting the custom icon it wouldn't show until we forced it with AppleScript/NSWorkspace API
- **Icon metadata:** Custom icons don't transfer over scp (stored as extended attributes), so had to re-apply the icon on goblin separately

## Live

https://watchlist-copy.netlify.app
