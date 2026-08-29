import { Button, Input, Text, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState } from 'react'
import { API_BASE } from '../../services/request'
import { authService } from '../../services/auth'
import { useAppStore } from '../../store/app-store'
import './index.scss'

export default function ProfilePage() {
  const [token, setToken] = useState(authService.getToken())
  const [user, setUser] = useState(authService.getUser())
  const { preferences, setPreferences, resetLocalData } = useAppStore()
  const save = () => { authService.setToken(token); Taro.showToast({ title: '认证已保存', icon: 'success' }) }
  const login = async () => {
    try {
      const next = await authService.login()
      setUser(next)
      setToken(authService.getToken())
      Taro.showToast({ title: '登录成功', icon: 'success' })
    } catch (error) {
      Taro.showToast({ title: error instanceof Error ? error.message : '登录失败', icon: 'none' })
    }
  }
  const clear = () => Taro.showModal({ title: '清除本地训练数据？', content: '将删除本机 token、偏好和会话缓存，不会删除服务端训练记录。', success: (res) => { if (res.confirm) { resetLocalData(); authService.clearToken(); setToken(''); setUser(null); Taro.showToast({ title: '已清除', icon: 'none' }) } } })

  return <View className='screen profile-screen'>
    <Text className='eyebrow'>OPERATOR PROFILE</Text>
    <Text className='page-title'>我的终端</Text>
    <View className='identity panel'>
      <View className='avatar mono'>PA</View>
      <View><Text className='identity-name'>{user?.display_name || (user ? 'WECHAT OPERATOR' : 'NOT SIGNED IN')}</Text><Text className='identity-meta mono'>{user ? `${user.provider.toUpperCase()} / ACTIVE` : 'AUTH REQUIRED'}</Text></View>
    </View>

    {!user && <Button className='primary-button' onClick={login}>{authService.isLocalDev() ? '开发环境登录' : '微信登录'}</Button>}

    <Text className='group-title'>连接配置</Text>
    <View className='setting panel'>
      <Text className='section-label'>API BASE</Text><Text className='api-base mono'>{API_BASE}</Text>
      <Text className='section-label token-label'>BEARER / DEV TOKEN</Text>
      <Input className='token-input mono' password value={token} placeholder='local-dev' onInput={(event) => setToken(event.detail.value)} />
      <Button className='secondary-button save-token' onClick={save}>保存认证</Button>
    </View>

    <Text className='group-title'>训练默认值</Text>
    <View className='setting-list'>
      <View className='setting-row'><View><Text>默认标的</Text><Text className='setting-hint'>当前本地训练品种</Text></View><Text className='setting-value mono'>{preferences.instrumentId}</Text></View>
      <View className='setting-row'><View><Text>回放周期</Text><Text className='setting-hint'>每根 K 线跨度</Text></View><Text className='setting-value mono'>{preferences.timeframe.toUpperCase()}</Text></View>
      <View className='setting-row'><View><Text>热身 K 线</Text><Text className='setting-hint'>开局可见的历史长度</Text></View><View className='stepper'><Text onClick={() => setPreferences({ warmupBars: Math.max(4, preferences.warmupBars - 2) })}>−</Text><Text className='mono'>{preferences.warmupBars}</Text><Text onClick={() => setPreferences({ warmupBars: Math.min(50, preferences.warmupBars + 2) })}>＋</Text></View></View>
    </View>
    <Button className='danger-zone' onClick={clear}>清除本地数据</Button>
    <Text className='build mono'>MINIAPP / TARO 4 / BUILD 0.1.0</Text>
  </View>
}
