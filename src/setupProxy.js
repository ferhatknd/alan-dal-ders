const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:5001', // Backend portunu 5001 olarak güncelledik
      changeOrigin: true,
    })
  );
};