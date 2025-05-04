const express = require('express');
const router = express.Router();
const csrf = require('csurf');
const infoController = require('../controllers/infoController');

const csrfProtection = csrf({ cookie: false });

const authMiddleware = (req, res, next) => {
    if (!req.session.loggedIn) {
        req.flash('error', '로그인이 필요한 페이지입니다.');
        return res.redirect('/login');
    }
    next();
};

router.get('/', authMiddleware, csrfProtection, infoController.renderInfoPage);

router.post('/update', authMiddleware, csrfProtection, express.json(), infoController.updateInfo);

module.exports = router;

// V1.5