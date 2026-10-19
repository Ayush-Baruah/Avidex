import { useState, useEffect } from 'react'
import { Routes, Route, Link, useNavigate } from 'react-router-dom'
import NavBar from '../src/components/NavBar.jsx'
import Identify from './pages/Identify.jsx'
import Home from './pages/Home.jsx'
import Compendium from './pages/Compendium.jsx'
import './App.css'



function App() {
  const [signedIn, setSignedIn] = useState(false)

  // Reads any previously saved preference on first load, defaulting to
  // "light" if this is the user's first visit
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
        <h1 className='title' onClick={() => handleNavClick("/")}>Avidex</h1>
        <nav className='nav-bar'>
          <h3 className='nav-bar-item' onClick={() => handleNavClick("/Identify")}>Identify</h3>
          <h3 className='nav-bar-item' onClick={() => handleNavClick("/Compendium")}>Compendium</h3>
          <h3 className='nav-bar-item'>Map</h3>
          <h3 className='nav-bar-item'>Badges</h3>
          <h3 className='nav-bar-item'>Avidex</h3>
          <button className='nav-bar-item'onClick={toggleTheme}>{theme === 'light' ? '🌙' : '☀️'}</button>
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