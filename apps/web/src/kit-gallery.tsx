import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { Gallery } from './components/kit/gallery/Gallery'
// index.css first: gallery.css (the sheet's doc- rules) must come after hermi.css, as on the kit page.

// Dev and test entry for the component gallery (kit-gallery.html). Not part of the production build.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Gallery />
  </StrictMode>,
)
