const express = require('express');
const router = express.Router();
const csrf = require('csurf');
const serverLinkController = require('../controllers/serverLinkController');

const csrfProtection = csrf({ cookie: false });

const authMiddleware = (req, res, next) => {
    if (!req.session.loggedIn) {
        req.flash('error', '로그인이 필요한 페이지입니다.');
        return res.redirect('/login');
    }
    next();
};

router.get('/:customLink', serverLinkController.handleCustomLink);

router.post('/setup', authMiddleware, csrfProtection, express.json(), serverLinkController.setupCustomLink);

router.get('/info', authMiddleware, csrfProtection, serverLinkController.getServerCustomLink);

module.exports = router;

// V1.5