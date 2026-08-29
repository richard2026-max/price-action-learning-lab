declare namespace NodeJS {
  interface ProcessEnv {
    NODE_ENV: 'development' | 'production'
    TARO_APP_API_BASE?: string
    TARO_APP_DEV_TOKEN?: string
  }
}
