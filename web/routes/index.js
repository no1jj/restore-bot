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

module.exports = router; 

// V1.1.1