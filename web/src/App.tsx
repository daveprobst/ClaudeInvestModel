import { useTheme } from './hooks'
import { useData } from './data'
import { Footer, Nav } from './components/Chrome'
import { Hero } from './components/Hero'
import { SignalBoard } from './components/SignalBoard'
import { Performance } from './components/Performance'
import { Crashes } from './components/Crashes'
import { Upside } from './components/Upside'
import { Evidence } from './components/Evidence'
import { Method } from './components/Method'

export default function App() {
  const [theme, toggle] = useTheme()
  const { data, error } = useData()
  return (
    <>
      <Nav theme={theme} toggle={toggle} />
      <main id="top">
        {error && <div className="skeleton">Could not load model data. {error}</div>}
        {!data && !error && <div className="skeleton">Loading model…</div>}
        {data && (
          <>
            <Hero model={data.model} />
            <SignalBoard model={data.model} series={data.series} />
            <Performance model={data.model} series={data.series} />
            <Crashes model={data.model} />
            <Upside model={data.model} />
            <Evidence model={data.model} />
            <Method model={data.model} />
          </>
        )}
      </main>
      {data && <Footer model={data.model} />}
    </>
  )
}
