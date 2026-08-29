import { PropsWithChildren, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { useAppStore } from './store/app-store'
import './app.scss'

function App({ children }: PropsWithChildren) {
  const hydrate = useAppStore((state) => state.hydrate)

  useEffect(() => {
    hydrate()
    Taro.setBackgroundColor({ backgroundColor: '#090d12', backgroundColorTop: '#090d12', backgroundColorBottom: '#090d12' })
  }, [hydrate])

  return children
}

export default App
