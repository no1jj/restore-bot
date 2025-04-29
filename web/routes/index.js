const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
    res.redirect('https://github.com/no1jj');
});

router.get('/privacypolicy', (req, res) => {
    res.render('privacy_policy');
});

module.exports = router; 