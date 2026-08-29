import Taro from '@tarojs/taro'

const PREFIX = 'pal:'

export const storage = {
  get<T>(key: string, fallback: T): T {
    try {
      const value = Taro.getStorageSync<T>(`${PREFIX}${key}`)
      return value === '' || value === undefined || value === null ? fallback : value
    } catch {
      return fallback
    }
  },
  set<T>(key: string, value: T) {
    Taro.setStorageSync(`${PREFIX}${key}`, value)
  },
  remove(key: string) {
    Taro.removeStorageSync(`${PREFIX}${key}`)
  },
  clear() {
    const info = Taro.getStorageInfoSync()
    info.keys.filter((key) => key.startsWith(PREFIX)).forEach((key) => Taro.removeStorageSync(key))
  }
}
