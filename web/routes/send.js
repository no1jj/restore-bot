const express = require('express');
const router = express.Router();
const csrf = require('csurf');
const sendController = require('../controllers/sendController');

const csrfProtection = csrf({ cookie: false });

const authMiddleware = (req, res, next) => {
    if (!req.session.loggedIn) {
        req.flash('error', '로그인이 필요한 페이지입니다.');
        return res.redirect('/login');
    }
    next();
};

router.get('/', csrfProtection, authMiddleware, sendController.renderSendPage);
router.post('/auth-message', csrfProtection, authMiddleware, express.json(), sendController.sendAuthMessage);

module.exports = router;

// V1.4.2 