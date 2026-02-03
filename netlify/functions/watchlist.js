// Fetches Letterboxd watchlist pages
export default async (request) => {
  const url = new URL(request.url);
  const username = url.searchParams.get('username');
  const page = url.searchParams.get('page') || '1';

  if (!username) {
    return new Response(JSON.stringify({ error: 'Username required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  try {
    const letterboxdUrl = `https://letterboxd.com/${username}/watchlist/page/${page}/`;

    const res = await fetch(letterboxdUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
      }
    });

    if (!res.ok) {
      return new Response(JSON.stringify({ error: 'Failed to fetch watchlist' }), {
        status: res.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const html = await res.text();

    return new Response(html, {
      headers: {
        'Content-Type': 'text/html',
        'Cache-Control': 'public, max-age=300' // Cache for 5 minutes
      }
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};

export const config = {
  path: "/api/watchlist"
};
