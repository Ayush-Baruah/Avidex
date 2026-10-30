import { useState, useEffect, useRef } from 'react'
import BirdCard from '../components/BirdCard';
import { searchBirds } from '../typesense';

const PAGE_SIZE = 24;


export default function Compendium() {
    // Holds the array of bird objects currently shown, whichever source
    // they came from (paginated browse, or a Typesense search)
    const [birds, setBirds] = useState([])
    const [page, setPage] = useState(1)
    const [hasMore, setHasMore] = useState(false)
    const [searchQuery, setSearchQuery] = useState("")
    const [placeholderName, setPlaceholderName] = useState("cardinal");

    // Scrolls the window back to the top -- called after any pagination
    // action, so clicking Next/Previous doesn't leave the user staring at
    // whatever scroll position they were at on the old page
    function scrollToTop() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // Runs whenever `birds` changes -- picks a new random name once the
    // first page of birds has actually loaded. Only fires once meaningfully,
    // since after the first load `birds.length` stays truthy and this
    // effect's dependency doesn't force a re-pick on every render.
    useEffect(() => {
        if (birds.length > 0) {
            const randomBird = birds[Math.floor(Math.random() * birds.length)];
            setPlaceholderName(randomBird.commonName);
        }
    }, [birds])

    async function loadPage(pageNumber) {
        const offset = (pageNumber - 1) * PAGE_SIZE;
        const response = await fetch(`/api/birds?limit=${PAGE_SIZE}&offset=${offset}`);
        const data = await response.json();

        setBirds(data.birds);
        setPage(pageNumber);
        setHasMore(data.hasMore)
    }

    // Runs the search for whichever page is currently selected. Called both
    // when the search text changes (reset to page 1) and when Next/Previous
    // is clicked while a search is active.
    async function runSearch(searchText, pageNumber) {
        const { birds: results, hasMore: more } = await searchBirds(searchText, pageNumber);
        setBirds(results);
        setPage(pageNumber);
        setHasMore(more);
    }

    // Runs once on mount to load the first page -- only when there's no
    // active search, since a search replaces this view entirely
    useEffect(() => {
        if (searchQuery.trim() === "") {
            loadPage(1);
        }
    }, [])

    // Debounced search: waits 300ms after the user stops typing before
    // actually querying Typesense, so a fast typist doesn't fire a
    // request on every single keystroke. The cleanup function (the
    // "return () => ...") cancels the pending timeout if searchQuery
    // changes again before it fires.
    useEffect(() => {
        if (searchQuery.trim() === "") {
            return;
        }

        const timeoutId = setTimeout(() => {
        runSearch(searchQuery, 1);
        }, 300);

        return () => clearTimeout(timeoutId);
    }, [searchQuery])

    // Clearing the search box goes back to the paginated browse view,
    // starting fresh from the first page
    function handleSearchChange(event) {
        const value = event.target.value;
        setSearchQuery(value);

        if (value.trim() === "") {
            setBirds([]);
            loadPage(1);
        }
    }

    return (
        <>
        <div className='search-bar-div'>
            <h3 className='search-bar-title'> Search for a Bird </h3>
            <hr className='search-bar-hb'/>
            <input
                type='text'
                className='search-bar'
                value={searchQuery}
                onChange={handleSearchChange}
                placeholder={`${placeholderName}`}
            />
        </div>
        <div className='card-box'>
            {birds.map((bird) => (
                <BirdCard 
                    key={bird.birdID}
                    commonName={bird.commonName}
                    species={bird.species}
                    description={bird.description}
                    photos={bird.photos}
                />
            ))}
        </div>

        {/* Only offer "Load more" during the default browse -- searches
            return their own complete result set from Typesense */}
            <div className='pagination-controls'>
                <button
                    className='pagination-button-left'
                    onClick={() => {
                        searchQuery.trim() === "" ? loadPage(page - 1) : runSearch(searchQuery, page - 1);
                        scrollToTop();
                    }}
                    disabled={page === 1}
                >
                    Previous
                </button>

                <span className='pagination-current'>Page {page}</span>

                <button
                    className='pagination-button-right'
                    onClick={() => {
                        searchQuery.trim() === "" ? loadPage(page + 1) : runSearch(searchQuery, page + 1);
                        scrollToTop();
                    }}
                    disabled={!hasMore}
                >
                    Next
                </button>
            </div>
        </>
    );
}