export default defineAppConfig({
  pages: [
    'pages/training/index',
    'pages/records/index',
    'pages/stats/index',
    'pages/profile/index',
    'pages/replay/index'
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#090d12',
    navigationBarTitleText: 'PRICE ACTION LAB',
    navigationBarTextStyle: 'white',
    backgroundColor: '#090d12'
  },
  tabBar: {
    color: '#69737f',
    selectedColor: '#d7ff3f',
    backgroundColor: '#0c1117',
    borderStyle: 'black',
    list: [
      { pagePath: 'pages/training/index', text: '训练' },
      { pagePath: 'pages/records/index', text: '记录' },
      { pagePath: 'pages/stats/index', text: '统计' },
      { pagePath: 'pages/profile/index', text: '我的' }
    ]
  },
  lazyCodeLoading: 'requiredComponents'
})
