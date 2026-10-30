import { useState } from "react"

const NavBar = () => {
    <div className='top-bar'>
        <h1 className='title' onClick={() => handleNavClick("/")}>Avidex</h1>
        <nav className='nav-bar'>
          <h3 className='nav-bar-item' onClick={() => handleNavClick("/Compendium")}>Compendium</h3>
          <h3 className='nav-bar-item'>Map</h3>
          <h3 className='nav-bar-item'>Badges</h3>
          <h3 className='nav-bar-item'>Your Avidex</h3>
        </nav>
      </div>
}

export default NavBar