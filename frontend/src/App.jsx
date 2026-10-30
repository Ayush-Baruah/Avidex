import { useState, useEffect } from 'react'
import { Routes, Route, Link, useNavigate, NavLink } from 'react-router-dom'
import Identify from './pages/Identify.jsx'
import Home from './pages/Home.jsx'
import Compendium from './pages/Compendium.jsx'
import './App.css'



function App() {
  const [signedIn, setSignedIn] = useState(false)

  // Reads any previously saved preference on first load, defaulting to
  // "light" if this is the user's first visit. Passing a function to
  // useState means localStorage is only read once, not on every render.
  const [theme, setTheme] = useState(
    () => localStorage.getItem('theme') || 'light'
  )

  // Runs whenever `theme` changes: writes it onto <html> so the CSS
  // variables above pick it up, and saves it so the choice survives a
  // page refresh
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  function toggleTheme() {
    setTheme((current) => (current === 'light' ? 'dark' : 'light'))
  }
  
  const navigate = useNavigate()

  function handleNavClick(path) {
    console.log(`${path} was clicked on`)
    navigate(path);
  }

  return (
    <>
      <div className='top-bar'>
        <Link className="title" to="/">Avidex</Link>
        <nav className='nav-bar'>
          <NavLink className={({ isActive }) => isActive ? "nav-bar-item current-page" : "nav-bar-item"} to="/Identify">Identify</NavLink>
          <NavLink className={({ isActive }) => isActive ? "nav-bar-item current-page" : "nav-bar-item"} to="/Compendium">Compendium</NavLink>
          <NavLink className={({ isActive }) => isActive ? "nav-bar-item current-page" : "nav-bar-item nav-bar-item-dsiabled" } >Map</NavLink>
          <NavLink className={({ isActive }) => isActive ? "nav-bar-item current-page" : "nav-bar-item nav-bar-item-dsiabled"} >Badges</NavLink>
          <button className='nav-bar-item'onClick={toggleTheme}>{theme === 'light' ? '🌑' : '🌕'}</button>
        </nav>
      </div>

      {
        <Routes>
          <Route path='/' element={<Home />} />
          <Route path='/Identify' element={<Identify />} />
          <Route path = '/Compendium' element={<Compendium />}/>
        </Routes>
      }
    </>
  )
}

export default App