import Typesense from 'typesense';

// Search-only key -- safe to ship to the browser since it can only read,
// never write or delete, unlike the admin key used in index_birds.py
const client = new Typesense.Client({
  nodes: [{
    host: window.location.hostname,
    port: Number(window.location.port) || (window.location.protocol === 'https:' ? 443 : 80),
    protocol: window.location.protocol.slice(0, -1),
    path: '/typesense',
  }],
  apiKey: 'xyz', // matches TYPESENSE_SEARCH_ONLY_API_KEY in .env
  connectionTimeoutSeconds: 2,
});

const PER_PAGE = 24;

// Searches commonName/species/description, typo-tolerant by default.
// Returns a flat array of bird objects shaped like what /api/birds
// returns, so BirdCard doesn't need to know which source it came from.
export async function searchBirds(query, page = 1) {
    try {
        const results = await client.collections('birds').documents().search({
            q: query,
            query_by: 'commonName,species,description',
            infix: 'fallback,fallback,off',

            per_page: PER_PAGE,
            page: page
        });

        const birds = results.hits.map((hit) => hit.document);

        // found = total matching documents across ALL pages, not just this
        // one -- comparing it against how far this page reaches tells us
        // whether a next page exists
        const hasMore = page * PER_PAGE < results.found;

        return {birds, hasMore}
    } catch (error) {
        console.error("Typesense search failed:", error);
        return { birds: [], hasMore: false };
    }
}