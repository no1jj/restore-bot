const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
    res.render('index', {
      title: '환영합니다',
      message: '우리 프로젝트에 방문해 주셔서 감사합니다.',
      discordUrl: 'https://discord.gg/tVCyWkTG5m',
      githubUrl: 'https://github.com/no1jj/restore-bot'
    });
  });

router.get('/privacypolicy', (req, res) => {
    res.render('privacy_policy');
});

router.get('/invite', (req, res) => {
    res.redirect('https://discord.com/oauth2/authorize?client_id=1355209496863178760&permissions=8&integration_type=0&scope=bot');
});

module.exports = router; 

// V1.3